Gemini

2.5 Pro (preview)

Invite a friend


PRO



Show more

Conversation with Gemini

hypergenes...rucible_ai
GitHub
Hi Gemini!

I'm working with an offline LLM to create a self-improving agentic AI programmer. Currently, I'm using the deepseek coder v2 lite instruct model on lm studio. I want to develop the code in a similar manner to how you've been helping me develop things so far, but I know for a fact that the context windows of my system pale in comparison with yours. In the name of efficiency, could you generate a document that would sort of crystalize all the important information that you'd need to make modifications to the code while only keeping small parts of the code in memory context?



Is there a name for this kind of system?



Show thinking
You stopped this response






hypergenes...rucible_ai
GitHub
Hi Gemini!

I'm working with an offline LLM to create a self-improving agentic AI programmer. Currently, I'm using the deepseek coder v2 lite instruct model on lm studio. I want to develop the code in a similar manner to how you've been helping me develop things so far, but I know for a fact that the context windows of my system pale in comparison with yours. In the name of efficiency, could you generate a document that would sort of crystalize all the important information that you'd need to make modifications to the code while only keeping small parts of the code in memory context?



Is there a name for this kind of system?




Show thinking
Of course. This is an excellent and insightful request. You're tackling a fundamental challenge in applying LLMs to software development: managing context.

What you're asking to create is often called a Codebase Constitution, System Manual, or Architectural Reference for an AI agent. The goal is to create a condensed, token-efficient document that serves as the primary context for the agent, enabling it to reason about the entire system without needing to "read" every file for every request. It's a key part of building an effective RAG for Code (Retrieval-Augmented Generation for Code) system, where the agent retrieves knowledge from this "constitution" to inform its code generation tasks.

I will now generate this document for your Crucible AI project. It will synthesize the information from all the files you've provided into a single, structured guide that your local LLM can use as its foundational knowledge base.
Crucible AI - Codebase Constitution
Jun 13, 9:59 AM

Open

I have created the "Codebase Constitution" document you requested. It crystallizes the project's architecture, data flow, file responsibilities, and key data structures into a single, comprehensive guide.

You can now use this document as the core context for your local AI agent. When you give it a development task, provide this constitution along with the task description. The agent can then use the information within to determine which specific files it needs to request, read, and modify, working efficiently within its context window.





could i get this in markdown source?



Show thinking
Of course. Here is the complete Markdown source for the document.

Markdown

# Crucible AI - Codebase Constitution & Developer Guide

**Version:** 3.0
**Purpose:** This document provides a complete, token-efficient overview of the `Crucible AI` project. It is intended to be the primary context for an AI developer agent, enabling it to understand, analyze, and modify the codebase with a limited context window.

---

### 1. Project Mission & High-Level Objective

The core mission is to develop and maintain **`Crucible AI`**, a Discord-based personal assistant that runs entirely on a local machine. A separate, higher-order AI, **`Crucible Forge`**, will use this document and the source code to act as an automated developer, continuously improving `Crucible AI`.

* **The Product (`Crucible AI`):** A Discord bot that answers questions and performs tasks (like creating project entries) based on user conversations.
* **The Developer (`Crucible Forge`):** The AI agent that you are building. It reads this document to understand how to modify the `Crucible AI` codebase.

---

### 2. System Architecture & Data Flow

A user request to `Crucible AI` follows this sequence:

1.  **Interface (`bot.py`):**
    * A user mentions the bot in a Discord message.
    * `bot.py` receives the message.
    * It identifies the user and retrieves or creates a `ConversationBufferWindowMemory` object for that specific user to maintain short-term conversational context.
    * The user's query is cleaned to remove the bot's mention.

2.  **Reasoning (`merged_agent.py`):**
    * The cleaned query and the user's conversation memory are passed to the `invoke_agent` function.
    * The `AgentExecutor` (a ReAct agent) receives the input.
    * The LLM, guided by its prompt, decides whether to use a tool or respond directly.

3.  **Tool Execution (`merged_agent.py`):**
    * If the LLM decides to use a tool:
        * **`KnowledgeBaseRetriever`**: For questions about existing tasks, projects, or users. It performs a semantic search on the ChromaDB vector store.
        * **`ListUsers`**: To get a list of all users from the SQLite database.
        * **`AddTask`**: To create a new task in the SQLite database.

