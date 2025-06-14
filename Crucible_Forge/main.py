# hypergenesisgametools/crucible_ai/Crucible_AI-dev/Crucible_Forge/main.py

import agent
import json

def main():
    """
    Main execution function for the Crucible Forge agent.
    Initializes the agent and starts the Plan-Execute-Evaluate loop.
    """
    print("--- Starting Crucible Forge ---")
    
    try:
        agent.initialize_agent()
    except Exception as e:
        print(f"[Main] FATAL ERROR: Could not initialize agent. Reason: {e}")
        return

    print("\n--- Crucible Forge is Ready ---")
    
    # Get the high-level goal from the user.
    goal = input("Enter your high-level development goal: ")
    
    max_cycles = 5 # Safety break to prevent infinite loops
    cycle_count = 0
    observations = None # No observations on the first cycle
    
    while cycle_count < max_cycles:
        cycle_count += 1
        print(f"\n====================== CYCLE {cycle_count}/{max_cycles} ======================")
        
        # 1. PLAN
        plan = agent.create_plan(goal, observations)
        
        # Let the user review and approve the plan before execution
        print("\nGenerated Plan:")
        print(json.dumps(plan, indent=2))
        confirmation = input("Do you want to execute this plan? (y/n): ")
        if confirmation.lower() != 'y':
            print("Plan rejected by user. Shutting down.")
            break
            
        # 2. EXECUTE
        plan_succeeded, observations = agent.execute_plan(plan)
        
        if not plan_succeeded:
            print("\nPlan execution failed. The observations from the failed step will be used to create a new plan.")
            continue # Skip evaluation and go to the next planning cycle
            
        # 3. EVALUATE
        is_goal_achieved = agent.evaluate_results(goal, observations)
        
        if is_goal_achieved:
            print("\n🎉 Goal achieved successfully! Shutting down.")
            break
        else:
            print("\nGoal not yet achieved. The observations will be used to create a new plan.")
            if cycle_count == max_cycles:
                print("\nMaximum cycle limit reached. Shutting down.")

    print("\n--- Crucible Forge Shutdown Complete ---")


if __name__ == "__main__":
    main()