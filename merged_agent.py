# merged_agent.py (Modified for Memory Manager Integration)
import os
import sys
import sqlite3
import re
from multiprocessing import Queue
from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from sqlite3 import Error

from prompt_context import PromptContext

# --- CONFIGURATION ---
DB_FILE = "project_tasks.db"
CHROMA_PERSIST_DIR = "./chroma_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
LOCAL_LLM_URL = "http://localhost:1234/v1"
DUMMY_API_KEY = "lm-studio"
MODEL_NAME = "local-model"
MODEL_TEMP = 0.4

# --- AGENT STATE ---
agent_executor = None
# This queue will be set by the main bot.py script.
memory_queue: Queue = None

def set_memory_queue(queue: Queue):
    """
    Allows the main application process to pass the multiprocessing
    queue to this module.
    """
    global memory_queue
    memory_queue = queue

# --- DATABASE HELPER FUNCTIONS (Unchanged) ---
def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file, check_same_thread=False)
        conn.row_factory = sqlite3.Row
    except Error as e:
        print(f"Error connecting to database: {e}")
    return conn

def get_project_id_by_name(conn, project_name):
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM projects WHERE name = ?", (project_name,))
    result = cursor.fetchone()
    return result[0] if result else None

def get_user_id_by_name(conn, user_name):
    cursor = conn.cursor()
    # This is a simple search, might need to be more robust for full names
    cursor.execute("SELECT id FROM users WHERE name LIKE ?", (f"%{user_name}%",))
    result = cursor.fetchone()
    return result[0] if result else None


# --- AGENT TOOLS (MODIFIED) ---

def reply_to_user(message: str) -> str:
    """
    Use this tool to provide a direct response or to have a general conversation with the user.
    Use this when no other tool is suitable for the user's query, such as for greetings,
    acknowledgements, or when you need to ask a clarifying question.
    The input should be your exact response to the user.
    """
    print(f"\n>> Replying to user with: '{message}'")
    return f"This was your response to the user: '{message}'. You should now provide this as your final answer."

def knowledge_base_retriever(input_str: str) -> str:
    """
    Use this tool to retrieve information from the knowledge base about
    existing tasks, projects, and users. It returns raw document context, not a final answer.
    Input should be a user's question.
    """
    print(f"\n>> Raw retriever input: '{input_str}'")
    match = re.search(r'query="([^"]*)"', input_str)
    query = match.group(1) if match else input_str
    print(f"\n>> Searching Knowledge Base for: '{query}'")

    if not os.path.exists(CHROMA_PERSIST_DIR):
        return f"Error: Knowledge base (ChromaDB) not found at '{CHROMA_PERSIST_DIR}'. Please run embed_db.py."

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vector_store = Chroma(
        persist_directory=CHROMA_PERSIST_DIR,
        embedding_function=embeddings
    )
    retriever = vector_store.as_retriever(search_kwargs={"k": 4})
    docs = retriever.get_relevant_documents(query)
    return "\n\n".join(doc.page_content for doc in docs)

def list_users() -> str:
    """
    Use this tool to get a list of all users in the database.
    Returns a formatted string of user names and their IDs.
    """
    print("\n>> Listing all users...")
    conn = create_connection(DB_FILE)
    if not conn: return "Error: Could not connect to the database."
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email FROM users")
    users = cursor.fetchall()
    conn.close()
    if not users: return "No users found in the database."
    return "\n".join([f"- ID: {user['id']}, Name: {user['name']}, Email: {user['email']}" for user in users])

