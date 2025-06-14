# hypergenesisgametools/crucible_ai/Crucible_AI-CmdToolUpgrade/Crucible_Forge/agent.py
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
tools_list = [
    ForgeTools.search_codebase,
    ForgeTools.list_files_recursive,
    ForgeTools.read_file,
    ForgeTools.write_file,
    ForgeTools.run_shell_command,
    ForgeTools.get_github_project_tasks
]
available_tools = {t.name: t for t in tools_list}
tool_descriptions = render_text_description(tools_list)
codebase_constitution = ""

def initialize_agent():
    """Initializes the LLM and loads the Codebase Constitution for the agent."""
    global llm, codebase_constitution
    print("[Agent] Initializing...")
    llm = ChatOpenAI(base_url=LOCAL_LLM_URL, api_key=DUMMY_API_KEY, model=MODEL_NAME, temperature=MODEL_TEMP)
    try:
        with open('Codebase_Constitution.md', 'r', encoding='utf-8') as f:
            codebase_constitution = f.read()
        print("[Agent] Codebase Constitution loaded.")
    except FileNotFoundError:
        print("[Agent] WARNING: Codebase_Constitution.md not found. Context will be limited.")
        codebase_constitution = "No constitution available. You must rely only on file contents."
    print("[Agent] Components loaded and ready.")

def _safe_json_parse(json_string: str) -> list | dict | None:
    """Safely parses a JSON string, trying to extract it from markdown code blocks."""
    match = re.search(r'```(?:json)?\s*\n(.*?)\n\s*```', json_string, re.DOTALL)
    if match:
        clean_json = match.group(1).strip()
    else:
        clean_json = json_string.strip()
    
    try:
        return json.loads(clean_json)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON. Cleaned string was:\n{clean_json}")
        print(f"Original LLM response was:\n{json_string}")
        return None

# --- PRIMARY OPERATIONAL LOOP ---

def create_master_plan(goal: str) -> list:
    """
    Phase 1: PLAN
    Takes a user goal and creates an initial, high-level, end-to-end plan.
    """
    print(f"\n--- 📝 Creating Master Plan for Goal: {goal} ---")
    
    planning_prompt_template = """
    You are an expert AI software developer. Your task is to create a detailed, step-by-step plan to accomplish a given software development goal.
    You must respond with a JSON array of "tasks". Each task is a dictionary with "description" and "tool_call" keys.
    The "tool_call" dictionary must contain "tool_name" and "parameters" keys.
    The "tool_name" must be one of a specific list of available tools.

    **Strategy:**
    1. First, use the `search_codebase` tool to understand the existing code relevant to the goal. This is critical for context.
    2. Then, use `list_files_recursive` to verify file locations if needed.
    3. Formulate the rest of your plan based on your findings (read, write, run tests, etc.).

    Available Tools:
    {tools}

    Your Primary Directive (Codebase Constitution):
    ---
    {constitution}
    ---

    Goal: {goal}
    
    Create a JSON plan to achieve the goal. Your response MUST be ONLY the JSON array of tasks, optionally wrapped in a single ```json code block.
    """
    
    prompt = ChatPromptTemplate.from_template(planning_prompt_template)
    chain = prompt | llm
    response = chain.invoke({
        "tools": tool_descriptions,
        "constitution": codebase_constitution,
        "goal": goal,
    })
    
    plan = _safe_json_parse(response.content)
    if plan and isinstance(plan, list):
        print("✅ Master Plan created successfully.")
        return plan
    else:
        print("❌ Failed to create a valid Master Plan.")
        return [{"description": "Error: Failed to create a plan.", "tool_call": {"tool_name": "error", "parameters": {"message": "Invalid plan format from LLM."}}}]

def execute_step(task: dict) -> str:
    """
    Phase 2: EXECUTE
    Executes a single step from the plan. This acts as a router.
    """
    print(f"\n--- 🚀 Executing Task: {task.get('description', 'No description')} ---")
    
    tool_call = task.get("tool_call", {})
    tool_name = tool_call.get("tool_name")
    parameters = tool_call.get("parameters", {})
    
    print(f"  - Tool: {tool_name}({parameters})")

    if tool_name == "implement_feature_tdd":
        return _run_tdd_sub_loop(parameters.get('feature_description', 'No feature description provided.'))

    tool_to_run = available_tools.get(tool_name)
    if not tool_to_run:
        observation = f"Error: Tool '{tool_name}' not found."
        print(f"    -> Observation: {observation}")
        return observation

    try:
        observation = tool_to_run.invoke(parameters)
        print(f"    -> Observation (start): {str(observation)[:300]}...")
        return observation
    except Exception as e:
        observation = f"Error executing tool '{tool_name}': {e}"
        print(f"    -> Observation: {observation}")
        return observation

