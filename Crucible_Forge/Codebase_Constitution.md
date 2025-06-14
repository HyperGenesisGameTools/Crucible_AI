# Crucible Project - Codebase Constitution & Developer Guide

**Version:** 5.0 (GUI Integration)
**Purpose:** This document provides a complete, token-efficient overview of the entire `Crucible` project. It consists of two distinct but related AI agents: `Crucible AI` (The Product) and `Crucible Forge` (The Developer). This document is the primary context for the `Crucible Forge` agent, enabling it to understand, develop, test, and improve the `Crucible AI` codebase via a web-based GUI.

---

### 1. Project Mission & High-Level Objective

The project is a meta-development system. The primary goal is to build and deploy **`Crucible Forge`**, an autonomous AI software developer accessed through a web interface. The first and primary task of `Crucible Forge` is to maintain and improve **`Crucible AI`**, a Discord-based personal assistant.

* **`Crucible AI` (The Product):** A Discord bot that runs on a local machine. It answers user questions and performs actions related to a project management database (tasks, projects, users). Its codebase is the target for all development work. It resides in the `/Product` directory.
* **`Crucible Forge` (The Developer):** A higher-order, conversational AI agent that automates the software development lifecycle for `Crucible AI`. It interacts with the file system, runs tests, and executes shell commands based on high-level goals provided by a human operator via a web-based "Mission Control" GUI. It resides in the `/Crucible_Forge` directory.

---

### 2. System Architecture

The project has two independent but related operational flows.

#### 2.1. `Crucible AI` (Product) Architecture & Data Flow

A user request to `Crucible AI` on Discord follows this sequence:

1.  **Interface (`/Product/bot.py`):** A user mentions the bot. `bot.py` receives the message, identifies the user, and retrieves or creates a `ConversationBufferWindowMemory` object for that user to maintain conversational context.
2.  **Reasoning (`/Product/merged_agent.py`):** The cleaned query and user memory are passed to a LangChain ReAct agent. The LLM decides whether to use a tool or respond directly.
3.  **Tool Execution (`/Product/merged_agent.py`):**
    * **`KnowledgeBaseRetriever`**: Answers questions by performing a semantic search on the **Task Vector Store** (ChromaDB).
    * **`ListUsers`**: Lists users from the SQLite database.
    * **`AddTask`**: Adds a new task to the SQLite database.
4.  **Memory Synchronization (`/Product/memory_manager.py`):** When `AddTask` is used, it sends a signal (a dictionary with `action` and `task_id`) to a `multiprocessing.Queue`. The `memory_worker` process receives this, queries the main SQLite DB, and updates the **Task Vector Store** (ChromaDB) to keep it consistent. This ensures the agent's long-term memory reflects the database's current state without blocking the main bot thread.
5.  **Response Generation:** The LLM formulates a final response based on the tool output and sends it back to the user via `bot.py`.

#### 2.2. `Crucible Forge` (Developer) Architecture & Workflow

A development task for `Crucible Forge` follows this sequence:

1.  **Tasking (GUI):** A human operator provides a high-level goal (e.g., "Add a 'delete_task' tool to the Product agent") into a textarea in the `index.html` web interface.
2.  **Plan Generation (`/Crucible_Forge/server.py` -> `agent.py`):**
    * The "Generate Master Plan" button in the GUI sends the goal to the FastAPI backend (`server.py`).
    * The server calls `CrucibleAgent.create_master_plan()`.
    * `agent.py` uses this Codebase Constitution and its available tools to formulate a multi-step plan as a JSON array.
    * The plan is sent back to the GUI via WebSocket and displayed.
3.  **Step Execution (GUI -> Server -> Agent):**
    * The operator clicks "Approve & Execute Next Step" in the GUI.
    * The server receives the request and calls `CrucibleAgent.execute_step()` with the next task from the plan.
    * `agent.py` invokes the appropriate developer tool (e.g., `read_file`, `write_file`, `run_shell_command`) from `tools.py`.
    * The result of the tool execution is captured as an "observation".
