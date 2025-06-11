import sqlite3
import sys
from sqlite3 import Error

from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from langchain_openai import ChatOpenAI

# --- CONFIGURATION ---
DB_FILE = "project_tasks.db"
LOCAL_LLM_URL = "http://localhost:1234/v1"
DUMMY_API_KEY = "lm-studio"
MODEL_NAME = "local-model"


# 1. PYTHON FUNCTION TO ADD A NEW TASK
# =======================================
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


# 2. CONVERT THE FUNCTION INTO A LANGCHAIN TOOL
# ==============================================
# The 'description' is crucial; it's how the agent knows what the tool is for.
add_task_tool = Tool(
    name="add_new_task_to_database",
    func=add_new_task,
    description="""
    Use this tool when you need to create and add a new task to the project management database.
    It requires all of the following arguments:
    - title (string): The title of the new task.
    - description (string): A detailed description for the new task.
    - project_id (integer): The ID of the project the task is associated with.
    - assignee_id (integer): The ID of the user assigned to complete the task.
    """
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
    tools = [add_task_tool]

    # --- Create the Agent Prompt Template ---
    # This prompt guides the agent's reasoning process.
    prompt_template = """
    You are an assistant that helps manage tasks.
    Respond to the user's request using the available tools.

    TOOLS:
    ------
    {tools}

    To use a tool, please use the following format:

    Thought: Do I need to use a tool? Yes
    Action: The action to take. Should be one of [{tool_names}]
    Action Input: The input to the action
    Observation: The result of the action

    When you have a response to say to the user, or if you don't need to use a tool, you MUST use the format:

    Thought: Do I need to use a tool? No
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
    print("Ask me to add a task. For example: 'Add a task to fix the login bug for project 1 and assign it to user 2.'")
    print("Type 'exit' or 'quit' to end.")

    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ["exit", "quit"]:
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
