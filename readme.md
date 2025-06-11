# Crucible AI (V0.2): A Discord-Based Personal Assistant

Crucible AI (V0.2 "Cognitive Shield") is the evolution of a local-first agentic system, now designed to operate as a personal assistant via Discord. The agent can reason about tasks, projects, and users stored in a local database. It uses a Retrieval-Augmented Generation (RAG) pipeline to answer questions and is equipped with tools to take actions, like creating new tasks, based on conversational commands from multiple users in a Discord server.

The entire system runs on your local machine with no required external API calls for its core functionality, ensuring privacy and offline capability. The Discord bot acts as a remote control for your self-hosted AI.

## Key Features

* **Local First**: All core components—the language model, database, and vector store—run on your local machine.
* **Discord Interface**: Interact with the agent through a Discord bot, which can handle multiple users simultaneously.
* **Conversational Q&A**: Ask questions about your projects and tasks in natural language.
* **Agentic Actions**: Instruct the agent to perform actions, such as creating new tasks.
* **Multi-Component Memory**:
    * **Long-Term Memory**: A ChromaDB vector store allows for semantic searching of tasks.
    * **Short-Term Memory**: A per-user conversational context ensures the agent remembers the flow of each unique conversation.

## Architecture Overview

The agent's "mind" is composed of several distinct parts that work together:

1.  **User Interface (`bot.py`)**: A Discord bot that serves as the primary interface. It listens for mentions, manages user-specific conversational context, and relays information to and from the core agent.
2.  **Database (`project_tasks.db`)**: A simple SQLite database holds the structured data for all projects, users, and tasks. The schema is created and populated by `setup_db.py`.
3.  **Memory (`chroma_db/`)**: The agent's long-term memory. Task data from the database is converted into vector embeddings and stored in a ChromaDB vector store, enabling semantic search capabilities. This process is handled by `embed_db.py`.
4.  **Reasoning Engine (Local LLM)**: The agent's "brain" is a Large Language Model (LLM) running locally via **LM Studio**. This provides the conversational and reasoning capabilities.
5.  **Cognitive Architecture (LangChain)**: LangChain is used to orchestrate all operations. The core logic in `merged_agent.py` combines a knowledge base retriever with a set of tools, creating a unified, powerful agent.

## How to Use

Follow these steps to set up and run the Crucible AI agent.

### 1. Prerequisites

* **Python 3.10+**
* **LM Studio**: Download and install from [lmstudio.ai](https://lmstudio.ai/).
    * Inside LM Studio, download a GGUF-compatible model (e.g., `Llama-3-8B-Instruct-GGUF`).
    * Go to the "Local Server" tab (`<->` icon) and start the server. Ensure the model you downloaded is loaded at the top.
* **Discord Bot Account**:
    * Go to the [Discord Developer Portal](https://discord.com/developers/applications).
    * Create a "New Application".
    * Go to the "Bot" tab, click "Add Bot", and grant it "Message Content Intent" under "Privileged Gateway Intents".
    * Click "Reset Token" to get your bot's token. **Save this token.**
    * Go to the "OAuth2" -> "URL Generator" tab, select the `bot` scope, and in the "Bot Permissions" that appear, select `Send Messages` and `Read Message History`.
    * Copy the generated URL, paste it into your browser, and invite the bot to your server.

### 2. Install Dependencies

Clone the repository and install the required Python packages.

```bash
git clone <repository_url>
cd <repository_directory>
pip install -r requirements.txt
```

### 3. Configure Environment

Create a file named `.env` in the project's root directory. Add your Discord bot token to it:

```
DISCORD_TOKEN="YOUR_BOT_TOKEN_HERE"
```

### 4. Create and Populate the Database

This script creates the `project_tasks.db` file and fills it with sample data.

```bash
python setup_db.py
```

### 5. Create the Agent's Memory

This script reads the data from the database, generates vector embeddings, and saves them to the local vector store.

```bash
python embed_db.py
```

### 6. Running the Agent

Start the bot. Make sure your LM Studio server is running first.

```bash
python bot.py
```

Once the console says `Crucible AI Agent is ready and listening`, go to your Discord server and mention the bot in a message.

**Example Interactions:**

* `@YourBotName who is working on the AI Agent Development project?`
* `@YourBotName add a new task for Jane Doe to 'set up project roadmap' for the Website Redesign project.`
* `@YourBotName list all available users.`