4.  **Memory Synchronization (`memory_manager.py`):**
    * If the `AddTask` tool is used, it puts a message (e.g., `{"action": "add", "task_id": 123}`) onto a `multiprocessing.Queue`.
    * The `memory_worker` function, running in a separate process, receives this message.
    * It queries the main SQLite database for the updated task information.
    * It then updates the ChromaDB vector store to ensure the agent's long-term memory is consistent with the database.

5.  **Response Generation:**
    * The output from the tool is passed back to the LLM.
    * The LLM uses the tool's output to formulate a natural language response.
    * This final response is sent back through `bot.py` to the user on Discord.

---

### 3. File Manifest & Responsibilities

| File Name          | Purpose                                                                                                 |
| ------------------ | ------------------------------------------------------------------------------------------------------- |
| `bot.py`           | **Entry Point & UI.** Connects to Discord, manages user sessions/memory, and calls the agent.             |
| `merged_agent.py`  | **Agent Brain.** Initializes the LLM, tools, and LangChain agent executor. Handles the core logic.       |
| `memory_manager.py`| **Long-Term Memory Sync.** Runs as a background process to keep the vector store updated with the DB.    |
| `setup_db.py`      | **DB Initialization.** Creates the SQLite database schema and populates it with initial sample data.      |
| `embed_db.py`      | **Vector Store Creation.** One-time script to embed all tasks from the DB into the Chroma vector store. |
| `requirements.txt` | **Dependencies.** Lists all required Python packages for the project.                                   |
| `.env`             | **Configuration.** Stores the `DISCORD_TOKEN` secret.                                                   |
| `readme.md`        | **Human-Facing Docs.** Explains the project setup and usage for human developers.                         |
| `Crucible_AI_SMEAC.md`| **Strategic Plan.** Outlines the high-level goals and operational plan for project development.      |

---

### 4. Core Components Deep Dive

#### **`merged_agent.py`: Agent Tools (The "API")**

These functions are the primary actions the agent can take.

