import sqlite3
import sys
from sqlite3 import Error
from typing import List

from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
# We will use StructuredTool to handle functions with multiple arguments
from langchain.tools import StructuredTool
from langchain_openai import ChatOpenAI

# --- CONFIGURATION ---
DB_FILE = "project_tasks.db"
LOCAL_LLM_URL = "http://localhost:1234/v1"
DUMMY_API_KEY = "lm-studio"
MODEL_NAME = "local-model"


# 1. PYTHON FUNCTIONS FOR DATABASE INTERACTION
# ===============================================================

def add_new_task(
    title: str,
    description: str,
    project_id: int,
    assignee_id: int,
    priority: str = 'Medium',
    status: str = 'To Do'
) -> str:
    """
    Adds a new task to the SQLite database after asking for user confirmation.
    This function should be used when a user explicitly wants to create a task.

    Args:
        title: A concise and descriptive title for the task.
        description: A detailed description of what the task involves.
        project_id: The integer ID of the project this task belongs to.
        assignee_id: The integer ID of the user this task is assigned to.
        priority: The task's priority level ('Low', 'Medium', 'High'). Defaults to 'Medium'.
        status: The task's current status ('To Do', 'In Progress', 'Done'). Defaults to 'To Do'.

    Returns:
        A string confirming the result of the operation.
    """
    # Parameterized SQL to prevent injection attacks
    sql_query = """
        INSERT INTO tasks(title, description, status, priority, project_id, assignee_id)
        VALUES(?, ?, ?, ?, ?, ?)
    """
    task_data = (title, description, status, priority, project_id, assignee_id)

    # --- User Confirmation Step ---
    print("\n--- ACTION CONFIRMATION ---")
    print("An agent is requesting to execute the following SQL command:")
    print(f"Query: INSERT INTO tasks(title, description, status, priority, project_id, assignee_id) VALUES{task_data}")

    # Loop until a valid input is received
    while True:
        confirm = input("Do you want to proceed? [y/n]: ").lower().strip()
        if confirm in ['y', 'n']:
            break
        print("Invalid input. Please enter 'y' for yes or 'n' for no.")

    if confirm != 'y':
        return "Action CANCELED by user. No changes were made to the database."

    # --- Database Execution Step ---
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(sql_query, task_data)
        conn.commit()
        # Return a descriptive success message
        return f"Success! Task '{title}' has been added to the database with Task ID {cursor.lastrowid}."
    except Error as e:
        # Return a detailed error message if something goes wrong
        return f"Database Error: {e}. Failed to add task '{title}'."
    finally:
        if conn:
            conn.close()


def list_users() -> str:
    """
    Retrieves a list of all users from the database.
    This tool is useful for finding the correct 'assignee_id' for a new task.
    It takes no arguments.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row  # Access columns by name
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email FROM users")
        rows = cursor.fetchall()
        
        if not rows:
            return "No users found in the database."

        # Format the output into a readable string
        user_list = "\n".join([f"- ID: {row['id']}, Name: {row['name']}, Email: {row['email']}" for row in rows])
        return f"Available users:\n{user_list}"

    except Error as e:
        return f"Database error: {e}"
    finally:
        if conn:
            conn.close()


# 2. CONVERT THE FUNCTIONS INTO LANGCHAIN TOOLS
# =================================================================
add_task_tool = StructuredTool.from_function(
    func=add_new_task,
    name="add_new_task_to_database",
    description="Use this tool to create and add a new task to the database. It requires a title, description, project_id, and assignee_id."
)

list_users_tool = StructuredTool.from_function(
    func=list_users,
    name="list_available_users",
    description="Use this tool to get a list of all available users and their corresponding IDs. This is helpful when you need to find the 'assignee_id' for a task."
)


# 3. INITIALIZE THE LANGCHAIN AGENT EXECUTOR
# ============================================
def main():
    """
    Initializes the LLM, tools, and agent, then starts an interactive loop.
    """
    print("--- Initializing Local LangChain Agent ---")

    # --- Initialize LLM from LM Studio ---
    try:
        llm = ChatOpenAI(
            base_url=LOCAL_LLM_URL,
            api_key=DUMMY_API_KEY,
            model=MODEL_NAME,
            temperature=0.2,  # Lower temperature for more predictable, tool-focused behavior
        )
        print("Successfully connected to local LLM server.")
    except Exception as e:
        print(f"FATAL: Could not connect to LLM server at {LOCAL_LLM_URL}.")
        print(f"Error details: {e}")
        sys.exit(1)

    # --- Combine tools for the agent ---
    tools = [add_task_tool, list_users_tool]

    # --- Create the Agent Prompt Template ---
    # This prompt is more explicit and includes the required 'tool_names' variable.
    prompt_template = """
    You are a helpful assistant for managing tasks. You have two primary capabilities:
    1. List all available users to find out their `assignee_id`.
    2. Add a new task to the database.

    **TOOL USAGE FLOW:**
    - If a user asks to create a task but does not provide an `assignee_id`, you MUST first use the `list_available_users` tool.
    - Review the output from `list_available_users` to find the correct `assignee_id` based on the user's request.
    - Once you have the `assignee_id`, use the `add_new_task_to_database` tool with all the required information.
    - If the user simply asks who is available, use the `list_available_users` tool and provide the output as the final answer.

    TOOLS:
    ------
    {tools}

    To use a tool, you MUST use the following format:

    Thought: [Your reasoning on which tool to use and why]
    Action: The action to take, must be one of [{tool_names}].
    Action Input: {{
      "arg_name_1": "value1",
      "arg_name_2": 123
    }}

    IMPORTANT: The 'Action Input' must be a single, valid JSON object. For tools that take no arguments, use an empty JSON object: {{}}.

    When you have a response to say to the user, you MUST use the format:

    Thought: I now have the final answer.
    Final Answer: [your response here]

    Begin!

    Question: {input}
    {agent_scratchpad}
    """
    prompt = PromptTemplate.from_template(prompt_template)

    # --- Create the Agent ---
    agent = create_react_agent(llm, tools, prompt)

    # --- Create the Agent Executor ---
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,  # Set to True to see the agent's thought process
        handle_parsing_errors=True # Helps with robustness
    )
    print("Agent initialized successfully.")

    # --- Interactive Chat Loop ---
    print("\n--- Agent is Ready ---")
    print("You can ask me to 'list the available users' or 'add a task for user X'.")
    print("Type 'exit' or 'quit' to end.")

    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ["exit", 'quit']:
                print("Exiting agent. Goodbye!")
                break

            # Invoke the agent to process the input
            response = agent_executor.invoke({"input": user_input})
            print(f"\nAssistant: {response['output']}")

        except KeyboardInterrupt:
            print("\nExiting agent. Goodbye!")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            break


if __name__ == "__main__":
    main()
