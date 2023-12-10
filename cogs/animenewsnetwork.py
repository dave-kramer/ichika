import discord
from discord.ext import commands, tasks
import feedparser
import sqlite3
from datetime import datetime

class AnimeNewsNetwork(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.CHANNEL_ID = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.CHANNEL_ID = self.get_news_channel_id()
        print(f'Loaded animenewsnetwork cog')
        self.check_news.start()

    def cog_unload(self):
        self.check_news.cancel()

    @tasks.loop(seconds=300)
    async def check_news(self):
        try:
            if self.CHANNEL_ID:
                feed_url = 'https://www.animenewsnetwork.com/news/rss.xml?ann-edition=w'
                feed = feedparser.parse(feed_url)

                if feed.bozo:
                    print('Error fetching news. Please try again later.')
                    return

                entries = reversed(feed.entries[:5])
                previous_entry_ids = self.get_previous_news_entry_ids()
                current_state = []

                for entry in entries:
                    entry_id = int(entry.id.split('.')[-1])
                    current_state.append(entry_id)

                    if entry_id not in previous_entry_ids:
                        title = entry.title
                        link = entry.link

                        message_content = f"**Anime News Network:** [{title}]({link})\n{link}"

                        channel = self.client.get_channel(int(self.CHANNEL_ID))
                        await channel.send(message_content)

                self.set_previous_news_entry_ids(current_state)
                print("News checked.")

            else:
                print("No valid channel ID set for AnimeNewsNetwork. Skipping check.")

        except Exception as e:
            print(f"Error checking for latest news: {str(e)}")

    def get_news_channel_id(self):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "news_channel_id"')
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def set_news_channel_id(self, channel_id):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', ('news_channel_id', str(channel_id)))
        conn.commit()
        conn.close()
        self.CHANNEL_ID = channel_id

    def get_previous_news_entry_ids(self):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "previous_news_entry_ids"')
        result = c.fetchone()
        conn.close()
        return [int(entry_id) for entry_id in result[0].split(',')] if result is not None else []

    def set_previous_news_entry_ids(self, previous_news_entry_ids):
        entry_ids_str = ','.join(map(str, previous_news_entry_ids))
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', ('previous_news_entry_ids', entry_ids_str))
        conn.commit()
        conn.close()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setnewschannel(self, ctx, channel_id):
        self.set_news_channel_id(channel_id)

        channel = self.client.get_channel(int(channel_id))
        channel_name = channel.name if channel else "Unknown Channel"
        channel_link = f"https://discord.com/channels/{ctx.guild.id}/{channel_id}"

        await ctx.send(f"Anime news updates will now be found in [{channel_name}]({channel_link}), from now on you'll receive the latest news.")

async def setup(client):
    await client.add_cog(AnimeNewsNetwork(client))