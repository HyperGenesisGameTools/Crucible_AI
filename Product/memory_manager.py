# memory_manager.py

import sqlite3
import time
import os
from multiprocessing import Queue
from sqlite3 import Error

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

# --- CONFIGURATION (Should match other scripts) ---
DB_FILE = "project_tasks.db"
CHROMA_PERSIST_DIR = "./chroma_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# --- HELPER FUNCTIONS ---

def create_connection(db_file):
    """ Create a database connection to a SQLite database. """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row  # Access columns by name
    except Error as e:
        print(f"[MemoryManager] Error connecting to database: {e}")
    return conn

def format_task_as_document(task_row: sqlite3.Row) -> Document:
    """ Formats a single task row from SQLite into a LangChain Document. """
    # Create the rich text content for embedding.
    page_content = (
        f"Task: {task_row['title']}\n"
        f"Project: {task_row['project_name']}\n"
        f"Status: {task_row['status']}\n"
        f"Priority: {task_row['priority']}\n"
        f"Assignee: {task_row['assignee_name']}\n"
        f"Description: {task_row['description']}"
    )
    # Store all individual fields in metadata.
    metadata = {
        "task_id": task_row['id'],
        "title": task_row['title'],
        "project": task_row['project_name'],
        "status": task_row['status'],
        "priority": task_row['priority'],
        "due_date": task_row['due_date'],
        "assignee": task_row['assignee_name']
    }
    # The document ID must be a string for ChromaDB.
    return Document(page_content=page_content, metadata=metadata)


def get_task_document_by_id(conn: sqlite3.Connection, task_id: int) -> Document | None:
    """
    Queries the database for a single task by its ID and returns it as a
    LangChain Document.
    """
    query = """
    SELECT
        t.id, t.title, t.description, t.status, t.priority, t.due_date,
        p.name as project_name, u.name as assignee_name
    FROM tasks t
    LEFT JOIN projects p ON t.project_id = p.id
    LEFT JOIN users u ON t.assignee_id = u.id
    WHERE t.id = ?;
    """
    cursor = conn.cursor()
    cursor.execute(query, (task_id,))
    row = cursor.fetchone()

    if row:
        return format_task_as_document(row)
    return None

def get_all_task_documents(conn: sqlite3.Connection) -> list[Document]:
    """
    Queries the database for all tasks and returns them as a list of
    LangChain Documents.
    """
    query = """
    SELECT
        t.id, t.title, t.description, t.status, t.priority, t.due_date,
        p.name as project_name, u.name as assignee_name
    FROM tasks t
    LEFT JOIN projects p ON t.project_id = p.id
    LEFT JOIN users u ON t.assignee_id = u.id;
    """
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()

    documents = [format_task_as_document(row) for row in rows]
    return documents


# --- CORE WORKER FUNCTION ---

def memory_worker(queue: Queue):
    """
    The main function for the memory manager process.
    It listens on a queue for update signals from the main application
    and keeps the ChromaDB vector store synchronized with the SQLite DB.
    """
    print("[MemoryManager] Worker process started.", flush=True)

    # 1. Initialize Embeddings and Vector Store
    if not os.path.exists(CHROMA_PERSIST_DIR):
        print(f"[MemoryManager] FATAL: ChromaDB directory not found at '{CHROMA_PERSIST_DIR}'.", flush=True)
        print("[MemoryManager] Please run embed_db.py first.", flush=True)
        return

    try:
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        vector_store = Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=embeddings
        )
        print("[MemoryManager] Successfully connected to ChromaDB.", flush=True)
    except Exception as e:
        print(f"[MemoryManager] FATAL: Could not initialize ChromaDB. Error: {e}", flush=True)
        return


    # 2. Initial Synchronization on Startup
    # This ensures consistency if the bot was offline while the DB was changed.
    print("[MemoryManager] Performing initial sync with database...", flush=True)
    conn = create_connection(DB_FILE)
    if conn:
        try:
            # Get all documents currently in the SQLite DB
            all_db_docs = get_all_task_documents(conn)
            all_db_ids = {str(doc.metadata['task_id']) for doc in all_db_docs}
            print(f"[MemoryManager] Found {len(all_db_ids)} tasks in SQLite.", flush=True)

            # Get all document IDs currently in the vector store
            existing_vector_ids_dict = vector_store.get(include=[]) # Fast way to get IDs
            existing_vector_ids = set(existing_vector_ids_dict['ids'])
            print(f"[MemoryManager] Found {len(existing_vector_ids)} documents in ChromaDB.", flush=True)

            # A) Delete documents from Chroma that are no longer in SQLite
            ids_to_delete = list(existing_vector_ids - all_db_ids)
            if ids_to_delete:
                print(f"[MemoryManager] Deleting {len(ids_to_delete)} obsolete documents from ChromaDB.", flush=True)
                vector_store.delete(ids=ids_to_delete)
            
            # B) Add/Update all current documents from SQLite to Chroma
            # .add_documents will update existing documents if the IDs are the same.
            if all_db_docs:
                print(f"[MemoryManager] Upserting {len(all_db_docs)} documents into ChromaDB to ensure consistency.", flush=True)
                vector_store.add_documents(
                    documents=all_db_docs,
                    ids=[str(doc.metadata['task_id']) for doc in all_db_docs]
                )

            print("[MemoryManager] Initial sync complete.", flush=True)
        except Exception as e:
            print(f"[MemoryManager] Error during initial sync: {e}", flush=True)
        finally:
            conn.close()

    # 3. Main Event Loop: Listen for messages from the main process
    print("[MemoryManager] Now listening for real-time updates...", flush=True)
    while True:
        try:
            # This call blocks until a message is available on the queue
            message = queue.get()
            print(f"[MemoryManager] Received message: {message}", flush=True)

            action = message.get("action")
            task_id = message.get("task_id")

            if not action or not task_id:
                print(f"[MemoryManager] WARNING: Received malformed message: {message}", flush=True)
                continue
            
            # We need a fresh connection for each transaction
            conn = create_connection(DB_FILE)
            if not conn:
                print("[MemoryManager] ERROR: Could not connect to DB to process update.", flush=True)
                continue

            if action in ["add", "update"]:
                print(f"[MemoryManager] Processing '{action}' for task_id: {task_id}", flush=True)
                doc_to_update = get_task_document_by_id(conn, task_id)
                if doc_to_update:
                    vector_store.add_documents(
                        documents=[doc_to_update],
                        ids=[str(task_id)] # Use .add_documents as it also handles updates (upsert)
                    )
                    print(f"[MemoryManager] Successfully upserted document for task {task_id}.", flush=True)
                else:
                    print(f"[MemoryManager] WARNING: Task {task_id} not found in DB for {action}.", flush=True)

            elif action == "delete":
                print(f"[MemoryManager] Processing 'delete' for task_id: {task_id}", flush=True)
                # Chroma requires a list of string IDs for deletion
                vector_store.delete(ids=[str(task_id)])
                print(f"[MemoryManager] Successfully deleted document for task {task_id}.", flush=True)
            
            conn.close()

        except queue.Empty:
            # This part of the try-except is not strictly needed with queue.get()
            # but is good practice if you switch to non-blocking gets.
            time.sleep(1)
            continue
        except KeyboardInterrupt:
            print("\n[MemoryManager] Worker process shutting down.", flush=True)
            break
        except Exception as e:
            # Catch-all for any other errors to keep the worker alive
            print(f"[MemoryManager] An unexpected error occurred in the event loop: {e}", flush=True)
            # Avoid rapid-fire error loops
            time.sleep(5)
# --- END OF MEMORY MANAGER ---