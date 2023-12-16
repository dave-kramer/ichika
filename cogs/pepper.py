import discord
from discord.ext import commands, tasks
import feedparser
import sqlite3
import json

class Pepper(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.CHANNEL_ID = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.CHANNEL_ID = self.get_pepper_channel_id()
        print(f'Loaded Pepper cog')
        self.check_pepper.start()

    def cog_unload(self):
        self.check_pepper.cancel()

    @tasks.loop(seconds=60)
    async def check_pepper(self):
        try:
            if self.CHANNEL_ID:
                feed_url = 'https://nl.pepper.com/rss/nieuw'
                feed = feedparser.parse(feed_url)

                if feed.bozo:
                    print('Error fetching nl.pepper.com. Please try again later.')
                    return

                entries = reversed(feed.entries[:5])
                previous_entry_ids = self.get_previous_pepper_entry_ids()
                current_state = []

                for entry in entries:
                    entry_id = int(entry.guid.split('-')[-1])
                    current_state.append(entry_id)

                    if entry_id not in previous_entry_ids:
                        title = entry.title
                        link = entry.link

                        embed = discord.Embed(title=f"{title}", url=link, color=0x1ED760)

                        if 'pepper_merchant' in entry:
                            price = entry['pepper_merchant'].get('price', 'Price not available')
                            embed.add_field(name="Price", value=price, inline=True)

                            if 'name' in entry['pepper_merchant']:
                                embed.add_field(name="Sold by", value=entry['pepper_merchant']['name'], inline=True)

                        if 'media_content' in entry and entry['media_content']:
                            media_url = entry['media_content'][0].get('url', '')
                            embed.set_thumbnail(url=media_url)
                        elif 'media_thumbnail' in entry and entry['media_thumbnail']:
                            media_url = entry['media_thumbnail'][0].get('url', '')
                            embed.set_thumbnail(url=media_url)


                        embed.set_footer(text='Pepper', icon_url='https://i.imgur.com/ut8mhPb.png')

                        channel = self.client.get_channel(int(self.CHANNEL_ID))
                        await channel.send(embed=embed)

                self.set_previous_pepper_entry_ids(current_state)
                print("Pepper checked.")

            else:
                print("No valid channel ID set for Pepper. Skipping check.")

        except Exception as e:
            print(f"Error checking for latest pepper: {str(e)}")

    def get_pepper_channel_id(self):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "pepper_channel_id"')
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def set_pepper_channel_id(self, channel_id):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', ('pepper_channel_id', str(channel_id)))
        conn.commit()
        conn.close()
        self.CHANNEL_ID = channel_id

    def get_previous_pepper_entry_ids(self):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "previous_pepper_entry_ids"')
        result = c.fetchone()
        conn.close()
        return [int(entry_id) for entry_id in result[0].split(',')] if result and result[0] else []

    def set_previous_pepper_entry_ids(self, previous_pepper_entry_ids):
        entry_ids_str = ','.join(map(str, previous_pepper_entry_ids))
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', ('previous_pepper_entry_ids', entry_ids_str))
        conn.commit()
        conn.close()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setpepperchannel(self, ctx, channel_id):
        self.set_pepper_channel_id(channel_id)

        channel = self.client.get_channel(int(channel_id))
        channel_name = channel.name if channel else "Unknown Channel"
        channel_link = f"https://discord.com/channels/{ctx.guild.id}/{channel_id}"

        await ctx.send(f"nl.pepper.com updates will now be found in [{channel_name}]({channel_link}), from now on you'll receive the latest pepper.")

async def setup(client):
    await client.add_cog(Pepper(client))