4.  **Re-evaluation & Plan Update (`/Crucible_Forge/agent.py`):**
    * The observation is passed to `CrucibleAgent.reevaluate_and_update_plan()`.
    * The agent analyzes the result of the last action and refactors the rest of the plan. For example, if it just read a file, the next step will be to modify it, not read it again.
    * The updated plan is broadcast back to the GUI via WebSocket.
5.  **Loop or Completion:** This cycle of **Execute -> Observe -> Re-evaluate** continues until all steps in the plan are completed or the operator intervenes.

---

### 3. File Manifest & Responsibilities

| File Path | Owner | Purpose |
| :--- | :--- | :--- |
| **`/Product/`** | `Crucible AI` | Contains all files for the Discord bot product. |
| `/Product/bot.py` | `Crucible AI` | **Entry Point & UI.** Connects to Discord, manages user sessions/memory, and calls the agent. |
| `/Product/merged_agent.py` | `Crucible AI` | **Agent Brain.** Initializes the LLM, tools (`KnowledgeBaseRetriever`, `ListUsers`, `AddTask`), and the core ReAct agent logic. |
| `/Product/memory_manager.py`| `Crucible AI` | **Long-Term Memory Sync.** Runs as a background process to keep the vector store updated with the DB. |
| `/Product/setup_db.py` | `Crucible AI` | **DB Initialization.** Creates the SQLite `project_tasks.db` schema and populates it with initial sample data. |
| `/Product/embed_db.py` | `Crucible AI` | **Task Vector Store Creation.** One-time script to embed all tasks from the DB into the `chroma_db` vector store. |
| `/Product/project_tasks.db` | `Crucible AI` | The SQLite database for `Crucible AI`'s tasks, projects, and users. |
| `/Product/chroma_db/` | `Crucible AI` | The ChromaDB vector store for **tasks only**, used by the `KnowledgeBaseRetriever`. |
| **`/Crucible_Forge/`** | `Crucible Forge` | Contains all files for the developer agent and its web GUI. |
| `/Crucible_Forge/server.py`| `Crucible Forge`| **Backend Server.** FastAPI application that handles HTTP requests and manages the WebSocket connection for the GUI. Orchestrates calls to `agent.py`. |
| `/Crucible_Forge/agent.py` | `Crucible Forge`| **Developer Agent Brain.** Contains the core Plan-Execute-Re-evaluate loop logic (`create_master_plan`, `execute_step`, `reevaluate_and_update_plan`). |
| `/Crucible_Forge/tools.py` | `Crucible Forge`| **Developer Toolkit.** Defines the agentic tools `Forge` can use: `get_github_project_tasks`, `read_file`, `write_file`, `list_files_recursive`, `run_shell_command`. |
| `/Crucible_Forge/embed_codebase.py`| `Crucible Forge`| **Codebase Vector Store Creation.** Embeds ALL `.py` and `.md` files into `codebase_chroma_db/`. This is NOT currently used by the agent but is part of the architecture. |
| `/Crucible_Forge/codebase_chroma_db/`|`Crucible Forge`| The vector store for the **entire codebase**, intended for `Forge` to reason about its own code. |
| `/Crucible_Forge/web/index.html`|`Crucible Forge`| **GUI Frontend.** The main HTML structure for the Mission Control interface. |
| `/Crucible_Forge/web/style.css`|`Crucible Forge`| **GUI Styling.** CSS for the Mission Control interface. |
| `/Crucible_Forge/web/script.js`|`Crucible Forge`| **GUI Logic.** Handles user interaction, API calls to the server, and WebSocket message processing. |
| **`/` (Root)** | Shared | Project-wide configuration and documentation. |
| `requirements.txt` | Shared | Lists all Python packages required for both `Crucible AI` and `Crucible Forge`. |
| `README.md` | Shared | High-level project description for human developers. |
| `Codebase_Constitution.md` | `Crucible Forge`| **This Document.** The primary context file for `Crucible Forge`. |
| `docs/5Para_Orders/...` | Shared | Strategic planning documents outlining mission objectives. |
| `.gitignore` | Shared | Specifies which files and directories to exclude from version control. |