def add_task(title: str, project_name: str, assignee_name: str, description: str = "", priority: str = "Medium", status: str = "To Do") -> str:
    """
    Use this tool to add a new task to the database.
    You must provide a title, a project name, and an assignee name.
    """
    print(f"\n>> Adding new task: '{title}'")
    conn = create_connection(DB_FILE)
    if not conn: return "Error: Could not connect to the database."

    project_id = get_project_id_by_name(conn, project_name)
    if not project_id: return f"Error: Project '{project_name}' not found."
    
    assignee_id = get_user_id_by_name(conn, assignee_name)
    if not assignee_id: return f"Error: User '{assignee_name}' not found."

    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (title, description, status, priority, project_id, assignee_id) VALUES (?, ?, ?, ?, ?, ?)",
            (title, description, status, priority, project_id, assignee_id),
        )
        conn.commit()
        task_id = cursor.lastrowid
        conn.close()

        # --- NEW: SEND UPDATE SIGNAL TO MEMORY MANAGER ---
        if memory_queue:
            print(f"   -> Sending 'add' signal for task_id: {task_id} to memory manager.")
            memory_queue.put({"action": "add", "task_id": task_id})
        else:
            print("   -> WARNING: Memory queue not available. Change will not be reflected in real-time.")
        
        return f"Successfully added new task '{title}' with ID {task_id} to project '{project_name}', assigned to {assignee_name}."
    except sqlite3.Error as e:
        return f"Error adding task: {e}"


# --- AGENT INITIALIZATION ---
def initialize_agent():
    """
    Sets up the agent components (LLM, tools, prompt) and assigns the
    created agent executor to the global 'agent_executor' variable.
    """
    global agent_executor
    print("--- Initializing The Crucible AI Agent ---")
    
    # Prerequisite checks
    if not os.path.exists(DB_FILE):
        print(f"FATAL ERROR: Database file not found at '{DB_FILE}'. Please run setup_db.py first.")
        sys.exit(1)
    if not os.path.exists(CHROMA_PERSIST_DIR):
        print(f"FATAL ERROR: ChromaDB directory not found at '{CHROMA_PERSIST_DIR}'. Please run embed_db.py first.")
        sys.exit(1)

    try:
        llm = ChatOpenAI(base_url=LOCAL_LLM_URL, api_key=DUMMY_API_KEY, model=MODEL_NAME, temperature=MODEL_TEMP)
        print("Successfully connected to local LLM server.")
    except Exception as e:
        print(f"FATAL ERROR: Could not connect to LLM server: {e}")
        sys.exit(1)
        
    tools = [
        Tool(name="Reply", func=reply_to_user, description="..."),
        Tool(name="KnowledgeBaseRetriever", func=knowledge_base_retriever, description="..."),
        Tool(name="ListUsers", func=list_users, description="..."),
        Tool(name="AddTask", func=add_task, description="Use this tool to create a new task. Requires a title, project_name, and assignee_name."),
    ]

    prompt = hub.pull("hwchase17/react")
    agent = create_react_agent(llm, tools, prompt)
    
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True, 
        handle_parsing_errors="Please try again, paying close attention to the tool's instructions and formatting."
    )
    
    print("Agent initialized successfully.")


# --- AGENT INVOCATION (Unchanged) ---
def invoke_agent(query: str, context: PromptContext) -> str:
    """
    Invokes the agent with a given query and context, returning the final output.
    """
    global agent_executor
    if not agent_executor:
        return "Error: Agent is not initialized. Please run initialize_agent() first."
    
    context_str = context.format_for_prompt()
    combined_input = f"{context_str}{query}"
    
    try:
        print(f"--- Invoking Agent with Combined Input ---\n{combined_input}\n-----------------------------------------")
        result = agent_executor.invoke({"input": combined_input})
        return result.get('output', "Error: No output from agent.")
    except Exception as e:
        print(f"An error occurred during agent invocation: {e}")
        return "Sorry, I encountered an error while processing your request."

# --- MAIN CHAT LOOP FOR COMMAND-LINE TESTING (Unchanged) ---
def main():
    initialize_agent()
    session_context = PromptContext()
    session_context.background_briefing = "The user is ARCHITECT. The AI is Crucible."
    print("\n--- Agent Interface Ready ---")
    while True:
        try:
            query = input("\nYou: ")
            if query.lower() in ["exit", "quit"]: break
            response = invoke_agent(query, session_context)
            print(f"\nAgent: {response}")
        except (KeyboardInterrupt, EOFError):
            break
    print("\nExiting. Goodbye!")

if __name__ == "__main__":
    main()
