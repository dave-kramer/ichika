import discord
from discord.ext import commands, tasks
from discord.interactions import Interaction
import requests
import sqlite3
import re
import asyncio

class GrandExchange(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.channel_id = None
        self.watchlist_channel_id = None
        self.base_url = 'https://api.weirdgloop.org/exchange/history/osrs/latest'
        self.item_detail_url = 'https://secure.runescape.com/m=itemdb_oldschool/api/catalogue/detail.json'
        self.emoji_mapping = {'positive': '⬆️', 'negative': '⬇️', 'neutral': '⚪️'}

    @commands.Cog.listener()
    async def on_ready(self):
        self.channel_id = self.get_ge_channel_id()
        self.watchlist_channel_id = self.get_watchlist_channel_id()
        print(f'Loaded /osrs/ge cog')
        self.check_watch_prices.start()

    def get_ge_data(self, item_name):
        params = {'name': item_name, 'lang': 'en'}
        response = requests.get(self.base_url, params=params, headers={'accept': 'application/json'})
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            return None
        
    def get_ge_data_by_id(self, item_id):
        params = {'id': item_id, 'lang': 'en'}
        response = requests.get(self.base_url, params=params, headers={'accept': 'application/json'})
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            return None

    def get_item_detail(self, item_id):
        params = {'item': item_id}
        response = requests.get(self.item_detail_url, params=params)
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            return None

    @commands.command(name='pricewatch')
    async def gewatch_command(self, ctx, *, input_string):
        try:
            if self.watchlist_channel_id:
                match = re.match(r'^(?P<item_name>.*?)(?P<watch_price>\d+)$', input_string)

                if match:
                    item_name = match.group('item_name').strip()
                    watch_price = int(match.group('watch_price'))
                    if 0 <= watch_price <= 2147483647:
                        ge_data = self.get_ge_data(item_name)
                        item_name_img = item_name.capitalize().replace(' ', '_')
                        title_url = f'https://oldschool.runescape.wiki/w/{item_name_img}'
                        thumbnail_url = f'https://oldschool.runescape.wiki/images/{item_name_img}.png'

                        if ge_data:
                            item_name = list(ge_data.keys())[0]
                            item_data = ge_data[item_name]
                            current_price = item_data['price']
                            trend_direction = 'above' if watch_price >= int(current_price) else 'below'
                            if watch_price != int(current_price):
                                user_id = str(ctx.author.id)
                                self.save_watch_details(item_data['id'], item_name, watch_price, trend_direction, user_id)
                                item_detail = self.get_item_detail(item_data['id'])
                                if item_detail:
                                    embed = discord.Embed(
                                        title=item_name,
                                        url=title_url,
                                        description=item_detail['item']['description'],
                                        color=discord.Color.green(),
                                    )
                                    embed.set_thumbnail(url=item_detail['item']['icon'])
                                    embed.add_field(name="Price", value=f"{format(item_data['price'], ',')}")
                                    embed.add_field(name="Watch Price", value=f"{format(watch_price, ',')}")
                                    members_text = ":white_check_mark:" if item_detail['item']['members'] else ":x:"
                                    embed.add_field(name="Members", value=members_text, inline=True)
                                    for period_key, display_name in [('today', 'Today'), ('day30', '30 Days'), ('day90', '90 Days'), ('day180', '180 Days')]:
                                        trend_value = item_detail['item'][period_key]['trend']
                                        
                                        arrow_emoji = self.emoji_mapping.get(trend_value, '⚪️')
                                        if period_key == 'today':
                                            price_value = item_detail['item'][period_key]['price']
                                        else:
                                            change_value = item_detail['item'][period_key]['change']
                                        embed.add_field(
                                            name=display_name,
                                            value=f"{arrow_emoji} {price_value if period_key == 'today' else change_value}",
                                            inline=True
                                        )
                                else:
                                    embed = discord.Embed(
                                        title=item_name,
                                        url=title_url,
                                        color=discord.Color.green(),
                                    )
                                    if self.image_exists(thumbnail_url):
                                        embed.set_thumbnail(url=thumbnail_url)
                                    else:
                                        embed.set_thumbnail(url='https://oldschool.runescape.wiki/images/thumb/Grand_Exchange_logo.png/150px-Grand_Exchange_logo.png')
                                        
                                    embed.add_field(name="Price", value=f"{format(item_data['price'], ',')}")
                                    embed.add_field(name="Watch Price", value=f"{format(watch_price, ',')}")

                                embed.add_field(name="Volume", value=f"{format(item_data['volume'], ',')}")
                                if ctx.author.avatar and ctx.author.avatar.url:
                                    embed.set_author(name=f"{ctx.author.display_name} has set an alert", icon_url=ctx.author.avatar.url)
                                else:
                                    embed.set_author(name=f"{ctx.author.display_name} has set an alert", icon_url=ctx.author.default_avatar.url)

                                embed.set_footer(text=f"Grand Exchange's Price Watcher", icon_url='https://oldschool.runescape.wiki/images/thumb/Grand_Exchange_logo.png/150px-Grand_Exchange_logo.png')
                                await ctx.send(embed=embed)

                            else:
                                await ctx.send(f"Watch price is already equal to the current price. No need to add to the watchlist.")
                        else:
                            await ctx.send(f"No data found for {item_name}")
                    else:
                        await ctx.send("Watch price must be between 0 and 2147483647.")
                else:
                    await ctx.send("Invalid format. Please use the format: `!gewatch <item_name> <watch_price>`")
            else:
                print("No valid channel ID set for OSRS GE's Price Watch")
        except Exception as e:
            print(f"Error checking for OSRS GE's Price Watch: {str(e)}")

    def save_watch_details(self, item_id, item_name, watch_price, trend_direction, user_id):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('INSERT INTO osrs_watchlist (item_id, item_name, watch_price, trend_direction, discord_user) VALUES (?, ?, ?, ?, ?)',
                (item_id, item_name, watch_price, trend_direction, user_id))
        conn.commit()
        conn.close()

    async def send_watch_alert(self, item_name, title_url, thumbnail_url, current_price, watch_price, trend_direction, user_id):
        embed = discord.Embed(
            title=item_name,
            url=title_url,
            description="The watch price has been reached, the item will now be removed from the Grand Exchange's Price Watcher.",
            color=discord.Color.green(),
        )
        user = self.client.get_user(int(user_id))
        embed.set_author(name=f"{user.display_name}'s Price Watch ✅", icon_url=user.avatar.url if user.avatar and user.avatar.url else user.default_avatar.url)
        if self.image_exists(thumbnail_url):
            embed.set_thumbnail(url=thumbnail_url)
        else:
            embed.set_thumbnail(url='https://oldschool.runescape.wiki/images/thumb/Grand_Exchange_logo.png/150px-Grand_Exchange_logo.png')
        embed.add_field(name="Current Price", value=f"{format(current_price, ',')}")
        embed.add_field(name="Watch Price", value=f"{format(int(watch_price), ',')}")
           
        embed.set_footer(text=f"Grand Exchange's Price Watcher", icon_url='https://oldschool.runescape.wiki/images/thumb/Grand_Exchange_logo.png/150px-Grand_Exchange_logo.png')
        channel = self.client.get_channel(int(self.watchlist_channel_id))

        await channel.send(embed=embed)

        user = self.client.get_user(int(user_id))
        if user:
            await user.send(embed=embed)

        self.delete_watch_details(item_name, user_id)

    @tasks.loop(hours=1)
    async def check_watch_prices(self):
        try:
            if self.watchlist_channel_id:
                watchlist_items = self.get_watchlist_items()
                for watch_item in watchlist_items:
                    id, item_id, item_name, watch_price, trend_direction, user_id = watch_item
                    ge_data = self.get_ge_data_by_id(item_id)
                    item_name_img = item_name.capitalize().replace(' ', '_')
                    title_url = f'https://oldschool.runescape.wiki/w/{item_name_img}'
                    thumbnail_url = f'https://oldschool.runescape.wiki/images/{item_name_img}.png'

                    if ge_data:
                        item_id = list(ge_data.keys())[0]
                        item_data = ge_data[item_id]
                        current_price = item_data['price']
                        print(current_price)
                        print(watch_price)
                        print(trend_direction)
                        if (trend_direction == 'above' and current_price <= watch_price) or (trend_direction == 'below' and current_price >= watch_price):
                            print(item_name)
                            await self.send_watch_alert(item_name, title_url, thumbnail_url, current_price, watch_price, trend_direction, user_id)
                    
                    else:
                        print("Couldn't get the API data for OSRS GE's Price Watch")

                    await asyncio.sleep(2)
                print("Checked all GE's price watch items.")
            else:
                print("No valid channel ID set for OSRS GE's Price Watch")
        except Exception as e:
            print(f"Error checking watch prices: {str(e)}")

    def delete_watch_details(self, item_name, user_id):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('DELETE FROM osrs_watchlist WHERE item_name = ? AND discord_user = ?', (item_name, user_id))
        conn.commit()
        conn.close()

    def get_watchlist_items(self):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('SELECT * FROM osrs_watchlist')
        result = c.fetchall()
        conn.close()
        return result

    @commands.command(name='removepricewatch')
    async def remove_ge_watch_command(self, ctx, *, item_name):
        try:
            if self.watchlist_channel_id:
                user_id = str(ctx.author.id)
                success = self.remove_watch_details_by_item_name(item_name, user_id)

                if success:
                    await ctx.send(f"{ctx.author.mention} successfully removed price watch for {item_name}.")
                else:
                    await ctx.send(f"{ctx.author.mention} no matching price watch found for {item_name}.")
            else:
                print("No valid channel ID set for OSRS GE's Price Watch")
        except Exception as e:
            print(f"Error removing OSRS GE's price watch: {str(e)}")

    def remove_watch_details_by_item_name(self, item_name, user_id):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('DELETE FROM osrs_watchlist WHERE item_name = ? AND discord_user = ?', (item_name, user_id))
        rows_affected = c.rowcount
        conn.commit()
        conn.close()
        return rows_affected > 0

    @commands.command(name='ge')
    async def ge_command(self, ctx, *, item_name):
        try:
            if self.channel_id:
                ge_data = self.get_ge_data(item_name)

                if ge_data:
                    item_name = list(ge_data.keys())[0]
                    item_name_img = item_name.capitalize().replace(' ', '_')
                    item_data = ge_data[item_name]
                    title_url = f'https://oldschool.runescape.wiki/w/{item_name_img}'
                    thumbnail_url = f'https://oldschool.runescape.wiki/images/{item_name_img}.png'

                    item_detail = self.get_item_detail(item_data['id'])
                    if item_detail:
                        embed = discord.Embed(
                            title=item_name,
                            url=title_url,
                            description=item_detail['item']['description'],
                            color=discord.Color.green(),
                        )
                        embed.set_thumbnail(url=item_detail['item']['icon'])
                        embed.add_field(name="Price", value=f"{format(item_data['price'], ',')}")
                        embed.add_field(name="Volume", value=f"{format(item_data['volume'], ',')}")
                        members_text = ":white_check_mark:" if item_detail['item']['members'] else ":x:"
                        embed.add_field(name="Members", value=members_text, inline=True)
                        for period_key, display_name in [('today', 'Today'), ('day30', '30 Days'), ('day90', '90 Days'), ('day180', '180 Days')]:
                            trend_value = item_detail['item'][period_key]['trend']
                            
                            arrow_emoji = self.emoji_mapping.get(trend_value, '⚪️')

                            if period_key == 'today':
                                price_value = item_detail['item'][period_key]['price']
                            else:
                                change_value = item_detail['item'][period_key]['change']

                            embed.add_field(
                                name=display_name,
                                value=f"{arrow_emoji} {price_value if period_key == 'today' else change_value}",
                                inline=True
                            )
                    else:
                        embed = discord.Embed(
                            title=item_name,
                            url=title_url,
                            color=discord.Color.green(),
                        )
                        if self.image_exists(thumbnail_url):
                            embed.set_thumbnail(url=thumbnail_url)
                        else:
                            embed.set_thumbnail(url='https://oldschool.runescape.wiki/images/thumb/Grand_Exchange_logo.png/150px-Grand_Exchange_logo.png')
                        embed.add_field(name="Price", value=f"{format(item_data['price'], ',')}")
                        embed.add_field(name="Volume", value=f"{format(item_data['volume'], ',')}")

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

    def get_watchlist_channel_id(self):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "watchlist_channel_id"')
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def set_watchlist_channel_id(self, channel_id):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', ('watchlist_channel_id', channel_id))
        conn.commit()
        conn.close()
        self.watchlist_channel_id = channel_id

    @commands.command(name='setgechannel')
    async def set_ge_channel_command(self, ctx):
        try:
            channel_id = ctx.channel.id
            self.set_ge_channel_id(channel_id)
            await ctx.send(f"OSRS GE channel set to {ctx.channel.mention}")
        except Exception as e:
            print(f"Error setting OSRS GE channel: {str(e)}")

    @commands.command(name='setpricewatchchannel')
    async def set_watchlist_channel_command(self, ctx):
        try:
            channel_id = ctx.channel.id
            self.set_watchlist_channel_id(channel_id)
            await ctx.send(f"OSRS GE Price Watch channel set to {ctx.channel.mention}")
        except Exception as e:
            print(f"Error setting OSRS GE's Price Watch channel: {str(e)}")

async def setup(client):
    await client.add_cog(GrandExchange(client))
