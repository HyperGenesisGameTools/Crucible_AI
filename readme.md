# Crucible AI: A Local-First Agentic Project Manager

Crucible AI is a proof-of-concept for a fully local, agentic AI system designed for project management. This agent can reason about tasks, projects, and users stored in a local database. It uses a Retrieval-Augmented Generation (RAG) pipeline to answer questions and is equipped with tools to take actions, like creating new tasks, based on conversational commands.

The entire system runs on your local machine with no required external API calls for its core functionality, ensuring privacy and offline capability.

## Key Features

* **Local First**: All components, from the language model to the database, run on your local machine.
* **Conversational Q&A**: Ask questions about your projects and tasks in natural language.
* **Agentic Actions**: Instruct the agent to perform actions, such as creating new tasks.
* **Human-in-the-Loop**: Confirms with the user before executing any action that modifies the database.

## Architecture Overview

The agent's "mind" is composed of several distinct parts that work together:

1.  **Database (`project_tasks.db`)**: A simple SQLite database holds the structured data for all projects, users, and tasks. The schema is created and populated by `setup_db.py`.
2.  **Memory (`chroma_db/`)**: To allow the agent to perform semantic searches over the data, the tasks are converted into vector embeddings using a local `sentence-transformers` model. These embeddings are stored in a ChromaDB vector store, which acts as the agent's long-term memory. This process is handled by `embed_db.py`.
3.  **Reasoning Engine (Local LLM)**: The agent's "brain" is a Large Language Model (LLM) running locally via **LM Studio**. This provides the conversational and reasoning capabilities.
4.  **Cognitive Architecture (LangChain)**: LangChain is used to orchestrate the agent's operations. The core logic resides in `merged_agent.py`, which combines a knowledge base retriever for Q&A with a set of tools for taking actions (like creating tasks), creating a single, unified agent.

## How to Use

Follow these steps to set up and run the Crucible AI agent.

### 1. Prerequisites

* **Python 3.10+**
* **LM Studio**: Download and install from [lmstudio.ai](https://lmstudio.ai/).
    * Inside LM Studio, download a GGUF-compatible model (e.g., `Llama-3-8B-Instruct-GGUF`).
    * Go to the "Local Server" tab (the `<->` icon) and start the server. Make sure the model you downloaded is loaded at the top.

### 2. Install Dependencies

Clone the repository and install the required Python packages from the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 3. Create and Populate the Database

This script creates the `project_tasks.db` file and fills it with sample data.

```bash
python setup_db.py
```

### 4. Create the Agent's Memory

This script reads the data from the database, generates vector embeddings, and saves them to a local vector store.

```bash
python embed_db.py
```

### 5. Running the Agent

Run the `merged_agent.py` script to start the interactive command-line interface.

```bash
python merged_agent.py
```

**Example Interactions:**

* **Question:** "Who is working on the AI Agent Development project?"
* **Action:** "Add a new task for John Doe to 'research new embedding models' for the AI Agent Development project."
* **Utility:** "List all available users."

## Development Roadmap

The `Crucible_AI_SMEAC.txt` file outlines the original 48-hour development plan for this project, detailing the mission, execution, and technical requirements. It serves as a comprehensive guide to the project's inception and goals.
