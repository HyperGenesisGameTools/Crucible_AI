# hypergenesisgametools/crucible_ai/Crucible_AI-dev/Crucible_Forge/agent.py

import json
import re  # Import the regular expression module
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools.render import render_text_description
import tools as ForgeTools

# --- CONFIGURATION ---
LOCAL_LLM_URL = "http://localhost:1234/v1"
DUMMY_API_KEY = "lm-studio"
MODEL_NAME = "local-model" # Or your deepseek-coder model
MODEL_TEMP = 0.2

# --- GLOBAL AGENT COMPONENTS ---
llm = None
available_tools = {
    "list_files": ForgeTools.list_files_recursive,
    "read_file": ForgeTools.read_file,
    "write_file": ForgeTools.write_file,
    "run_shell": ForgeTools.run_shell_command,
    "get_tasks": ForgeTools.get_github_project_tasks
}
tool_descriptions = render_text_description(list(available_tools.values()))

def initialize_agent():
    """Initializes the LLM for the agent."""
    global llm
    print("[Agent] Initializing...")
    llm = ChatOpenAI(base_url=LOCAL_LLM_URL, api_key=DUMMY_API_KEY, model=MODEL_NAME, temperature=MODEL_TEMP)
    print("[Agent] Components loaded and ready.")

def create_plan(goal: str, previous_observations: str = None) -> list:
    """
    First 'turn': Takes a user goal and creates a structured plan.
    If a previous plan failed, it takes the observations to create a new, revised plan.
    """
    print(f"\n--- 📝 Creating Plan for Goal: {goal} ---")
    
    planning_prompt_template = """
    You are an expert AI software developer agent. Your task is to create a detailed, step-by-step plan to accomplish a given software development goal.

    You must respond with a JSON array of "tasks". Each task is a dictionary with two keys: "tool_name" and "parameters".
    The "tool_name" must be one of the available tools. The "parameters" is a dictionary of arguments for that tool.

    Available Tools:
    {tools}

    Goal: {goal}
    {observation_context}
    
    Based on the goal and any provided context from previous attempts, create a JSON plan to achieve the goal.
    Ensure your plan follows a logical sequence. For new features, this means writing a failing test first, then writing the code to make it pass.
    
    Your response MUST be ONLY the JSON array of tasks, optionally wrapped in a single ```json code block. Do not include any other text.
    """
    
    observation_context = ""
    if previous_observations:
        observation_context = f"A previous attempt failed. Use the following observations to create a new, corrected plan:\n{previous_observations}"

    prompt = ChatPromptTemplate.from_template(planning_prompt_template)
    
    chain = prompt | llm
    
    response = chain.invoke({
        "tools": tool_descriptions,
        "goal": goal,
        "observation_context": observation_context
    })
    
    # --- FIX STARTS HERE ---
    # The LLM often wraps its response in ```json ... ```. We need to extract the raw JSON.
    response_content = response.content
    print(f"Raw LLM response:\n{response_content}") # For debugging

    # Use regex to find the content inside ```json ... ``` or just ``` ... ```
    match = re.search(r'```(?:json)?\s*\n(.*?)\n\s*```', response_content, re.DOTALL)
    if match:
        # If we found a match, use the captured group
        json_string = match.group(1).strip()
    else:
        # If no markdown block is found, assume the whole response is the JSON
        json_string = response_content.strip()

    try:
        plan = json.loads(json_string)
        print("✅ Plan parsed successfully.")
        return plan
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode the plan from the LLM. Cleaned string was:\n{json_string}")
        return [{"tool_name": "error", "parameters": {"message": f"Invalid plan format: {e}"}}]
    # --- FIX ENDS HERE ---


def execute_plan(plan: list) -> (bool, str):
    """
    Second 'turn': Executes the plan sequentially and gathers observations.
    Returns a tuple of (plan_succeeded, all_observations_string).
    """
    print("\n--- 🚀 Executing Plan ---")
    all_observations = []
    
    if not plan or not isinstance(plan, list):
        return False, "Execution failed: The plan was empty or invalid."

    for i, task in enumerate(plan):
        print(f"  - Task {i+1}/{len(plan)}: {task['tool_name']}({task.get('parameters', {})})")
        
        tool_to_run = available_tools.get(task["tool_name"])
        if not tool_to_run:
            observation = f"Error: Tool '{task['tool_name']}' not found."
            all_observations.append(observation)
            print(f"    -> Observation: {observation}")
            return False, "\n".join(all_observations) # Halt on critical error

        try:
            # Use .get('parameters', {}) to avoid errors if parameters are missing
            observation = tool_to_run.invoke(task.get('parameters', {}))
            all_observations.append(observation)
            # Print a snippet of the observation for brevity
            print(f"    -> Observation (start): {str(observation)[:200]}...")
        except Exception as e:
            observation = f"Error executing tool '{task['tool_name']}': {e}"
            all_observations.append(observation)
            print(f"    -> Observation: {observation}")
            return False, "\n".join(all_observations) # Halt on execution error
            
    print("✅ Plan execution complete.")
    return True, "\n".join(all_observations)

def evaluate_results(goal: str, observations: str) -> bool:
    """
    Final 'turn': Evaluates if the goal was met based on the observations.
    """
    print("\n--- 🤔 Evaluating Results ---")
    
    evaluation_prompt_template = """
    You are an expert AI software developer agent. You have just executed a plan to achieve a goal.
    Your task is to analyze the observations from the execution and determine if the goal was successfully met.
    The most important observation is usually the output of the final test run. If all tests pass, the goal is likely met.

    Goal: {goal}
    
    Observations from executed plan:
    ---
    {observations}
    ---

    Based on the observations, did the plan successfully achieve the goal?
    Respond with only the word "SUCCESS" or "FAILURE".
    """
    prompt = ChatPromptTemplate.from_template(evaluation_prompt_template)
    chain = prompt | llm
    response = chain.invoke({"goal": goal, "observations": observations})
    
    result = response.content.strip().upper()
    print(f"✅ Evaluation complete. Result: {result}")
    return result == "SUCCESS"
