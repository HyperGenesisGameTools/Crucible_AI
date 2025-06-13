# embed_codebase.py
import os
import shutil
import fnmatch
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.text_splitter import Language
from langchain_core.documents import Document

# --- CONFIGURATION ---
# The root directory of the codebase to be embedded.
# We go up one level from `/Crucible_Forge` to the project root.
CODEBASE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# The directory where the new vector store will be saved.
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "codebase_chroma_db")

# The embedding model to use. Should be the same as the one used by the agent.
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# File extensions to include in the embedding process.
# We want Python source, Markdown docs, and text files.
FILE_EXTENSIONS = [".py", ".md", ".txt"]

# --- CHUNKING CONFIGURATION ---
# These settings are crucial for creating meaningful document chunks.
# A larger chunk size can keep more context (e.g., a whole function) together.
PYTHON_CHUNK_SIZE = 1000
PYTHON_CHUNK_OVERLAP = 200
MARKDOWN_CHUNK_SIZE = 800
MARKDOWN_CHUNK_OVERLAP = 150


def get_gitignore_patterns(root_path):
    """Reads .gitignore from the root and returns a list of patterns."""
    gitignore_path = os.path.join(root_path, '.gitignore')
    patterns = []
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Add patterns for both file and directory matching
                    patterns.append(line)
                    if not line.endswith('/'):
                        patterns.append(line + '/')
    # Also add default ignores that might not be in the file
    patterns.extend(['.git/', '.venv/', 'venv/', '__pycache__/'])
    return list(set(patterns)) # Return unique patterns

def is_ignored(path, root_path, ignore_patterns):
    """Checks if a file or directory path matches any of the .gitignore patterns."""
    # Ensure the path is relative and uses forward slashes for matching
    relative_path = os.path.relpath(path, root_path).replace('\\', '/')
    # For directories, ensure it ends with a slash
    if os.path.isdir(path):
        relative_path += '/'
        
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(relative_path, pattern):
            return True
    return False

def load_documents_manually():
    """
    Manually walks the filesystem, respects .gitignore, and reads files
    with robust encoding handling to prevent UnicodeDecodeError.
    """
    loaded_docs = []
    ignore_patterns = get_gitignore_patterns(CODEBASE_ROOT)
    print(f"Scanning codebase root: {CODEBASE_ROOT}")
    print(f"Ignoring patterns: {ignore_patterns}")

    for root, dirs, files in os.walk(CODEBASE_ROOT, topdown=True):
        # Filter out ignored directories in-place
        dirs[:] = [d for d in dirs if not is_ignored(os.path.join(root, d), CODEBASE_ROOT, ignore_patterns)]
        
        for file_name in files:
            file_path = os.path.join(root, file_name)
            
            if file_name.endswith(tuple(FILE_EXTENSIONS)) and not is_ignored(file_path, CODEBASE_ROOT, ignore_patterns):
                try:
                    # Use errors='ignore' to skip problematic characters instead of crashing
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        doc = Document(page_content=content, metadata={"source": file_path})
                        loaded_docs.append(doc)
                except Exception as e:
                    print(f"Could not read file {file_path}: {e}")
    
    return loaded_docs


def load_and_split_documents():
    """
    Loads all relevant files from the codebase, splits them into
    manageable chunks using language-aware splitters, and returns
    a list of LangChain Document objects.
    This version uses a manual loader to handle encoding errors.
    """
    # --- Document Loading (Replaced GenericLoader with manual function) ---
    loaded_docs = load_documents_manually()
    
    if not loaded_docs:
        print("No documents found to embed. Check file paths and extensions.")
        return []
    
    print(f"Loaded {len(loaded_docs)} documents from the codebase.")

    # --- Document Splitting (Unchanged logic) ---
    python_splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.PYTHON,
        chunk_size=PYTHON_CHUNK_SIZE,
        chunk_overlap=PYTHON_CHUNK_OVERLAP,
    )
    
    markdown_splitter = RecursiveCharacterTextSplitter(
        chunk_size=MARKDOWN_CHUNK_SIZE,
        chunk_overlap=MARKDOWN_CHUNK_OVERLAP,
    )

    split_docs = []
    for doc in loaded_docs:
        file_path = doc.metadata.get("source")
        if file_path.endswith(".py"):
            split_docs.extend(python_splitter.split_documents([doc]))
        elif file_path.endswith((".md", ".txt")):
            split_docs.extend(markdown_splitter.split_documents([doc]))
            
    print(f"Split {len(loaded_docs)} documents into {len(split_docs)} chunks.")
    return split_docs


def main():
    """
    Main function to orchestrate the codebase embedding pipeline:
    1. Clean up any existing vector store.
    2. Load and split all relevant codebase files.
    3. Initialize a local embedding model.
    4. Create and persist a ChromaDB vector store.
    """
    print("--- Starting Crucible Forge Codebase Embedding Pipeline ---")

    # 1. Clean up previous vector store if it exists
    if os.path.exists(CHROMA_PERSIST_DIR):
        print(f"Found existing vector store. Removing '{CHROMA_PERSIST_DIR}'...")
        shutil.rmtree(CHROMA_PERSIST_DIR)

    # 2. Load and split documents from the codebase
    documents = load_and_split_documents()
    if not documents:
        print("Halting pipeline due to no documents loaded.")
        return

    # 3. Initialize the local, open-source embedding model
    print(f"Initializing embedding model: '{EMBEDDING_MODEL}'...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    print("Embedding model loaded successfully.")

    # 4. Create the vector store and persist it to disk
    print(f"Generating embeddings and creating Chroma vector store...")
    print(f"Persistence directory: '{CHROMA_PERSIST_DIR}'")
    
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=CHROMA_PERSIST_DIR
    )

    print("\n--- Codebase Embedding Pipeline Complete ---")
    print(f"Successfully embedded {len(documents)} chunks.")
    print(f"Vector store has been saved to '{vector_store._persist_directory}'")


if __name__ == '__main__':
    main()