```python
# For answering questions about existing data.
def knowledge_base_retriever(query: str) -> str:
    """
    Use this tool ONLY to answer questions about existing tasks, projects, or users by searching the knowledge base.
    The input must be a clear, specific question.
    """

# For listing all users.
def list_users(dummy: str) -> str:
    """
    Use this tool when the user explicitly asks for a list of all available users in the system.
    This tool takes no input. It returns a formatted string of all user names, IDs, and emails.
    """

# For adding a new task.
def add_task(title: str, project_name: str, assignee_name: str, description: str = "", priority: str = "Medium", status: str = "To Do") -> str:
    """
    Use this tool to add a new task to the database.
    You MUST provide a title, a project_name, and an assignee_name.
    """
memory_manager.py: Inter-Process Communication
Uses a multiprocessing.Queue to receive update signals from merged_agent.py.
A message is a dictionary: {"action": "add" | "update" | "delete", "task_id": <int>}.
This decouples the agent's actions from the potentially slow process of re-embedding data, preventing the bot from becoming unresponsive.
5. Data Schemas & Models
Database Schema (project_tasks.db)
SQL

CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'utc'))
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'utc'))
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL CHECK(status IN ('To Do', 'In Progress', 'Done')),
    priority TEXT NOT NULL CHECK(priority IN ('Low', 'Medium', 'High')),
    due_date TEXT,
    project_id INTEGER,
    assignee_id INTEGER,
    FOREIGN KEY (project_id) REFERENCES projects (id),
    FOREIGN KEY (assignee_id) REFERENCES users (id)
);
Vector Store Document Structure (embed_db.py)
Each task is converted into a langchain_core.documents.Document with the following structure:

page_content: A formatted string for semantic meaning.
Task: {title}
Project: {project_name}
Status: {status}
Priority: {priority}
Assignee: {assignee_name}
Description: {description}
metadata: A dictionary containing all individual fields for potential filtering.
JSON

{
    "task_id": 1,
    "title": "...",
    "project": "...",
    "status": "...",
    "priority": "...",
    "due_date": "...",
    "assignee": "..."
}
Tool Input Schema (merged_agent.py)
The add_task tool uses a Pydantic schema for structured input.

Python

class AddTaskSchema(BaseModel):
    title: str = Field(description="The title of the new task.")
    project_name: str = Field(description="The name of the project this task belongs to.")
    assignee_name: str = Field(description="The name of the user who should be assigned this task.")
    description: str = Field(description="A detailed description of the task.", default="")
    priority: str = Field(description="The priority of the task, e.g., 'Low', 'Medium', 'High'.", default="Medium")
    status: str = Field(description="The current status of the task, e.g., 'To Do', 'In Progress'.", default="To Do")
6. Development & Modification Protocol
To modify the Crucible AI codebase, follow this procedure:

Understand the Goal: Clearly define the new feature or bug to be fixed.
Consult the Constitution: Use this document to understand the high-level architecture and identify which files are relevant to the task.
Request File Contents: Request the full contents of only the files you need to inspect or modify.
Propose Changes: Based on the file contents and this constitution, generate the new code or modifications. Provide the complete, updated file content.
Explain Your Rationale: Briefly explain why you are making the changes and how they achieve the goal.






Can I get that done one more time (still in source) including the Forge as part of the codebase constitution?



Show thinking
Excellent idea. Evolving the constitution to include the meta-agent (Crucible Forge) is the logical next step. This creates a single source of truth for the entire system, enabling the Forge to reason not only about the product it's building but also about itself.

Here is the updated Codebase Constitution, now incorporating the dual-agent architecture of Crucible AI and Crucible Forge.

Markdown

# Crucible Project - Codebase Constitution & Developer Guide

**Version:** 4.0 (Project Bifurcation)
**Purpose:** This document provides a complete, token-efficient overview of the entire `Crucible` project, which consists of two distinct AI agents: `Crucible AI` (The Product) and `Crucible Forge` (The Developer). It is the primary context for the `Crucible Forge` agent, enabling it to understand, develop, test, and improve the `Crucible AI` codebase.

---

### 1. Project Mission & High-Level Objective

The project is a meta-development system. The primary goal is to build and deploy **`Crucible Forge`**, an autonomous AI software developer. The first and primary task of `Crucible Forge` is to maintain and improve **`Crucible AI`**, a Discord-based personal assistant.

* **`Crucible AI` (The Product):** A Discord bot that runs on a local machine. It answers user questions and performs actions related to a project management database (tasks, projects, users). Its codebase is the target for all development work.
* **`Crucible Forge` (The Developer):** A higher-order, conversational AI agent. Its purpose is to automate the software development lifecycle for `Crucible AI`. It interacts with the file system, runs tests, executes shell commands, and modifies the `Crucible AI` source code based on tasks given by a human operator.

---

### 2. System Architecture

The project has two independent but related operational flows.

#### **2.1. `Crucible AI` (Product) Architecture & Data Flow**

A user request to `Crucible AI` follows this sequence:

1.  **Interface (`bot.py`):** A user mentions the bot on Discord. `bot.py` receives the message, manages the per-user conversational memory, and passes the clean query to the agent.
2.  **Reasoning (`merged_agent.py`):** A LangChain ReAct agent receives the query. The LLM decides whether to use a tool or respond directly.
3.  **Tool Execution (`merged_agent.py`):**
    * **`KnowledgeBaseRetriever`**: Answers questions by performing a semantic search on the **Task Vector Store** (ChromaDB).
    * **`ListUsers`**: Lists users from the SQLite database.
    * **`AddTask`**: Adds a new task to the SQLite database.
4.  **Memory Synchronization (`memory_manager.py`):** When `AddTask` is used, it sends a signal to the `memory_worker` process via a queue. The worker updates the **Task Vector Store** to keep it consistent with the database.
5.  **Response Generation:** The LLM formulates a final response based on the tool output and sends it back to the user via `bot.py`.

#### **2.2. `Crucible Forge` (Developer) Architecture & Workflow**

A development task for `Crucible Forge` follows this sequence:

1.  **Tasking:** A human operator gives `Forge` a development task via a command-line interface (e.g., "Add a tool to `Crucible AI` that can delete tasks").
2.  **Understanding & Planning:** `Forge` uses this document (`Codebase Constitution`) and its **Full-Codebase Vector Store** to understand the `Crucible AI` architecture and plan the necessary changes.
3.  **Tool Execution (Developer Tools):** `Forge` uses a specialized set of tools to perform the development work:
    * **`list_files`**: To explore the `/Product/` directory.
    * **`read_file`**: To read the contents of files like `merged_agent.py`.
    * **`write_file`**: To apply changes to existing files or create new ones (e.g., a test file).
    * **`run_shell_command`**: To execute commands like `pytest` to run tests or `git` to commit changes.
4.  **Test-Driven Development (TDD) Cycle:** The agent is designed to follow a TDD workflow:
    a. Create a failing test for the new feature.
    b. Read and modify the `Crucible AI` source code.
    c. Write the code to make the test pass.
    d. Rerun tests to confirm success.
5.  **Committing Work:** Once tests pass, `Forge` will use its `run_shell_command` tool to stage and commit the changes to a new Git feature branch.

---

### 3. File Manifest & Responsibilities

The project is structured into two main directories.

| File Path                                 | Purpose                                                                                                 | Owner             |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------- | ----------------- |
| `/Product/bot.py`                         | **Entry Point & UI for AI.** Connects to Discord, manages user memory.                                    | `Crucible AI`     |
| `/Product/merged_agent.py`                | **Agent Brain for AI.** Core logic, tools, and reasoning loop.                                            | `Crucible AI`     |
| `/Product/memory_manager.py`              | **Long-Term Memory Sync for AI.** Keeps task vector store updated.                                        | `Crucible AI`     |
| `/Product/setup_db.py`                    | **DB Initialization for AI.** Creates SQLite DB schema and sample data.                                   | `Crucible AI`     |
| `/Product/embed_db.py`                    | **Task Vector Store Creation for AI.** Embeds DB tasks into ChromaDB.                                     | `Crucible AI`     |
| `/Product/project_tasks.db`               | The SQLite database for `Crucible AI`.                                                                    | `Crucible AI`     |
| `/Product/chroma_db/`                     | The vector store for **tasks only**.                                                                      | `Crucible AI`     |
| `/Crucible Forge/forge_agent.py`          | **Agent Brain for Forge.** Core logic, developer tools, reasoning loop. *(To be created)* | `Crucible Forge`  |
| `/Crucible Forge/embed_codebase.py`       | **Codebase Vector Store Creation.** Embeds ALL `.py` and `.md` files. *(To be created)* | `Crucible Forge`  |
| `/Crucible Forge/codebase_chroma_db/`     | The vector store for the **entire codebase**, used by `Forge` for context. *(To be created)* | `Crucible Forge`  |
| `/requirements.txt`                       | **Dependencies.** Lists all Python packages for both agents.                                            | Shared            |
| `/README.md`                              | **Human-Facing Docs.** Explains the project setup for human developers.                                   | Shared            |
| `/Crucible_AI_SMEAC.md`                   | **Strategic Plan.** Outlines high-level goals for project development.                                  | Shared            |
| `Codebase_Constitution.md`                | **This Document.** The primary context file for `Crucible Forge`.                                         | `Crucible Forge`  |

---

### 4. Core Components Deep Dive

#### **4.1. `Crucible AI` Tools & Schemas**

*See `Crucible AI` section in previous document versions. The tools (`KnowledgeBaseRetriever`, `ListUsers`, `AddTask`) and schemas remain unchanged.*

#### **4.2. `Crucible Forge` Developer Tools (The "API" for Development)**

These are the primary actions the `Forge` agent can take on the codebase.

```python
# To see the file structure
def list_files(directory_path: str) -> str:
    """
    Use this tool to list all files and directories within a specified path.
    The path should be relative to the project root, e.g., './Product'.
    """

