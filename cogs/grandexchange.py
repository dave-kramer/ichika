import discord
from discord.ext import commands
import requests
import sqlite3

class GrandExchange(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.channel_id = None
        self.base_url = 'https://api.weirdgloop.org/exchange/history/osrs/latest'

    @commands.Cog.listener()
    async def on_ready(self):
        self.channel_id = self.get_ge_channel_id()
        print(f'Loaded /osrs/ge cog')

    def get_ge_data(self, item_name):
        params = {'name': item_name, 'lang': 'en'}
        response = requests.get(self.base_url, params=params, headers={'accept': 'application/json'})
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            return None

    @commands.command(name='ge')
    async def ge_command(self, ctx, *, item_name):
        try:
            if self.channel_id:
                ge_data = self.get_ge_data(item_name)

                if ge_data:
                    item_name = list(ge_data.keys())[0]
                    item_name_img = item_name.capitalize().replace(' ', '_')
                    title_url = f'https://oldschool.runescape.wiki/w/{item_name_img}'
                    thumbnail_url = f'https://oldschool.runescape.wiki/images/{item_name_img}.png'
                    item_data = ge_data[item_name]

                    embed = discord.Embed(
                        title=item_name,
                        url=title_url,
                        color=discord.Color.green(),
                    )
                    embed.add_field(name="Price", value=f"{format(item_data['price'], ',')}")
                    embed.add_field(name="Volume", value=f"{format(item_data['volume'], ',')}")

                    if self.image_exists(thumbnail_url):
                        embed.set_thumbnail(url=thumbnail_url)
                    else:
                        embed.set_thumbnail(url='https://oldschool.runescape.wiki/images/thumb/Grand_Exchange_logo.png/150px-Grand_Exchange_logo.png')

                    embed.set_footer(text=f'Grand Exchange', icon_url='https://oldschool.runescape.wiki/images/thumb/Grand_Exchange_logo.png/150px-Grand_Exchange_logo.png')
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"No data found for {item_name}")
            else:
                print("No valid channel ID set for OSRS GE")
        except Exception as e:
            print(f"Error checking for OSRS GE: {str(e)}")

    def image_exists(self, url):
        try:
            response = requests.head(url)
            return response.status_code == 200
        except requests.RequestException:
            return False
        
    def get_ge_channel_id(self):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "ge_channel_id"')
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def set_ge_channel_id(self, channel_id):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', ('ge_channel_id', channel_id))
        conn.commit()
        conn.close()
        self.channel_id = channel_id

    @commands.command(name='setgechannel')
    async def set_ge_channel_command(self, ctx):
        try:
            channel_id = ctx.channel.id
            self.set_ge_channel_id(channel_id)
            await ctx.send(f"OSRS GE channel set to {ctx.channel.mention}")
        except Exception as e:
            print(f"Error setting OSRS GE channel: {str(e)}")

async def setup(client):
    await client.add_cog(GrandExchange(client))
