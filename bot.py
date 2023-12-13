import os
import discord
from discord.ext import commands, tasks
from discord import Game, ActivityType
import requests
import sqlite3
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import random

load_dotenv()

intents = discord.Intents().all()
client = commands.Bot(command_prefix='!', intents=intents)


def initialize_database():
    db_path = "db/mal_users.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS mal_users (mal_username TEXT PRIMARY KEY, last_check REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS bot_settings (setting_key TEXT PRIMARY KEY, setting_value TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS subreddits (subreddit_name TEXT PRIMARY KEY, checked_subreddits REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS osrs_users (username TEXT PRIMARY KEY, highscore REAL)')
    
    conn.commit()
    conn.close()

@tasks.loop(minutes=10)
async def change_status():
    server = client.guilds[0]
    display_names = [member.display_name for member in server.members]
    
    statuses = [
        Game(name=f"with {random.choice(display_names)}'s knob"),
        Game(name="Hentai Hunter"),
        discord.Activity(type=ActivityType.watching, name=f"{random.choice(display_names)}'s every move"),
        discord.Activity(type=ActivityType.watching, name=f"The Boys"),
        discord.Activity(type=ActivityType.listening, name="EDEN")
    ]
    
    status = random.choice(statuses)
    await client.change_presence(activity=status)

@client.event
async def on_ready():
    await change_status.start()

async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await client.load_extension(f"cogs.{filename[:-3]}")

async def main():
    initialize_database()
    await load_extensions()
    await client.start(os.getenv("TOKEN"))

asyncio.run(main())