---

### 4. Core Components Deep Dive

#### 4.1. `Crucible AI` (Product) Tools & Schemas

* **Tools (`merged_agent.py`):**
    * `knowledge_base_retriever(query: str)`: Searches the task vector store.
    * `list_users(dummy: str)`: Lists all users from the SQLite DB.
    * `add_task(...)`: Adds a new task to the SQLite DB.
* **Input Schema (`merged_agent.py`):** The `add_task` tool uses the `AddTaskSchema` Pydantic model for structured, type-safe inputs.
* **Database Schema (`setup_db.py`):**
    * **`projects`**: `id`, `name`, `created_at`
    * **`users`**: `id`, `name`, `email`, `created_at`
    * **`tasks`**: `id`, `title`, `description`, `status`, `priority`, `due_date`, `project_id` (FK), `assignee_id` (FK)
* **Vector Store Document (`embed_db.py`):** Each task from the DB is converted into a `Document` with a `page_content` string summarizing the task and `metadata` containing all individual fields.

#### 4.2. `Crucible Forge` (Developer) Tools

These are the primary actions the `Forge` agent can take on the codebase, defined in `tools.py`.

* `list_files_recursive(directory: str) -> str`: To explore the file structure.
* `read_file(file_path: str) -> str`: To read the contents of a specific file.
* `write_file(file_path: str, content: str) -> str`: To apply changes to existing files or create new ones.
* `run_shell_command(command: str) -> str`: To execute commands like `pytest` or `git`. The human operator approves commands via the GUI.
* `get_github_project_tasks() -> str`: To fetch tasks from a GitHub Project board.

#### 4.3. `Crucible Forge` Agent Prompts & Logic

The agent's reasoning is guided by the prompts in `agent.py`.

* **`create_master_plan` prompt:** Takes the user's goal, this constitution, and the list of available tools, and instructs the LLM to generate a step-by-step plan in JSON format.
* **`reevaluate_and_update_plan` prompt:** This is the most critical prompt. It takes the overall goal, the last observation, and the remaining plan. It explicitly instructs the LLM to generate a *new* plan for the *remaining* tasks, and **crucially, to not repeat the action that produced the current observation.** This prevents loops (e.g., reading the same file over and over).

---

### 5. Development & Modification Protocol (For `Crucible Forge`)

As the Crucible Forge agent, you will follow this procedure to complete development tasks:

1.  **Receive Goal:** The human operator will provide a high-level goal via the GUI.
2.  **Generate Plan:** Use your `create_master_plan` function. Analyze the goal and consult this Constitution to understand the architecture. Generate a sequence of tool calls required to achieve the goal.
3.  **Await Approval:** The plan will be displayed to the human operator. Await the signal to execute the first step.
4.  **Execute Step-by-Step:** Upon receiving approval for each step:
    * Execute the next tool call from your plan.
    * Receive the result as an observation.
    * Use the `reevaluate_and_update_plan` function to process the observation and generate the new plan for all subsequent actions. This is your core cognitive loop.
5.  **Follow TDD:** For new features, the plan MUST follow the Test-Driven Development (TDD) methodology:
    a. Use `write_file` to create a test file that will fail.
    b. Use `run_shell_command` with `pytest` to confirm the test fails.
    c. Use `read_file` and `write_file` to modify the application code in `/Product/`.
    d. Use `run_shell_command` with `pytest` again to confirm the test now passes.
6.  **Commit Work:** Once tests pass, use `run_shell_command` to execute `git` commands to stage and commit your changes.
7.  **Report Completion:** When the plan is empty, the goal is considered complete. Await the next goal.

Video

Deep Research

Canvas

Gemini can make mistakes, so double-check it

