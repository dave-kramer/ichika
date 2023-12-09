import os
import discord
from discord.ext import commands, tasks
import requests
import sqlite3
import asyncio
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)


def initialize_database():
    db_path = "db/mal_users.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS mal_users (mal_username TEXT PRIMARY KEY, last_check REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS bot_settings (setting_key TEXT PRIMARY KEY, setting_value TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS subreddits (subreddit_name TEXT PRIMARY KEY, last_check REAL)')
    
    conn.commit()
    conn.close()

async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            # cut off the .py from the file name
            await client.load_extension(f"cogs.{filename[:-3]}")

async def main():
    initialize_database()
    await load_extensions()
    await client.start(os.getenv("TOKEN"))

asyncio.run(main())