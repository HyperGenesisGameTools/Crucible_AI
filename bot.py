import discord
import os
import asyncio
import multiprocessing
from dotenv import load_dotenv

# Import the functions and classes from your agent and memory scripts
from merged_agent import initialize_agent, invoke_agent, set_memory_queue
from memory_manager import memory_worker

# --- NEW IMPORTS for Conversational Memory ---
from langchain.memory import ConversationBufferWindowMemory

# --- REMOVED ---
# from prompt_context import PromptContext

# --- DISCORD BOT SETUP ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    print("FATAL ERROR: DISCORD_TOKEN not found in .env file.")
    exit()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

# This dictionary will store a separate memory object for each user.
memory_per_user = {}


@client.event
async def on_ready():
    """
    This function runs when the bot has successfully connected to Discord.
    """
    print(f'Bot logged in as {client.user}')
    print('Crucible AI Agent is ready and listening.')
    print('---')


@client.event
async def on_message(message):
    """
    This function runs for every new message received in any channel the bot can see.
    """
    # 1. Ignore messages from the bot itself
    if message.author == client.user:
        return

    # 2. Check if the bot was mentioned in the message
    if client.user.mentioned_in(message):
        
        user_id = message.author.id
        
        # 3. Get or create a ConversationBufferWindowMemory object for the user.
        if user_id not in memory_per_user:
            print(f"Creating new conversation memory for user: {message.author.name} ({user_id})")
            memory_per_user[user_id] = ConversationBufferWindowMemory(
                k=5, # Keep the last 5 exchanges
                memory_key="chat_history", # This must match the key in the prompt
                return_messages=True # Ensure it returns message objects
            )

        user_memory = memory_per_user[user_id]
        
        async with message.channel.typing():
            print(f"Received query from {message.author}: {message.content}")

            # 4. Clean the message content to get the pure query.
            bot_display_name = f'@{client.user.name}'
            clean_query = message.clean_content.replace(bot_display_name, '').strip()

            if message.guild and message.guild.me.nick:
                 bot_nickname = f'@{message.guild.me.nick}'
                 clean_query = clean_query.replace(bot_nickname, '').strip()

            print(f"Cleaned query: '{clean_query}'")
            
            # 5. Invoke the agent, passing the user's query and their unique memory object.
            try:
                # Run the synchronous agent invocation in a separate thread.
                agent_response = await asyncio.to_thread(invoke_agent, clean_query, user_memory)

                # 6. Manually save the context to the memory object for the next turn
                user_memory.save_context(
                    {"input": clean_query},
                    {"output": agent_response}
                )

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

    try:
        multiprocessing.set_start_method('spawn', force=True)
        print("[Main] Set multiprocessing start method to 'spawn'.")
    except RuntimeError:
        print("[Main] Multiprocessing context already set.")

    # 1. Create the communication queue for the memory manager
    memory_update_queue = multiprocessing.Queue()

    # 2. Start the memory manager as a separate, long-running process
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
    print("[Main] Initializing the Crucible AI Agent for Discord...")
    initialize_agent()

    # 5. Start the Discord bot
    print("[Main] Starting Discord bot...")
    client.run(TOKEN)

if __name__ == "__main__":
    main()
