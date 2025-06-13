import sqlite3
from sqlite3 import Error
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
import os

# --- CONFIGURATION ---
DB_FILE = "project_tasks.db"
CHROMA_PERSIST_DIR = "./chroma_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

def load_tasks_from_db(db_file):
    """
    Connects to the SQLite database, queries all tasks with their related project
    and user info, and formats them into LangChain Document objects.
    """
    if not os.path.exists(db_file):
        print(f"Error: Database file not found at '{db_file}'")
        print("Please run the `setup_db.py` script first to create and populate the database.")
        return []

    conn = None
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row  # Access columns by name
        print(f"Successfully connected to SQLite database: {db_file}")
    except Error as e:
        print(e)
        return []

    cursor = conn.cursor()
    # Query to get a comprehensive view of each task
    query = """
    SELECT
        t.id,
        t.title,
        t.description,
        t.status,
        t.priority,
        t.due_date,
        p.name as project_name,
        u.name as assignee_name
    FROM
        tasks t
    LEFT JOIN
        projects p ON t.project_id = p.id
    LEFT JOIN
        users u ON t.assignee_id = u.id;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    documents = []
    for row in rows:
        # Create a rich text content for embedding. This combines the most
        # important fields into a single string.
        page_content = (
            f"Task: {row['title']}\n"
            f"Project: {row['project_name']}\n"
            f"Status: {row['status']}\n"
            f"Priority: {row['priority']}\n"
            f"Assignee: {row['assignee_name']}\n"
            f"Description: {row['description']}"
        )
        # Store all individual fields in metadata for potential filtering later
        metadata = {
            "task_id": row['id'],
            "title": row['title'],
            "project": row['project_name'],
            "status": row['status'],
            "priority": row['priority'],
            "due_date": row['due_date'],
            "assignee": row['assignee_name']
        }
        documents.append(Document(page_content=page_content, metadata=metadata))

    print(f"Loaded {len(documents)} documents from the database.")
    return documents

def main():
    """
    Main function to orchestrate the embedding pipeline:
    1. Load data from SQLite.
    2. Initialize a local embedding model.
    3. Create and persist a ChromaDB vector store.
    """
    print("--- Starting Embedding Pipeline ---")

    # 1. Load documents from the database
    documents = load_tasks_from_db(DB_FILE)

    if not documents:
        print("Halting pipeline due to no documents loaded.")
        return

    # 2. Initialize the local, open-source embedding model
    # The model will be downloaded automatically by the library on its first run.
    print(f"Initializing embedding model: '{EMBEDDING_MODEL}'...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    print("Embedding model loaded successfully.")

    # 3. Create the vector store and persist it to disk
    # This single step generates embeddings for all documents and saves them.
    print(f"Generating embeddings and creating Chroma vector store...")
    print(f"Persistence directory: '{CHROMA_PERSIST_DIR}'")
    
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=CHROMA_PERSIST_DIR
    )

    print("\n--- Embedding Pipeline Complete ---")
    print(f"Successfully embedded {len(documents)} documents.")
    print(f"Vector store has been saved to '{vector_store._persist_directory}'")

if __name__ == '__main__':
    # To run this script, you need to install the required packages:
    # pip install langchain-community sentence-transformers chromadb
    main()