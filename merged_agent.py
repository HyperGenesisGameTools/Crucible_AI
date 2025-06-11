import os
import sys
import sqlite3
import re
from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
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

# --- AGENT STATE ---
# This will hold the initialized agent so it doesn't need to be reloaded.
agent_executor = None

# --- DATABASE HELPER FUNCTIONS ---

def create_connection(db_file):
    """Create a database connection to the SQLite database."""
    conn = None
    try:
        # Allow multithreaded access for web frameworks/bots
        conn = sqlite3.connect(db_file, check_same_thread=False)
        conn.row_factory = sqlite3.Row
    except Error as e:
        print(f"Error connecting to database: {e}")
    return conn

def get_project_id_by_name(conn, project_name):
    """Finds a project's ID by its name."""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM projects WHERE name = ?", (project_name,))
    result = cursor.fetchone()
    return result['id'] if result else None

def get_user_id_by_name(conn, user_name):
    """Finds a user's ID by their name."""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE name = ?", (user_name,))
    result = cursor.fetchone()
    return result['id'] if result else None


# --- AGENT TOOLS ---

def reply_to_user(message: str) -> str:
    """
    Use this tool to provide a direct response or to have a general conversation with the user.
    Use this when no other tool is suitable for the user's query, such as for greetings,
    acknowledgements, or when you need to ask a clarifying question.
    The input should be your exact response to the user.
    """
    print(f"\n>> Replying to user with: '{message}'")
    # This response is for the agent's internal reasoning, confirming the action was taken.
    return f"This was your response to the user: '{message}'. You should now provide this as your final answer."

def knowledge_base_retriever(input_str: str) -> str:
    """
    Use this tool to retrieve information from the knowledge base about
    existing tasks, projects, and users. It returns raw document context, not a final answer.
    Input should be a user's question.
    """
    print(f"\n>> Raw retriever input: '{input_str}'")
    match = re.search(r'query="([^"]*)"', input_str)
    if match:
        query = match.group(1)
    else:
        query = input_str
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
    if not conn:
        return "Error: Could not connect to the database."
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email FROM users")
    users = cursor.fetchall()
    conn.close()
    if not users:
        return "No users found in the database."
    return "\n".join([f"- ID: {user['id']}, Name: {user['name']}, Email: {user['email']}" for user in users])

def add_task(title: str, project_name: str, assignee_name: str, description: str = "", priority: str = "Medium", status: str = "To Do") -> str:
    """
    Use this tool to add a new task to the database.
    You must provide a title, a project name, and an assignee name.
    """
    print(f"\n>> Adding new task: '{title}'")
    conn = create_connection(DB_FILE)
    if not conn:
        return "Error: Could not connect to the database."

    project_id = get_project_id_by_name(conn, project_name)
    if not project_id:
        return f"Error: Project '{project_name}' not found."
    
    assignee_id = get_user_id_by_name(conn, assignee_name)
    if not assignee_id:
        return f"Error: User '{assignee_name}' not found."

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tasks (title, description, status, priority, project_id, assignee_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, description, status, priority, project_id, assignee_id),
        )
        conn.commit()
        task_id = cursor.lastrowid
        conn.close()
        return f"Successfully added new task '{title}' with ID {task_id} to project '{project_name}', assigned to {assignee_name}."
    except sqlite3.IntegrityError as e:
        return f"Error adding task: {e}"


# --- AGENT INITIALIZATION AND INVOCATION ---

def initialize_agent():
    """
    Sets up the agent components (LLM, tools, prompt) and assigns the
    created agent executor to the global 'agent_executor' variable.
    This should be run once on application startup.
    """
    global agent_executor # Declare that we are modifying the global variable
    print("--- Initializing The Crucible AI Agent ---")
    
    if not os.path.exists(DB_FILE):
        print(f"FATAL ERROR: Database file not found at '{DB_FILE}'. Please run setup_db.py first.")
        sys.exit(1)
    if not os.path.exists(CHROMA_PERSIST_DIR):
        print(f"FATAL ERROR: ChromaDB directory not found at '{CHROMA_PERSIST_DIR}'. Please run embed_db.py first.")
        sys.exit(1)

    try:
        llm = ChatOpenAI(
            base_url=LOCAL_LLM_URL, api_key=DUMMY_API_KEY, model=MODEL_NAME, temperature=0.2
        )
        print("Successfully connected to local LLM server.")
    except Exception as e:
        print(f"FATAL ERROR: Could not connect to LLM server: {e}")
        sys.exit(1)
        
    tools = [
        Tool(
            name="Reply",
            func=reply_to_user,
            description="Use this tool for general conversation, greetings, or when no other tool is appropriate. The input should be your direct response to the user."
        ),
        Tool(
            name="KnowledgeBaseRetriever",
            func=knowledge_base_retriever,
            description="Use this to retrieve context about existing tasks, projects, status, or assignees from the project knowledge base. It's the best tool for answering specific questions about project data."
        ),
        Tool(name="ListUsers", func=list_users, description="Use this to get a list of all available users who can be assigned to tasks."),
        Tool(name="AddTask", func=add_task, description="Use this tool to create a new task. Requires a title, project_name, and assignee_name."),
    ]

    prompt = hub.pull("hwchase17/react")
    agent = create_react_agent(llm, tools, prompt)
    
    # Assign the created executor directly to the global variable
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True, 
        handle_parsing_errors="Please try again, paying close attention to the tool's instructions and formatting."
    )
    
    print("Agent initialized successfully.")

def invoke_agent(query: str) -> str:
    """
    Invokes the agent with a given query and returns the final output string.
    This is a SYNCHRONOUS function and should be run in a separate thread
    in an async environment.
    """
    global agent_executor
    if not agent_executor:
        return "Error: Agent is not initialized. Please run initialize_agent() first."
    
    try:
        print(f"Invoking agent with query: '{query}'")
        result = agent_executor.invoke({"input": query})
        return result.get('output', "Error: No output from agent.")
    except Exception as e:
        print(f"An error occurred during agent invocation: {e}")
        return "Sorry, I encountered an error while processing your request."


# --- MAIN CHAT LOOP FOR COMMAND-LINE TESTING ---
def main():
    """
    Main function for command-line interaction.
    Initializes the agent and then enters a chat loop.
    """
    initialize_agent()

    print("\n--- Agent Interface Ready ---")
    print("Ask about tasks, or ask to add a new task. Type 'exit' to end.")
    while True:
        try:
            query = input("\nYou: ")
            if query.lower() in ["exit", "quit"]:
                print("Exiting. Goodbye!")
                break
            
            response = invoke_agent(query)
            
            print(f"\nAgent: {response}")

        except KeyboardInterrupt:
            print("\nExiting. Goodbye!")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            break


if __name__ == "__main__":
    main()