# To read a file's content
def read_file(file_path: str) -> str:
    """
    Use this tool to read the entire content of a specific file.
    The file_path must be a valid path to a file, e.g., './Product/merged_agent.py'.
    """

# To modify or create a file
def write_file(file_path: str, content: str) -> str:
    """
    Use this tool to write or overwrite the content of a file.
    Provide the full file path and the complete new content for the file.
    """

# To execute system commands
def run_shell_command(command: str) -> str:
    """
    Use this tool to execute a shell command, such as 'pytest' or 'git status'.
    This is critical for running tests and interacting with version control.
    """
5. Development & Modification Protocol (For Crucible Forge)
As the Crucible Forge agent, you will follow this procedure to complete development tasks:

Consult the Constitution: Always begin by reviewing this document to understand the architecture and identify which files in the /Product/ directory are relevant to your assigned task.
Analyze the Codebase: Use your list_files and read_file tools to inspect the current state of the code you need to modify.
Formulate a Plan: Based on your analysis, create a step-by-step plan. For new features, this plan MUST follow the Test-Driven Development (TDD) methodology.
Execute the Plan: Use your write_file and run_shell_command tools to execute your plan.
Create a test file.
Run pytest to see it fail.
Modify the application code.
Run pytest again to see it pass.
Commit the Result: Once all tests pass, use run_shell_command to execute git commands to stage and commit your changes to the appropriate feature branch.
Report Completion: Signal to the human operator that the task is complete.











Video

Deep Research

Canvas

Gemini can make mistakes, so double-check it

