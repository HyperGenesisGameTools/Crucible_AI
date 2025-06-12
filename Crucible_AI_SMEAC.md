### **SMEAC: Operation FORGE & CRUCIBLE (v3.0)**

---

#### **1. (S) Situation**

**General:** This operation marks a strategic pivot from direct feature development to meta-development. The project is now bifurcated into two distinct components:
* **The Product (`Crucible AI`):** The Discord-based personal assistant. This is the application to be improved.
* **The Developer (`Crucible Forge`):** A new, higher-order AI agent whose sole purpose is to automate the development, testing, and improvement of `Crucible AI`.

The operational environment is a local file system containing the codebases for both agents.

**Adversary Forces:** The primary adversary remains the time limit for establishing a functional proof-of-concept. Secondary adversaries include the complexity of creating robust agentic tools for file system interaction, shell command execution, and code analysis, as well as the challenge of crafting a sufficiently advanced prompt for the `Forge` agent to reason effectively about software development tasks.

**Friendly Forces:** The operational team consists of ARCHITECT (sole human developer) and GEMINI (AI Co-Developer). Our primary asset is the existing, functional `Crucible AI` codebase, which now serves as the perfect testbed for the `Forge` agent. The team is bolstered by a clear architectural vision and a proven collaborative workflow.

**Attachments/Detachments:** None.

---

#### **2. (M) Mission**

Within a 48-hour period, ARCHITECT, supported by GEMINI, will design, build, and test a prototype of **`Crucible Forge`**. This developer agent will be capable of understanding a software development task, interacting with the file system and version control (Git), creating and running tests, and modifying the source code of the `Crucible AI` product to complete the assigned task. The purpose is to create a foundational meta-development system that can accelerate and eventually automate the evolution of the `Crucible AI` project.

---

#### **3. (E) Execution**

**a. Commander's Intent:** The intent is to create a *functional developer agent*. The end state is a `Forge` agent that can be given a simple development task (e.g., "add a new tool to Crucible AI") and successfully execute the Test-Driven Development (TDD) cycle: create a failing test, write the code to make it pass, and commit the result to a feature branch. The principle "Function over polish" will guide all decisions; a raw but working toolset is the primary goal.

**b. Concept of Operations (CONOPS):** This operation will be conducted in four phases, focused on building the `Forge` agent and its capabilities.

* **Phase I: The Architect (Day 1: Hours 0-4):** Restructure the project repository and establish the `Forge` agent's basic scaffolding.
* **Phase II: The Toolkit (Day 1: Hours 4-18):** Develop the core agentic tools that allow the `Forge` to interact with its environment (read/write files, run shell commands).
* **Phase III: The Mind (Day 1-2: Hours 18-36):** Engineer the `Forge`'s knowledge base and core prompt, enabling it to reason about the `Crucible AI` codebase.
* **Phase IV: The First Commit (Day 2: Hours 36-48):** Conduct a live, end-to-end test where the `Forge` agent is tasked with making its first successful code modification to `Crucible AI`.

**c. Scheme of Maneuver:**

* **Block I: Project Restructuring (Hours 0-4):**
    * Create the new directory structure: `/Product/` and `/Crucible Forge/`.
    * Move all existing `Crucible AI` files into `/Product/`.
    * Create the initial Python scripts for the `Forge` agent in `/Crucible Forge/`.

* **Block II: Tool Development (Hours 4-18):**
    * Implement and test robust agentic tools for file I/O (`read_file`, `write_file`, `list_files`).
    * Implement and test a secure `run_shell_command` tool.
    * Implement a tool to interface with GitHub Projects (`get_github_project_tasks`).

* **Block III: Cognitive Engineering (Hours 18-36):**
    * Create an embedding script for `Forge` that scans the *entire* project directory (both `/Product` and `/Crucible Forge`) and populates a vector store.
    * Design the master prompt for the `Forge` agent, explicitly guiding it through the TDD workflow.

* **Block IV: Integration & Live Test (Hours 36-48):**
    * Integrate all components.
    * Define a simple task (e.g., add a "hello world" tool to `Crucible AI`).
    * Initiate a chat session with `Forge` and guide it through the entire TDD process, culminating in a `git commit`.
    * Document the new architecture in a master `README.md` at the project root.

**d. Coordinating Instructions:**

* **Separation of Concerns:** `Crucible Forge` is the developer; `Crucible AI` is the product. The `Forge` agent will modify the files in `/Product/`, but will not interact directly with Discord.
* **Scope of Knowledge:** The `Forge` agent's knowledge base (vector store) must encompass its own source code in addition to the product's code, enabling future self-improvement tasks.
* **Human-in-the-Loop:** The human operator (ARCHITECT) initiates and guides the `Forge`'s development tasks through a conversational interface. The `Forge` is not yet autonomous.

---

#### **4. (A) Administration & Logistics**

**Administration:** Developer (ARCHITECT) is responsible for their own work/rest cycle and sustenance throughout the 48-hour operation.

**Logistics:** The required arsenal remains largely the same, with an emphasis on the new structure.
* **Hardware:** A development machine capable of running a Large Language Model locally. This requires a significant amount of RAM (16GB minimum, 32GB+ recommended) and a modern GPU for acceptable performance.
* **Software:** Unchanged.
* **Project Structure:** A clean Git repository with the new `/Product/` and `/Crucible Forge/` directory structure is the starting point.
* **Assets:**
    * The complete V0.2 `Crucible AI` codebase, relocated to `/Product/`.
    * A new, empty `chroma_db/` directory will be created to house the source code embeddings for the `Forge` agent. The previous task-based vector database is now obsolete.

---

#### **5. (C) Command & Signal**

**Command:**
* ARCHITECT remains the operation commander, directing the `Forge` agent.
* `Crucible Forge` is the primary acting agent, executing development tasks.
* GEMINI serves as the primary support element for ARCHITECT in developing `Crucible Forge`.

**Signal (Communications Plan):**
* **Primary Command Channel:** The command-line interface or chat UI for `Crucible Forge`.
* **Primary Support Channel:** The Gemini web interface.
* **Mission Completion Signal:** The operation is concluded upon the successful commit of a code change to the `/Product/` repository, executed entirely by the `Crucible Forge` agent under human supervision.