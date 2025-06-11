import discord
import os
import asyncio
import multiprocessing
from dotenv import load_dotenv

# Import the functions and classes from your agent and memory scripts
from merged_agent import initialize_agent, invoke_agent, set_memory_queue
from prompt_context import PromptContext
from memory_manager import memory_worker

# --- DISCORD BOT SETUP ---

# Load environment variables from a .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    print("FATAL ERROR: DISCORD_TOKEN not found in .env file.")
    exit()

# Define the intents your bot needs. The 'message_content' intent is crucial.
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

# This dictionary will store a separate PromptContext object for each user.
prompt_context_per_user = {}


@client.event
async def on_ready():
    """
    This function runs when the bot has successfully connected to Discord.
    """
    print(f'Bot logged in as {client.user}')
    # The agent is now initialized in the main execution block
    # to ensure it happens after the memory manager process is started.
    print('Crucible AI Agent is ready and listening.')
    print('---')


@client.event
async def on_message(message):
    """
    This function runs for every new message received in any channel the bot can see.
    """
    # 1. Ignore messages from the bot itself to prevent loops
    if message.author == client.user:
        return

    # 2. Check if the bot was mentioned in the message
    if client.user.mentioned_in(message):
        
        user_id = message.author.id
        
        # 3. Get or create a PromptContext object for the user who sent the message.
        if user_id not in prompt_context_per_user:
            print(f"Creating new conversation context for user: {message.author.name} ({user_id})")
            prompt_context_per_user[user_id] = PromptContext()
            prompt_context_per_user[user_id].background_briefing = (
                f"This is a conversation with the user named {message.author.name}. "
                "The AI is a project management assistant named Crucible. "
                "The user is likely a project manager."
            )
        
        user_context = prompt_context_per_user[user_id]
        
        async with message.channel.typing():
            print(f"Received query from {message.author}: {message.content}")

            # 4. Clean the message content to get the pure query.
            bot_display_name = f'@{client.user.name}'
            clean_query = message.clean_content.replace(bot_display_name, '').strip()

            if message.guild and message.guild.me.nick:
                 bot_nickname = f'@{message.guild.me.nick}'
                 clean_query = clean_query.replace(bot_nickname, '').strip()

            print(f"Cleaned query: '{clean_query}'")
            
            # 5. Invoke the agent, passing the user's query and their unique context object.
            try:
                # Run the synchronous agent invocation in a separate thread.
                agent_response = await asyncio.to_thread(invoke_agent, clean_query, user_context)

                # 6. Update the user's current context with the latest exchange.
                user_context.current_context += f"\nUser: {clean_query}\nAI: {agent_response}"

            except Exception as e:
                print(f"Error invoking agent via asyncio.to_thread: {e}")
                agent_response = "I'm sorry, a critical error occurred while I was thinking."

            # 7. Send the agent's response back to the Discord channel
            await message.channel.send(agent_response)
            print(f"Sent response to {message.author}")
            print("---")


def main():
    """
    Main function to set up the multiprocessing environment and start the bot.
    """
    print("--- Starting Crucible AI System ---")

    # Use 'spawn' start method for compatibility across platforms (macOS, Windows)
    try:
        multiprocessing.set_start_method('spawn', force=True)
        print("[Main] Set multiprocessing start method to 'spawn'.")
    except RuntimeError:
        print("[Main] Multiprocessing context already set.")


    # 1. Create the communication queue for the memory manager
    memory_update_queue = multiprocessing.Queue()

    # 2. Start the memory manager as a separate, long-running process
    # The 'daemon=True' flag ensures it shuts down when the main script exits.
    manager_process = multiprocessing.Process(
        target=memory_worker,
        args=(memory_update_queue,),
        daemon=True
    )
    manager_process.start()
    print("[Main] Memory Manager process started.")

    # 3. Provide the agent module with the queue for its tools to use
    set_memory_queue(memory_update_queue)
    print("[Main] Memory update queue has been passed to the agent.")

    # 4. Initialize the agent's components (LLM, tools, etc.)
    # This must happen in the main process after the queue is set.
    print("[Main] Initializing the Crucible AI Agent for Discord...")
    initialize_agent()

    # 5. Start the Discord bot
    print("[Main] Starting Discord bot...")
    client.run(TOKEN)

if __name__ == "__main__":
    main()