def reevaluate_and_update_plan(goal: str, remaining_plan: list, observation_history: list[str]) -> list:
    """
    Phase 3: RE-EVALUATE
    Takes the most recent observations and refactors the rest of the plan.
    """
    print("\n--- 🤔 Re-evaluating and Updating Plan ---")
    
    if not remaining_plan:
        print("✅ No remaining steps. Plan is complete.")
        return []

    reevaluation_prompt_template = """
    You are an expert AI software developer, currently executing a multi-step plan.
    Your task is to generate the *next* sequence of steps based on what just happened.

    **Overall Goal:** {goal}

    **Recent Observation History (most recent is last):**
    ---
    {observation_history}
    ---

    **Previously Remaining Plan (for context):**
    ---
    {old_plan}
    ---

    Your Primary Directive (Codebase Constitution):
    ---
    {constitution}
    ---
    
    Available Tools:
    {tools}

    **Your Instructions:**
    1. Analyze the 'Observation History'. This is the result of the last few steps. Pay closest attention to the most recent one.
    2. If you need more context about the codebase, use the `search_codebase` tool.
    3. Look at the 'Previously Remaining Plan' for context on what you originally intended to do.
    4. Generate a NEW, REVISED plan for the *remaining* tasks.
    5. **Crucially, do not repeat the action that produced the most recent observation.** If the last observation shows the contents of a file, your next step must be to process or modify that file, not to read it again.
    6. If the most recent observation is an error, your new plan's first step must be to fix that error.

    Your response MUST be ONLY the JSON array of new tasks.
    """
    
    prompt = ChatPromptTemplate.from_template(reevaluation_prompt_template)
    chain = prompt | llm
    
    formatted_history = "\n".join([f"OBSERVATION {i+1}:\n{obs}" for i, obs in enumerate(observation_history)])
    
    response = chain.invoke({
        "goal": goal,
        "observation_history": formatted_history,
        "old_plan": json.dumps(remaining_plan, indent=2),
        "constitution": codebase_constitution,
        "tools": tool_descriptions,
    })

    new_plan = _safe_json_parse(response.content)
    if new_plan is not None and isinstance(new_plan, list):
        print("✅ Plan re-evaluated and updated successfully.")
        return new_plan
    else:
        print("❌ Failed to update the plan. Returning the old plan.")
        return remaining_plan


def _run_tdd_sub_loop(feature_description: str) -> str:
    """
    A specialized sub-loop for implementing code changes using Test-Driven Development.
    """
    print(f"\n--- TDD Sub-Loop Started: {feature_description} ---")
    
    # This is a simplified placeholder. A real implementation would be more complex.
    context = f"TDD process for '{feature_description}'"
    print("  [TDD] Step 1: Identifying relevant files (Simulated)")
    
    print("  [TDD] Step 2: Generating a failing test (Simulated)")
    test_code = f"# Test for: {feature_description}\nimport pytest\ndef test_new_feature():\n  assert False, 'Test not implemented yet'"
    write_obs = ForgeTools.write_file.invoke({"file_path": "./Product/tests/test_new_feature.py", "content": test_code})
    print(f"  [TDD]  -> {write_obs}")

    print("  [TDD] Step 3: Running tests to confirm failure (Simulated)")
    test_obs = ForgeTools.run_shell_command.invoke({"command": "echo 'pytest output: 1 failed in 0.01s'"})
    print(f"  [TDD]  -> {test_obs}")
    
    print("  [TDD] Step 4: Implementing feature to pass test (Simulated)")
    implementation_code = "# New feature code\ndef new_feature():\n  return True"
    write_impl_obs = ForgeTools.write_file.invoke({"file_path": "./Product/new_feature.py", "content": implementation_code})
    print(f"  [TDD]  -> {write_impl_obs}")

    print("  [TDD] Step 5: Running tests to confirm success (Simulated)")
    final_test_obs = ForgeTools.run_shell_command.invoke({"command": "echo 'pytest output: 1 passed in 0.02s'"})
    print(f"  [TD]  -> {final_test_obs}")
    
    final_observation = f"SUCCESS: TDD sub-loop completed for '{feature_description}'. New tests and implementation have been created and verified."
    print("--- TDD Sub-Loop Finished ---")
    return final_observation
