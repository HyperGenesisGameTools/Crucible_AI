# Crucible AI: A Local-First Agentic Project Manager

Crucible AI is a proof-of-concept for a fully local, agentic AI system designed for project management. This agent can reason about tasks, projects, and users stored in a local database. It uses a Retrieval-Augmented Generation (RAG) pipeline to answer questions and is being expanded to take actions, like creating new tasks, based on conversational commands.

The entire system runs on your local machine with no required external API calls for its core functionality, ensuring privacy and offline capability.

## Architecture Overview

The agent's "mind" is composed of several distinct parts that work together:

1.  **Database (`project_tasks.db`):** A simple SQLite database holds the structured data for all projects, users, and tasks. The schema is created and populated by `setup_db.py`.
2.  **Memory (`chroma_db/`):** To allow the agent to perform semantic searches over the data, the tasks are converted into vector embeddings using a local `sentence-transformers` model. These embeddings are stored in a ChromaDB vector store, which acts as the agent's long-term memory. This process is handled by `embed_db.py`.
3.  **Reasoning Engine (Local LLM):** The agent's "brain" is a Large Language Model (LLM) running locally via **LM Studio**. This provides the conversational and reasoning capabilities.
4.  **Cognitive Loop (`main.py`):** LangChain is used to orchestrate the agent's operations. It connects the user's query to the **Reasoning Engine** and the **Memory**, creating a RAG pipeline that allows the agent to find relevant information and formulate an answer.

## How to Use

Follow these steps to set up and run the Crucible AI agent.

### 1. Prerequisites

* **Python 3.10+**
* **LM Studio:** Download and install from [lmstudio.ai](https://lmstudio.ai/).
    * Inside LM Studio, download a GGUF-compatible model (e.g., `Llama-3-8B-Instruct-GGUF`).
    * Go to the "Local Server" tab (the `<->` icon) and start the server. Make sure the model you downloaded is loaded at the top.

### 2. Install Dependencies

Clone the repository and install the required Python packages.

```
pip install -r requirements.txt
```

### 3. Create and Populate the Database

This script creates the `project_tasks.db` file and fills it with sample data.

```
python setup_db.py
```

### 4. Create the Agent's Memory

This script reads the data from the database, generates vector embeddings, and saves them to a local vector store.

```
python embed_db.py
```

### 5. Chat with the Agent

Now you can run the main application and start a conversation with your agent.

```
python main.py
```

The script will connect to your local LLM server. Once it's ready, you can ask questions about the project data.

**Example Questions:**

* "What tasks are currently in progress?"
* "Are there any high-priority tasks?"
* "Summarize the 'AI Agent Development' project."

## Next Steps: Agentic Actions

The current implementation allows the agent to answer questions (read-only). The next phase of development (Block IV) is to give the agent **tools** to act upon its environment, starting with the ability to create new tasks in the database through natural language commands.
