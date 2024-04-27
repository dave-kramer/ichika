import discord
from discord.ext import commands, tasks
import requests
import sqlite3
import base64
import json
import time

class Reddit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.CHANNEL_ID = None
        self.reddit_credentials = self.load_reddit_credentials()

    @commands.Cog.listener()
    async def on_ready(self):
        self.CHANNEL_ID = self.get_watched_subreddit_channel_id()
        print(f'Loaded reddit cog')
        self.check_threads.start()

    def load_reddit_credentials(self):
        try:
            with open("reddit.json", "r") as config_file:
                config_data = json.load(config_file)
                return config_data.get("reddit", {})
        except FileNotFoundError:
            print("reddit.json not found. Add reddit client id & client secret")
            return {}

    @tasks.loop(seconds=60)
    async def check_threads(self):
        try:
            if self.CHANNEL_ID:
                subreddits = self.get_monitored_subreddits()

                if not subreddits:
                    print("No monitored subreddits. Skipping check.")
                    return

                for subreddit in subreddits:
                    print(subreddit)
                    threads = self.get_latest_threads(subreddit)
                    last_check = self.get_last_check(subreddit)

                    for thread in reversed(threads):
                        thread_created = thread['data']['created']

                        if thread_created > last_check:
                            title = thread['data']['title']
                            description = thread['data']['selftext']
                            thumbnail = thread['data']['thumbnail']
                            author = thread['data']['author']
                            thread_id = thread['data']['id']

                            embed = discord.Embed(title=title, url=f'https://www.reddit.com/r/eden/comments/{thread_id}/', description=description, color=0x00ff00)
                            if thumbnail.lower() != "self":
                                embed.set_thumbnail(url=thumbnail)
                            embed.set_footer(text=f'{author} @ /r/{subreddit}', icon_url='https://github.com/dave-kramer/ichika/blob/main/icons/reddit.png?raw=true')

                            channel = self.bot.get_channel(int(self.CHANNEL_ID))
                            await channel.send(embed=embed)

                            self.update_database(subreddit, thread_created)

                print("Subreddits checked.")
            else:
                print("No valid channel ID set for Reddit. Skipping check.")

        except Exception as e:
            print(f"Error checking for latest subreddit: {str(e)}")

    def update_database(self, subreddit, thread_created):
        try:
            conn = sqlite3.connect('db/mal_users.db')
            c = conn.cursor()
            c.execute('UPDATE subreddits SET last_check = ? WHERE subreddit_name = ?;', (thread_created, subreddit))
            conn.commit()

        except Exception as e:
            print(f"Error updating database: {str(e)}")

        finally:
            conn.close()

    def get_last_check(self, subreddit):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('SELECT last_check FROM subreddits WHERE subreddit_name = ?', (subreddit,))
        result = c.fetchone()
        conn.close()
        if result and result[0]:
            return result[0]
        else:
            return None

    def get_latest_threads(self, subreddit):
        base_url = 'https://oauth.reddit.com/r/'
        category = '/new'

        params = {
            'after': None,
            'before': None,
            'count': 0,
            'limit': 5,
            'show': 'all',
            'sr_detail': False,
        }

        headers = {
            'User-Agent': 'ichika/1.0',
            'Authorization': f'bearer {self.get_access_token()}',
        }

        response = requests.get(f'{base_url}{subreddit}{category}.json', params=params, headers=headers)

        if response.status_code == 200:
            data = response.json()
            return data['data']['children']
        else:
            print(f'Error retrieving threads from {subreddit}. Please try again later.')
            return []

    def get_access_token(self):
        client_id = self.reddit_credentials.get("client_id")
        client_secret = self.reddit_credentials.get("client_secret")

        credentials = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Basic {credentials}",
            "User-Agent": "ichika/1.0", 
        }

        data = {
            "grant_type": "client_credentials",
        }

        response = requests.post("https://www.reddit.com/api/v1/access_token", headers=headers, data=data)

        if response.status_code == 200:
            token_data = response.json()
            return token_data.get("access_token")
        else:
            print(f"Error obtaining access token: {response.text}")
            return None

    def get_monitored_subreddits(self):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('SELECT subreddit_name FROM subreddits')
        result = c.fetchall()
        conn.close()
        return [row[0] for row in result]

    def get_watched_subreddit_channel_id(self):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "reddit_channel_id"')
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def set_watched_subreddit_channel_id(self, channel_id):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', ('reddit_channel_id', channel_id))
        conn.commit()
        conn.close()
        self.CHANNEL_ID = channel_id

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setredditchannel(self, ctx, channel_id):
        self.set_watched_subreddit_channel_id(channel_id)

        channel = self.bot.get_channel(int(channel_id))
        channel_name = channel.name if channel else "Unknown Channel"
        channel_link = f"https://discord.com/channels/{ctx.guild.id}/{channel_id}"

        await ctx.send(f"New watched subreddit updates will now be found in [{channel_name}]({channel_link}), these are updated daily.")

    @commands.command()
    async def addsubreddit(self, ctx, subreddit):
        self.add_subreddit(subreddit)
        await ctx.send(f'Subreddit [r/{subreddit}](https://www.reddit.com/r/{subreddit}) added for monitoring.')

    @commands.command()
    async def removesubreddit(self, ctx, subreddit):
        self.remove_subreddit(subreddit)
        await ctx.send(f'Subreddit [r/{subreddit}](https://www.reddit.com/r/{subreddit}) removed from monitoring.')

    def add_subreddit(self, subreddit):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        current_timestamp = int(time.time())
        c.execute('INSERT INTO subreddits (subreddit_name, last_check) VALUES (?, ?)', (subreddit, current_timestamp))
        conn.commit()
        conn.close()

    def remove_subreddit(self, subreddit):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('DELETE FROM subreddits WHERE subreddit_name = ?', (subreddit,))
        conn.commit()
        conn.close()

async def setup(client):
    await client.add_cog(Reddit(client))
