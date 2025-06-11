import discord
import os
import asyncio
from dotenv import load_dotenv

# Import the functions from your refactored agent script
from merged_agent import initialize_agent, invoke_agent

# --- DISCORD BOT SETUP ---

# Load environment variables from a .env file
# Create a file named .env and add the line: DISCORD_TOKEN=your_bot_token_here
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

@client.event
async def on_ready():
    """
    This function runs when the bot has successfully connected to Discord.
    """
    print(f'Bot logged in as {client.user}')
    print('Initializing the Crucible AI Agent for Discord...')
    # This calls the updated function, which sets the global agent
    # executor variable inside the merged_agent module.
    initialize_agent()
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
        
        # Let the user know the bot is working on the request
        async with message.channel.typing():
            print(f"Received query from {message.author}: {message.content}")

            # 3. Clean the message content to get the pure query.
            bot_display_name = f'@{client.user.name}'
            clean_query = message.clean_content.replace(bot_display_name, '').strip()

            if message.guild and message.guild.me.nick:
                 bot_nickname = f'@{message.guild.me.nick}'
                 clean_query = clean_query.replace(bot_nickname, '').strip()

            print(f"Cleaned query: '{clean_query}'")
            
            # 4. Invoke the agent in a separate thread to avoid blocking
            # This is the crucial fix for the "heartbeat blocked" error.
            # It runs the synchronous `invoke_agent` function in the background.
            try:
                agent_response = await asyncio.to_thread(invoke_agent, clean_query)
            except Exception as e:
                print(f"Error invoking agent via asyncio.to_thread: {e}")
                agent_response = "I'm sorry, a critical error occurred while I was thinking."

            # 5. Send the agent's response back to the Discord channel
            await message.channel.send(agent_response)
            print(f"Sent response to {message.author}")
            print("---")


def main():
    """
    Main function to start the bot.
    """
    print("Starting Discord bot...")
    client.run(TOKEN)

if __name__ == "__main__":
    main()
