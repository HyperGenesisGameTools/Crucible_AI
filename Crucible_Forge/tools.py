# tools.py
import os
import subprocess
from langchain.tools import tool
from github import Github, GithubException

@tool
def get_github_project_tasks() -> str:
    """
    Fetches and lists all tasks from a pre-configured GitHub Project board.
    This tool reads the repository and project number from environment variables.
    Use this to get an overview of current development tasks.
    """
    token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("GITHUB_REPO")
    project_number = os.getenv("GITHUB_PROJECT_NUMBER")

    if not all([token, repo_name, project_number]):
        return "Error: GITHUB_TOKEN, GITHUB_REPO, and GITHUB_PROJECT_NUMBER must be set as environment variables."

    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        project = repo.get_project(int(project_number))
    except GithubException as e:
        return f"Error accessing GitHub. Please check your token, repo, and project number. Details: {e}"
    except ValueError:
        return "Error: GITHUB_PROJECT_NUMBER is not a valid integer."
    except Exception as e:
        return f"An unexpected error occurred: {e}"

    output = f"Tasks for Project '{project.name}' in repository '{repo_name}':\n"
    output += "=" * 50 + "\n"

    try:
        columns = project.get_columns()
        if columns.totalCount == 0:
            return f"{output}\nNo columns found in this project."

        for column in columns:
            output += f"\n--- Column: {column.name} ---\n"
            cards = column.get_cards()
            if cards.totalCount == 0:
                output += "  (No tasks in this column)\n"
            for card in cards:
                # The note of a card is its main content for project automation
                if card.note:
                    task_title = card.note.strip().split('\n', 1)[0] # First line as title
                    output += f"  - [Task] {task_title}\n"
    except Exception as e:
        return f"Error fetching project columns or cards: {e}"
        
    return output


@tool
def read_file(file_path: str) -> str:
    """
    Reads the entire content of a specified file and returns it as a string.
    Use this tool to inspect the content of existing files.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return content
    except FileNotFoundError:
        return f"Error: The file '{file_path}' was not found."
    except Exception as e:
        return f"An unexpected error occurred while reading the file: {e}"

@tool
def write_file(file_path: str, content: str) -> str:
    """
    Writes the given content to a specified file. 
    This will create the file if it does not exist and overwrite it if it does.
    Use this tool to create new files or modify existing ones.
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to '{file_path}'."
    except Exception as e:
        return f"An unexpected error occurred while writing to the file: {e}"

@tool
def list_files_recursive(directory: str) -> str:
    """
    Walks a directory and returns a formatted string listing all files and subdirectories.
    Use this tool to understand the structure of the codebase.
    """
    if not os.path.isdir(directory):
        return f"Error: The directory '{directory}' does not exist."
    
    try:
        output = f"File structure for '{directory}':\n"
        for root, dirs, files in os.walk(directory):
            # Calculate the level of indentation
            level = root.replace(directory, '').count(os.sep)
            indent = ' ' * 4 * (level)
            
            # Add the current directory to the output
            output += f"{indent}{os.path.basename(root)}/\n"
            
            # Indent for files within this directory
            sub_indent = ' ' * 4 * (level + 1)
            
            # Add all files in the current directory
            for f in files:
                output += f"{sub_indent}{f}\n"
                
        return output
    except Exception as e:
        return f"An unexpected error occurred while listing the files: {e}"

@tool
def run_shell_command(command: str) -> str:
    """
    Executes a shell command after receiving user confirmation.
    Captures and returns the standard output and standard error.
    This tool has a 60-second timeout.
    Use this for executing system commands, like running tests or git operations.
    """
    print(f"\nPROPOSED COMMAND: {command}")
    confirmation = input("Do you want to execute this command? (y/n): ")
    
    if confirmation.lower() != 'y':
        return "Command execution cancelled by user."

    try:
        # Using shell=True can be a security risk if not used carefully.
        # The user confirmation step (Human-in-the-Loop) is a critical safeguard.
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60  # 60-second timeout
        )
        
        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        if not output:
            output = "Command executed successfully with no output."
            
        return output

    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 60 seconds."
    except Exception as e:
        return f"An unexpected error occurred while executing the command: {e}"