# hypergenesisgametools/crucible_ai/Crucible_AI-CmdToolUpgrade/Crucible_Forge/tools.py
import os
import subprocess
import json
from langchain.tools import tool
from github import Github, GithubException

@tool
def get_github_project_tasks() -> str:
    """
    Fetches and lists all tasks from a pre-configured classic GitHub Project board.
    This tool reads the repository and project number from environment variables.
    It returns a JSON string representing the project's columns and their tasks (cards).
    Use this to get an overview of current development tasks.
    """
    token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("GITHUB_REPO")
    project_number_str = os.getenv("GITHUB_PROJECT_NUMBER")

    if not all([token, repo_name, project_number_str]):
        return json.dumps({
            "error": "Configuration missing",
            "message": "GITHUB_TOKEN, GITHUB_REPO, and GITHUB_PROJECT_NUMBER must be set as environment variables."
        })
    try:
        project_number = int(project_number_str)
    except (ValueError, TypeError):
        return json.dumps({
            "error": "Invalid Configuration",
            "message": f"GITHUB_PROJECT_NUMBER must be an integer, but got '{project_number_str}'."
        })
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        project = repo.get_project(project_number)
        print(f"Successfully connected to GitHub and found project '{project.name}'.")
    except GithubException as e:
        return json.dumps({
            "error": "GitHub API Error",
            "message": f"Error accessing GitHub. Details: {e.status} {e.data}"
        })
    except Exception as e:
        return json.dumps({"error": "Unexpected Error", "message": str(e)})

    project_data = {"projectName": project.name, "repositoryName": repo_name, "columns": []}
    try:
        columns = project.get_columns()
        for column in columns:
            column_data = {"columnName": column.name, "tasks": []}
            for card in column.get_cards():
                if card.note:
                    task_title = card.note.strip().split('\n', 1)[0]
                    column_data["tasks"].append({"cardId": card.id, "taskTitle": task_title, "fullNote": card.note.strip()})
            project_data["columns"].append(column_data)
        return json.dumps(project_data, indent=2)
    except Exception as e:
        return json.dumps({"error": "Error Processing Project Data", "message": str(e)})

@tool
def read_file(file_path: str) -> str:
    """
    Reads the entire content of a specified file and returns it as a string.
    Use this tool to inspect the content of existing files.
    The input must be a dictionary: {"file_path": "path/to/your/file.py"}
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: The file '{file_path}' was not found."
    except Exception as e:
        return f"An unexpected error occurred while reading the file: {e}"

@tool
def write_file(file_path: str, content: str) -> str:
    """
    Writes content to a specified file, creating directories if they don't exist.
    This overwrites the file if it already exists.
    The input must be a dictionary: {"file_path": "path/to/file.txt", "content": "hello world"}
    """
    try:
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to '{file_path}'."
    except Exception as e:
        return f"An unexpected error occurred while writing to the file: {e}"

@tool
def list_files_recursive(directory: str) -> str:
    """
    Lists all files and subdirectories within a given directory, returning a formatted string.
    Use this to understand the structure of the codebase.
    The input must be a dictionary: {"directory": "./some_folder"}
    """
    if not os.path.isdir(directory):
        return f"Error: The directory '{directory}' does not exist."
    try:
        output = f"File structure for '{directory}':\n"
        for root, dirs, files in os.walk(directory):
            # Exclude common virtual environment and cache folders
            dirs[:] = [d for d in dirs if d not in ['.git', '.venv', '__pycache__', 'node_modules']]
            level = root.replace(directory, '').count(os.sep)
            indent = ' ' * 4 * level
            output += f"{indent}{os.path.basename(root) or '.'}/\n"
            sub_indent = ' ' * 4 * (level + 1)
            for f in files:
                output += f"{sub_indent}{f}\n"
        return output
    except Exception as e:
        return f"An unexpected error occurred while listing the files: {e}"

@tool
def run_shell_command(command: str) -> str:
    """
    Executes a shell command. Captures and returns stdout and stderr.
    This tool has a 60-second timeout.
    Use this for non-interactive system commands like running tests ('pytest') or git operations.
    THE HUMAN OPERATOR APPROVES COMMANDS VIA THE GUI; DO NOT ASK FOR CONFIRMATION.
    The input must be a dictionary: {"command": "pytest -v"}
    """
    print(f"Executing command: '{command}'")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            check=False  # Do not raise exception on non-zero exit codes
        )
        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        if not output:
            output = "Command executed successfully with no output."
        # Add exit code for better context
        output += f"\nExit Code: {result.returncode}"
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 60 seconds."
    except Exception as e:
        return f"An unexpected error occurred while executing the command: {e}"
