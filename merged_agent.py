# merged_agent.py (Modified for Memory Manager and Conversational Memory)
import os
import sys
import sqlite3
from multiprocessing import Queue

# Langchain imports for conversational memory and agent creation
from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain.memory import ConversationBufferWindowMemory
from langchain.tools.render import render_text_description # <-- ADDED IMPORT

# Existing imports
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from sqlite3 import Error


# --- CONFIGURATION ---
DB_FILE = "project_tasks.db"
CHROMA_PERSIST_DIR = "./chroma_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
LOCAL_LLM_URL = "http://localhost:1234/v1"
DUMMY_API_KEY = "lm-studio"
MODEL_NAME = "local-model"
MODEL_TEMP = 0.4
# System prompt is now part of the pulled hub prompt.

# --- AGENT STATE ---
agent_executor = None
memory_queue: Queue = None

def set_memory_queue(queue: Queue):
    """ Allows the main application process to pass the multiprocessing queue to this module. """
    global memory_queue
    memory_queue = queue

# --- DATABASE HELPER FUNCTIONS (Unchanged) ---
def create_connection(db_file):
    """ Create a database connection to a SQLite database. """
    conn = None
    try:
        conn = sqlite3.connect(db_file, check_same_thread=False)
        conn.row_factory = sqlite3.Row
    except Error as e:
        print(f"Error connecting to database: {e}")
    return conn

def get_project_id_by_name(conn, project_name):
    """ Fetches a project's ID from the database by its name. """
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM projects WHERE name = ?", (project_name,))
    result = cursor.fetchone()
    return result[0] if result else None

def get_user_id_by_name(conn, user_name):
    """ Fetches a user's ID from the database by their name. """
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE name LIKE ?", (f"%{user_name}%",))
    result = cursor.fetchone()
    return result[0] if result else None

# --- AGENT TOOLS (Unchanged) ---
def knowledge_base_retriever(query: str) -> str:
    """
    Use this tool ONLY to answer questions about existing tasks, projects, or users by searching the knowledge base.
    The input must be a clear, specific question.
    For example: 'What are the details of the task about the AI agent?' or 'Who is working on the Website Redesign project?'
    """
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
    return "\n\n".join(doc.page_content for doc in docs) if docs else "No relevant information found in the knowledge base for that query."


def list_users(dummy: str) -> str:
    """
    Use this tool when the user explicitly asks for a list of all available users in the system.
    This tool takes no input. It returns a formatted string of all user names, IDs, and emails.
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
    You MUST provide a title, a project_name, and an assignee_name.
    The 'description', 'priority', and 'status' fields are optional.
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

        if memory_queue:
            print(f"   -> Sending 'add' signal for task_id: {task_id} to memory manager.")
            memory_queue.put({"action": "add", "task_id": task_id})
        else:
            print("   -> WARNING: Memory queue not available. Change will not be reflected in real-time.")

        return f"Successfully added new task '{title}' with ID {task_id} to project '{project_name}', assigned to {assignee_name}."
    except sqlite3.Error as e:
        return f"Error adding task: {e}"


# --- AGENT INITIALIZATION (MODIFIED TO FIX THE ERROR) ---
def initialize_agent():
    """
    Sets up the agent components (LLM, tools, prompt) to support conversational memory.
    """
    global agent_executor
    print("--- Initializing The Crucible AI Agent (with Conversational Memory) ---")
    
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
        Tool(name="KnowledgeBaseRetriever", func=knowledge_base_retriever, description=knowledge_base_retriever.__doc__),
        Tool(name="ListUsers", func=list_users, description=list_users.__doc__),
        Tool(name="AddTask", func=add_task, description=add_task.__doc__),
    ]

    # --- START OF FIX ---
    # 1. Pull the standard ReAct chat prompt from the LangChain hub.
    # This prompt is specifically designed for this type of agent and has the required input variables.
    prompt = hub.pull("hwchase17/react-chat")

    # 2. Render the tool descriptions into a string.
    # The `render_text_description` function formats the tools in the way the prompt expects.
    rendered_tools = render_text_description(tools)
    tool_names = ", ".join([t.name for t in tools])

    # 3. "Partially" format the prompt with the tool information.
    # This pre-fills the 'tools' and 'tool_names' variables in the prompt template.
    prompt = prompt.partial(
        tools=rendered_tools,
        tool_names=tool_names,
    )
    # --- END OF FIX ---
    
    agent = create_react_agent(llm, tools, prompt)
    
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True,
        handle_parsing_errors="I made a formatting error. I will try again."
    )
    
    print("Agent initialized successfully with corrected prompt.")


# --- AGENT INVOCATION (Unchanged) ---
def invoke_agent(query: str, memory: ConversationBufferWindowMemory) -> str:
    """
    Invokes the agent with a query and a user-specific memory object.
    """
    global agent_executor
    if not agent_executor:
        return "Error: Agent is not initialized. Please run initialize_agent() first."
    
    try:
        print(f"--- Invoking Agent with Query: '{query}' ---")
        # The 'chat_history' key here MUST match the MessagesPlaceholder variable name in the prompt.
        result = agent_executor.invoke({
            "input": query,
            "chat_history": memory.chat_memory.messages
        })
        return result.get('output', "Error: No output from agent.")
    except Exception as e:
        print(f"An error occurred during agent invocation: {e}")
        return "Sorry, I encountered an error while processing your request."

# --- MAIN CHAT LOOP FOR COMMAND-LINE TESTING (Unchanged) ---
def main():
    """
    Provides a simple command-line interface for testing the agent directly.
    """
    initialize_agent()
    cli_memory = ConversationBufferWindowMemory(
        k=5, memory_key="chat_history", return_messages=True
    )

    print("\n--- Agent CLI Ready (type 'exit' or 'quit' to stop) ---")
    while True:
        try:
            query = input("\nYou: ")
            if query.lower() in ["exit", "quit"]: break
            
            response = invoke_agent(query, cli_memory)
            cli_memory.save_context({"input": query}, {"output": response})

            print(f"\nAgent: {response}")
        except (KeyboardInterrupt, EOFError):
            break
    print("\nExiting. Goodbye!")

if __name__ == "__main__":
    main()
