import discord
from discord.ext import commands, tasks
import sqlite3
import asyncio
import feedparser
from datetime import datetime
import time
import re

class UserUpdates(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.CHANNEL_ID = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.CHANNEL_ID = self.get_watched_anime_channel_id()
        print(f'Loaded /mal/userupdates cog')
        self.check_new_watched_anime.start()

    def cog_unload(self):
        self.check_new_watched_anime.cancel()

    @tasks.loop(minutes=5)
    async def check_new_watched_anime(self):
        try:
            if self.CHANNEL_ID:
                conn = sqlite3.connect('db/mal_users.db')
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute('SELECT mal_username, last_check FROM mal_users')
                users = c.fetchall()

                for user in users:
                    mal_username, last_check = user
                    feed_url = f'https://myanimelist.net/rss.php?type=rwe&u={mal_username}'
                    feed = feedparser.parse(feed_url)

                    for entry in reversed(feed.entries):
                        entry_time = int(time.mktime(entry.published_parsed))

                        if entry_time > last_check:
                            anime_title = entry.title
                            anime_url = entry.link
                            anime_episode = entry.description

                            match = re.search(r'Watching - (\d+)', anime_episode)
                            episode_number = match.group(1) if match else "Unknown"

                            embed = discord.Embed(title=f"Watched {anime_title} - Episode {episode_number}", url=anime_url, color=0x7289DA)
                            embed.set_author(name=mal_username, url=f'https://myanimelist.net/profile/{mal_username}')
                            embed.set_footer(text=f"MyAnimeList", icon_url='https://image.myanimelist.net/ui/OK6W_koKDTOqqqLDbIoPAiC8a86sHufn_jOI-JGtoCQ')

                            channel = self.client.get_channel(int(self.CHANNEL_ID))
                            await channel.send(embed=embed)

                            await asyncio.sleep(3)

                    with conn:
                        conn.execute('UPDATE mal_users SET last_check = ? WHERE mal_username = ?', (entry_time, mal_username))

                print("Watched anime checked.")
            else:
                print("No valid channel ID set for MAL UserUpdates. Skipping check.")

        except Exception as e:
            print(f"Error checking for new watched anime: {str(e)}")

    def get_watched_anime_channel_id(self):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "channel_id"')
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def set_watched_anime_channel_id(self, channel_id):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', ('channel_id', channel_id))
        conn.commit()
        conn.close()
        self.CHANNEL_ID = channel_id

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setuserchannel(self, ctx, channel_id):
        self.set_watched_anime_channel_id(channel_id)

        channel = self.client.get_channel(int(channel_id))
        channel_name = channel.name if channel else "Unknown Channel"
        channel_link = f"https://discord.com/channels/{ctx.guild.id}/{channel_id}"

        await ctx.send(f"New watched anime updates will now be found in [{channel_name}]({channel_link}), these are updated daily.")

async def setup(client):
    await client.add_cog(UserUpdates(client))
