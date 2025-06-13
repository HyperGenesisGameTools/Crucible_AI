# main.py

from agent import initialize_agent, invoke_agent

def main():
    """
    Main execution function for the Crucible Forge agent.
    Initializes the agent and starts the interaction loop.
    """
    print("--- Starting Crucible Forge ---")
    
    # 1. Initialize the agent's components (LLM, tools, prompt, etc.)
    print("[Main] Initializing the Crucible Forge Agent...")
    try:
        initialize_agent()
        print("[Main] Agent initialized successfully.")
    except Exception as e:
        print(f"[Main] FATAL ERROR: Could not initialize agent. Reason: {e}")
        return

    # 2. Start the main application loop
    print("\n--- Crucible Forge is Ready ---")
    print("You can now interact with the agent.")
    
    try:
        while True:
            query = input("\nEnter your command: ")
            if query.lower() in ["exit", "quit"]:
                break
            
            # 3. Invoke the agent with the user's query
            response = invoke_agent(query)
            print(f"\n[Agent Response]: {response}")

    except KeyboardInterrupt:
        print("\n[Main] User interrupted the session. Shutting down.")
    except Exception as e:
        print(f"\n[Main] An unexpected error occurred: {e}")
    finally:
        print("--- Crucible Forge Shutdown Complete ---")


if __name__ == "__main__":
    main()
