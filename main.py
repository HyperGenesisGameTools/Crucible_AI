import os
import sys
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# --- CONFIGURATION ---
# Point to the directory where you persisted your ChromaDB vector store
CHROMA_PERSIST_DIR = "./chroma_db"
# Specify the same embedding model used in your embed_db.py script
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
# Point to your local LM Studio server
LOCAL_LLM_URL = "http://localhost:1234/v1"
# Use a dummy API key for local servers
DUMMY_API_KEY = "lm-studio"
# The model name is often required, though it's managed by LM Studio
# You can often use "local-model" or the specific model identifier
MODEL_NAME = "local-model"

def format_docs(docs):
    """
    Helper function to format the retrieved documents into a single string.
    """
    return "\n\n".join(doc.page_content for doc in docs)

def main():
    """
    Main function to set up and run the RAG chat interface.
    """
    print("--- Initializing RAG Chat Interface ---")

    # --- 1. INITIALIZE THE CHAT MODEL ---
    # Connect to the local LLM running in LM Studio
    try:
        llm = ChatOpenAI(
            base_url=LOCAL_LLM_URL,
            api_key=DUMMY_API_KEY,
            model=MODEL_NAME,
            temperature=0.7, # Adjust for desired creativity
            streaming=True
        )
        print("Successfully connected to local LLM server.")
    except Exception as e:
        print(f"Error connecting to LLM server: {e}")
        sys.exit(1)


    # --- 2. LOAD EXISTING VECTOR STORE ---
    # Check if the ChromaDB directory exists
    if not os.path.exists(CHROMA_PERSIST_DIR):
        print(f"Error: ChromaDB directory not found at '{CHROMA_PERSIST_DIR}'")
        print("Please run the `embed_db.py` script first to create the vector store.")
        sys.exit(1)

    # Initialize the same embedding model used for storage
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    # Load the persisted ChromaDB
    vector_store = Chroma(
        persist_directory=CHROMA_PERSIST_DIR,
        embedding_function=embeddings
    )
    print(f"Successfully loaded vector store from '{CHROMA_PERSIST_DIR}'.")


    # --- 3. CREATE A RETRIEVER AND PROMPT TEMPLATE ---
    # Create a retriever from the vector store
    retriever = vector_store.as_retriever(search_kwargs={"k": 5}) # Retrieve top 5 results

    # Define the prompt template for the RAG chain
    # This template instructs the LLM on how to use the retrieved context
    template = """
    You are a helpful assistant who answers questions based on the provided context.
    Use the following pieces of context to answer the user's question.
    If you don't know the answer, just say that you don't know, don't try to make up an answer.
    Keep the answer concise and relevant to the user's question.

    Context:
    {context}

    Question:
    {question}

    Helpful Answer:
    """
    prompt = PromptTemplate(template=template, input_variables=["context", "question"])


    # --- 4. COMBINE INTO A RAG CHAIN ---
    # This chain orchestrates the retrieval and generation process
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    print("RAG chain created successfully.")


    # --- 5. WRAP IN A WHILE TRUE LOOP FOR A CLI CHAT ---
    print("\n--- Chat Interface Ready ---")
    print("Type 'exit' or 'quit' to end the chat.")

    while True:
        try:
            # Get user input from the command line
            query = input("\nYou: ")

            # Check for exit command
            if query.lower() in ["exit", "quit"]:
                print("Exiting chat. Goodbye!")
                break

            # Stream the response from the RAG chain
            print("Assistant: ", end="", flush=True)
            for chunk in rag_chain.stream(query):
                print(chunk, end="", flush=True)
            print() # Newline after the full response

        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            print("\nExiting chat. Goodbye!")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            break


if __name__ == '__main__':
    # To run this script, you need to install the required packages:
    # pip install langchain-openai langchain-community sentence-transformers chromadb
    main()