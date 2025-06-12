# merged_agent.py (Modified for Graceful Error Handling)
import os
import sys
import sqlite3
from multiprocessing import Queue

# Langchain imports
from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain.memory import ConversationBufferWindowMemory
from langchain.tools.render import render_text_description
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

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

# --- AGENT STATE ---
agent_executor = None
memory_queue: Queue = None

def set_memory_queue(queue: Queue):
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
    cursor.execute("SELECT id FROM users WHERE name LIKE ?", (f"%{user_name}%",))
    result = cursor.fetchone()
    return result[0] if result else None

# --- PYDANTIC SCHEMA (Unchanged) ---
class AddTaskSchema(BaseModel):
    title: str = Field(description="The title of the new task.")
    project_name: str = Field(description="The name of the project this task belongs to.")
    assignee_name: str = Field(description="The name of the user who should be assigned this task.")
    description: str = Field(description="A detailed description of the task.", default="")
    priority: str = Field(description="The priority of the task, e.g., 'Low', 'Medium', 'High'.", default="Medium")
    status: str = Field(description="The current status of the task, e.g., 'To Do', 'In Progress'.", default="To Do")

# --- AGENT TOOLS (Unchanged) ---
def knowledge_base_retriever(query: str) -> str:
    """
    Use this tool ONLY to answer questions about existing tasks, projects, or users by searching the knowledge base.
    The input must be a clear, specific question.
    """
    print(f"\n>> Searching Knowledge Base for: '{query}'")
    if not os.path.exists(CHROMA_PERSIST_DIR):
        return f"Error: Knowledge base (ChromaDB) not found at '{CHROMA_PERSIST_DIR}'. Please run embed_db.py."
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vector_store = Chroma(persist_directory=CHROMA_PERSIST_DIR, embedding_function=embeddings)
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

# --- AGENT INITIALIZATION (MODIFIED) ---
def initialize_agent():
    """
    Sets up the agent components (LLM, tools, prompt) with enhanced error handling.
    """
    global agent_executor
    print("--- Initializing The Crucible AI Agent (with Conversational ReAct Prompt) ---")

    # ... (file existence checks are unchanged) ...

    try:
        llm = ChatOpenAI(base_url=LOCAL_LLM_URL, api_key=DUMMY_API_KEY, model=MODEL_NAME, temperature=MODEL_TEMP)
        print("Successfully connected to local LLM server.")
    except Exception as e:
        print(f"FATAL ERROR: Could not connect to LLM server: {e}")
        sys.exit(1)

    tools = [
        Tool(name="KnowledgeBaseRetriever", func=knowledge_base_retriever, description=knowledge_base_retriever.__doc__),
        Tool(name="ListUsers", func=list_users, description=list_users.__doc__),
        Tool(name="AddTask", func=add_task, description=add_task.__doc__, args_schema=AddTaskSchema),
    ]

    prompt = hub.pull("hwchase17/react-chat")
    rendered_tools = render_text_description(tools)
    tool_names = ", ".join([t.name for t in tools])

    prompt = prompt.partial(tools=rendered_tools, tool_names=tool_names)
    agent = create_react_agent(llm, tools, prompt)

    # --- MODIFIED: Added 'handle_tool_error' to the AgentExecutor ---
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors="I made a formatting error. I will try again.",
        # This new parameter tells the agent to catch tool errors and pass them back to the LLM.
        handle_tool_error=True
    )

    print("Agent initialized successfully with enhanced error handling.")


# --- AGENT INVOCATION (MODIFIED) ---
def invoke_agent(query: str, memory: ConversationBufferWindowMemory) -> str:
    """
    Invokes the agent and handles any unrecoverable errors gracefully.
    """
    global agent_executor
    if not agent_executor:
        return "Error: Agent is not initialized. Please run initialize_agent() first."

    try:
        chat_history = memory.load_memory_variables({}).get("chat_history", [])
        print(f"--- Invoking Agent with Query: '{query}' ---")
        result = agent_executor.invoke({
            "input": query,
            "chat_history": chat_history
        })
        return result.get('output', "Error: No output from agent.")
    # --- MODIFIED: This block now returns a detailed error message to the user ---
    except Exception as e:
        error_message = f"An error occurred during agent invocation: {e}"
        print(error_message)
        # Return a more informative message to the user in a formatted block
        return f"Sorry, I encountered an unrecoverable error. Please see the details below:\n```\n{e}\n```"

# --- MAIN CHAT LOOP (Unchanged) ---
def main():
    initialize_agent()
    cli_memory = ConversationBufferWindowMemory(k=5, memory_key="chat_history", return_messages=True)
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