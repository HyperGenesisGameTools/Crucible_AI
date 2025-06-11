import discord
import os
from dotenv import load_dotenv

# --- CONFIGURATION ---
# Load environment variables from a .env file
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# --- BOT SETUP ---
# discord.py requires specifying intents. 
# The default intents are sufficient for on_ready, but we need message_content for on_message.
intents = discord.Intents.default()
intents.message_content = True

# Create a client instance
client = discord.Client(intents=intents)

# --- EVENTS ---
@client.event
async def on_ready():
    """
    This event is triggered when the bot has successfully connected to Discord's servers.
    """
    print(f'Logged in as {client.user}')
    print('Bot is ready.')
    print('------')

@client.event
async def on_message(message):
    """
    This event is triggered for every message that the bot can see.
    """
    # Ignore messages sent by the bot itself to prevent infinite loops.
    if message.author == client.user:
        return

    # Check if the message content is exactly '!ping'
    if message.content == '!ping':
        # Reply to the user's message with 'pong'
        await message.reply('pong')

# --- RUN THE BOT ---
# Entry point for the script
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN not found. Please set it in your .env file.")
    else:
        # Run the client with the provided token
        client.run(DISCORD_TOKEN)
