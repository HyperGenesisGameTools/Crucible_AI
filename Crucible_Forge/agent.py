# hypergenesisgametools/crucible_ai/Crucible_AI-dev/Crucible_Forge/agent.py

import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools.render import render_text_description
import tools as ForgeTools

# --- CONFIGURATION ---
LOCAL_LLM_URL = "http://localhost:1234/v1"
DUMMY_API_KEY = "lm-studio"
MODEL_NAME = "local-model"
MODEL_TEMP = 0.2

# --- GLOBAL AGENT COMPONENTS ---
llm = None

# --- FIX: Define tools in a list for robust registration ---
tools_list = [
    ForgeTools.list_files_recursive,
    ForgeTools.read_file,
    ForgeTools.write_file,
    ForgeTools.run_shell_command,
    ForgeTools.get_github_project_tasks
]

# --- FIX: Build the lookup dictionary and descriptions programmatically ---
# This guarantees the keys match the actual tool names.
available_tools = {t.name: t for t in tools_list}
tool_descriptions = render_text_description(tools_list)

def initialize_agent():
    """Initializes the LLM for the agent."""
    global llm
    print("[Agent] Initializing...")
    llm = ChatOpenAI(base_url=LOCAL_LLM_URL, api_key=DUMMY_API_KEY, model=MODEL_NAME, temperature=MODEL_TEMP)
    print("[Agent] Components loaded and ready.")

def create_plan(goal: str, previous_observations: str = None) -> list:
    """
    First 'turn': Takes a user goal and creates a structured plan.
    """
    print(f"\n--- 📝 Creating Plan for Goal: {goal} ---")
    
    planning_prompt_template = """
    You are an expert AI software developer agent. Your task is to create a detailed, step-by-step plan to accomplish a given software development goal.
    You must respond with a JSON array of "tasks". Each task is a dictionary with "tool_name" and "parameters" keys.
    The "tool_name" must be one of the available tools.

    Available Tools:
    {tools}

    Goal: {goal}
    {observation_context}
    
    Create a JSON plan to achieve the goal. Your response MUST be ONLY the JSON array of tasks, optionally wrapped in a single ```json code block.
    """
    
    observation_context = ""
    if previous_observations:
        observation_context = f"A previous attempt failed. Use these observations to create a new plan:\n{previous_observations}"

    prompt = ChatPromptTemplate.from_template(planning_prompt_template)
    chain = prompt | llm
    response = chain.invoke({
        "tools": tool_descriptions,
        "goal": goal,
        "observation_context": observation_context
    })
    
    response_content = response.content
    print(f"Raw LLM response:\n{response_content}")

    match = re.search(r'```(?:json)?\s*\n(.*?)\n\s*```', response_content, re.DOTALL)
    if match:
        json_string = match.group(1).strip()
    else:
        json_string = response_content.strip()

    try:
        plan = json.loads(json_string)
        print("✅ Plan parsed successfully.")
        return plan
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode the plan. Cleaned string was:\n{json_string}")
        return [{"tool_name": "error", "parameters": {"message": f"Invalid plan format: {e}"}}]

def execute_plan(plan: list) -> (bool, str):
    """
    Second 'turn': Executes the plan sequentially and gathers observations.
    """
    print("\n--- 🚀 Executing Plan ---")
    all_observations = []
    
    if not plan or not isinstance(plan, list):
        return False, "Execution failed: The plan was empty or invalid."

    for i, task in enumerate(plan):
        # --- FIX: More robust task dictionary access ---
        tool_name = task.get("tool_name")
        parameters = task.get("parameters", {})
        
        print(f"  - Task {i+1}/{len(plan)}: {tool_name}({parameters})")
        
        tool_to_run = available_tools.get(tool_name)
        if not tool_to_run:
            observation = f"Error: Tool '{tool_name}' not found."
            all_observations.append(observation)
            print(f"    -> Observation: {observation}")
            return False, "\n".join(all_observations)

        try:
            observation = tool_to_run.invoke(parameters)
            all_observations.append(observation)
            print(f"    -> Observation (start): {str(observation)[:200]}...")
        except Exception as e:
            observation = f"Error executing tool '{tool_name}': {e}"
            all_observations.append(observation)
            print(f"    -> Observation: {observation}")
            return False, "\n".join(all_observations)
            
    print("✅ Plan execution complete.")
    return True, "\n".join(all_observations)

def evaluate_results(goal: str, observations: str) -> bool:
    """
    Final 'turn': Evaluates if the goal was met based on the observations.
    """
    print("\n--- 🤔 Evaluating Results ---")
    
    evaluation_prompt_template = """
    You are an expert AI software developer agent. Analyze if the goal was met based on the observations.
    If test outputs show success, the goal is likely met.

    Goal: {goal}
    
    Observations:
    ---
    {observations}
    ---

    Did the plan successfully achieve the goal? Respond with only "SUCCESS" or "FAILURE".
    """
    prompt = ChatPromptTemplate.from_template(evaluation_prompt_template)
    chain = prompt | llm
    response = chain.invoke({"goal": goal, "observations": observations})
    
    result = response.content.strip().upper()
    print(f"✅ Evaluation complete. Result: {result}")
    return result == "SUCCESS"
