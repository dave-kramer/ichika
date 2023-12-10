# cogs/trailers.py
import discord
from discord.ext import commands, tasks
import requests
import sqlite3
import asyncio

class Trailers(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.TRAILER_CHANNEL_ID = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.TRAILER_CHANNEL_ID = self.get_trailer_channel_id()
        print(f'Loaded /mal/trailers cog')
        self.check_new_trailers.start()

    def cog_unload(self):
        self.check_new_trailers.cancel()

    @tasks.loop(seconds=600)
    async def check_new_trailers(self):
        try:
            if self.TRAILER_CHANNEL_ID:
                response = requests.get('https://api.jikan.moe/v4/watch/promos')
                data = response.json()

                if response.status_code == 200:
                    trailers = data.get('data', [])
                    previous_state = self.get_previous_trailer_state()
                    current_state = []

                    for trailer in reversed(trailers):
                        youtube_id = trailer.get('trailer', {}).get('youtube_id', '')
                        current_state.append(youtube_id)

                        if youtube_id and youtube_id not in previous_state:
                            entry_title = trailer.get('entry', {}).get('title', 'Unknown Title')
                            entry_url = trailer.get('entry', {}).get('url', '')
                            title = trailer.get('title', '')
                            message = f"[{entry_title}]({entry_url}) - [{title}](https://www.youtube.com/watch?v={youtube_id})"
                            channel = self.client.get_channel(int(self.TRAILER_CHANNEL_ID))
                            await channel.send(message)

                    self.set_previous_trailer_state(current_state)
                    print("Trailers checked.")

                else:
                    print(f"Error fetching MAL Trailers. Status Code: {response.status_code}")
            else:
                print("No valid channel ID set for trailers. Skipping check.")

        except Exception as e:
            print(f"Error checking for new trailers: {str(e)}")

    def get_previous_trailer_state(self):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "previous_trailer_state"')
        result = c.fetchone()
        conn.close()
        return result[0].split(',') if result and result[0] else []

    def set_previous_trailer_state(self, previous_state):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        serialized_state = ','.join(previous_state)
        c.execute('INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', ('previous_trailer_state', serialized_state))
        conn.commit()
        conn.close()

    def get_trailer_channel_id(self):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "trailer_channel_id"')
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def set_trailer_channel_id(self, channel_id):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', ('trailer_channel_id', channel_id))
        conn.commit()
        conn.close()
        self.TRAILER_CHANNEL_ID = channel_id

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def settrailerchannel(self, ctx, channel_id):
        self.set_trailer_channel_id(channel_id)
        channel = self.client.get_channel(int(channel_id))
        channel_name = channel.name if channel else "Unknown Channel"
        channel_link = f"https://discord.com/channels/{ctx.guild.id}/{channel_id}"
        await ctx.send(f"New trailers will now be found in [{channel_name}]({channel_link}), please note that it may take a moment for the trailers to appear.")

async def setup(client):
    await client.add_cog(Trailers(client))
