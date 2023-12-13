import discord
from discord.ext import commands, tasks
import requests
import sqlite3
import asyncio

class OSRSHiscores(commands.Cog):
    skills = [
        "Overall", "Attack", "Defence", "Strength", "Hitpoints",
        "Ranged", "Prayer", "Magic", "Cooking", "Woodcutting",
        "Fletching", "Fishing", "Firemaking", "Crafting", "Smithing",
        "Mining", "Herblore", "Agility", "Thieving", "Slayer",
        "Farming", "Runecrafting", "Hunter", "Construction"
    ]

    def __init__(self, client):
        self.client = client
        self.highscore_channel_id = None
        self.dailyhighscore_channel_id = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.highscore_channel_id = self.get_highscore_channel_id()
        self.dailyhighscore_channel_id = self.get_dailyhighscore_channel_id()
        print(f'Loaded /osrs/highscores cog')
        self.compare_highscores.start()

    def cog_unload(self):
         self.compare_highscores.cancel()

    @tasks.loop(hours=24)
    async def compare_highscores(self):
        try:
            if self.dailyhighscore_channel_id:
                conn = sqlite3.connect('db/mal_users.db')
                c = conn.cursor()

                try:
                    c.execute('SELECT username, highscore FROM osrs_users')
                    rows = c.fetchall()

                    for username, stored_highscore_str in rows:
                        stored_highscore = eval(stored_highscore_str) 

                        new_highscore = self.fetch_hiscores(username)
                        if new_highscore:
                            await self.send_highscore_difference(username, stored_highscore, new_highscore)
                        
                        await asyncio.sleep(5)

                    conn.close()
                except Exception as e:
                    print(f"Error comparing highscores: {e}")
                    conn.close()
            else:
                print("No valid channel ID set for OSRS daily highscores. Skipping check.")
        except Exception as e:
            print(f"Error checking for OSRS daily highscores: {str(e)}")

    async def send_highscore_difference(self, username, stored_highscore, new_highscore):
        try:
            conn = sqlite3.connect('db/mal_users.db')
            c = conn.cursor()
            c.execute('UPDATE osrs_users SET highscore = ? WHERE LOWER(username) = ?', (str(new_highscore), username.lower()))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error updating OSRS stats data for {username} in the database: {e}")
            conn.close()

        embed = discord.Embed(color=0xFF0000)
        formatted_username = username.replace("_", " ").capitalize()
        embed.set_author(name=formatted_username, icon_url='https://oldschool.runescape.wiki/images/HiScores_icon.png')

        stored_overall_data = stored_highscore[0].split(',')
        new_overall_data = new_highscore[0].split(',')
        stored_overall_level, stored_overall_experience = map(int, stored_overall_data[1:3])
        new_overall_level, new_overall_experience = map(int, new_overall_data[1:3])

        for skill, (stored_data, new_data) in zip(self.skills[1:], zip(stored_highscore[1:], new_highscore[1:])):
            stored_level, stored_experience = map(int, stored_data.split(',')[1:3])
            new_level, new_experience = map(int, new_data.split(',')[1:3])
            emoji = discord.utils.get(self.client.guilds[0].emojis, name=skill.lower())

            if stored_level < new_level:
                embed.add_field(
                    name=f"{emoji} {stored_level} → {new_level}",
                    value=f"{format(new_experience, ',')} XP",
                    inline=True
                )
            else:
                embed.add_field(
                    name=f"{emoji} {stored_level}",
                    value=f"{format(new_experience, ',')} XP",
                    inline=True
                )

        overall_emoji = discord.utils.get(self.client.guilds[0].emojis, name="overall")

        if stored_overall_level < new_overall_level:
            embed.add_field(
                name=f"{overall_emoji} {stored_overall_level} → {new_overall_level}",
                value=f"{format(new_overall_experience, ',')} XP",
                inline=True
            )
        else:
            embed.add_field(
                name=f"{overall_emoji} {stored_overall_level}",
                value=f"{format(new_overall_experience, ',')} XP",
                inline=True
            )

        embed.set_footer(text="Oldschool Runescape's Daily Highscore", icon_url='https://media.kbin.social/media/43/d4/43d476bdb07dfe85e0356a04dc681d0eeb66fab81da43874372d4a10960932da.png')

        channel = self.client.get_channel(int(self.dailyhighscore_channel_id))
        await channel.send(embed=embed)


    def fetch_hiscores(self, username):
        url = f'https://secure.runescape.com/m=hiscore_oldschool/index_lite.ws?player={username}'

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.text.split('\n')
            return data
        except requests.RequestException as e:
            print(f"Error fetching Old School RuneScape stats for {username}: {e}")
            return None
        

    @commands.command(name='highscore')
    async def osrs_stats(self, ctx, username):
        try:
            if self.highscore_channel_id:
                hiscores_data = self.fetch_hiscores(username)

                if hiscores_data:
                    embed = discord.Embed(color=0x00ff00)

                    embed.set_author(name=username.capitalize(), icon_url='https://oldschool.runescape.wiki/images/HiScores_icon.png')

                    for skill, data_line in zip(self.skills[1:], hiscores_data[1:]):
                        rank, level, experience = map(int, data_line.split(','))
                        emoji = discord.utils.get(ctx.guild.emojis, name=skill.lower())

                        embed.add_field(
                            name=f"{emoji} {level}",
                            value=f"{format(experience, ',')} XP",
                            inline=True
                        )

                    overall_rank, overall_level, overall_experience = map(int, hiscores_data[0].split(','))
                    overall_emoji = discord.utils.get(ctx.guild.emojis, name="overall")

                    embed.add_field(
                        name=f"{overall_emoji} {overall_level}",
                        value=f"{format(overall_experience, ',')} XP",
                        inline=True
                    )

                    embed.set_footer(text='Oldschool Runescape', icon_url='https://media.kbin.social/media/43/d4/43d476bdb07dfe85e0356a04dc681d0eeb66fab81da43874372d4a10960932da.png')
                    
                    channel = self.client.get_channel(int(self.highscore_channel_id))
                    await channel.send(embed=embed)
                else:
                    await ctx.send(f"Error fetching Old School RuneScape stats for {username}")
            else:
                print("No valid channel ID set for OSRS highscores & addosrsuser/removeosrsuser")
        except Exception as e:
            print(f"Error checking for OSRS highscores & addosrsuser/removeosrsuser: {str(e)}")


    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addosrsuser(self, ctx, *args):
        try:
            if self.highscore_channel_id:
                username = ' '.join(args)
                conn = sqlite3.connect('db/mal_users.db')
                c = conn.cursor()

                try:
                    username_processed = username.lower().replace(' ', '_')

                    hiscores_data = self.fetch_hiscores(username_processed)
                    if hiscores_data is None:
                        await ctx.send(f"{username} is not found on the OSRS highscores.")
                        conn.close()
                        return

                    c.execute('SELECT * FROM osrs_users WHERE LOWER(username) = ?', (username_processed,))
                    if c.fetchone():
                        await ctx.send(f"{username} is already in the OSRS users database.")
                        conn.close()
                        return

                    initial_highscore_str = str(hiscores_data)
                    c.execute('INSERT INTO osrs_users (username, highscore) VALUES (?, ?)', (username_processed, initial_highscore_str))
                    conn.commit()
                    conn.close()

                    await ctx.send(f"{username} added to the OSRS users database.")
                except Exception as e:
                    await ctx.send(f"An error occurred while adding {username} to the OSRS users database: {e}")
                    conn.close()
            else:
                print("No valid channel ID set for OSRS highscores & addosrsuser/removeosrsuser")
        except Exception as e:
            print(f"Error checking for OSRS highscores & addosrsuser/removeosrsuser: {str(e)}")


    @commands.command()
    @commands.has_permissions(administrator=True)
    async def removeosrsuser(self, ctx, *args):
        try:
            if self.highscore_channel_id:
                username = ' '.join(args)
                conn = sqlite3.connect('db/mal_users.db')
                c = conn.cursor()

                try:
                    username_processed = username.lower().replace(' ', '_')

                    c.execute('SELECT * FROM osrs_users WHERE LOWER(username) = ?', (username_processed,))
                    if not c.fetchone():
                        await ctx.send(f"{username} is not in the OSRS users database.")
                        conn.close()
                        return

                    c.execute('DELETE FROM osrs_users WHERE LOWER(username) = ?', (username_processed,))
                    conn.commit()
                    conn.close()

                    await ctx.send(f"{username} removed from the OSRS users database.")
                except Exception as e:
                    await ctx.send(f"An error occurred while removing {username} from the OSRS users database: {e}")
                    conn.close()
            else:
                print("No valid channel ID set for OSRS highscores & addosrsuser/removeosrsuser")
        except Exception as e:
            print(f"Error checking for OSRS OSRS highscores & addosrsuser/removeosrsuser: {str(e)}")

    def get_highscore_channel_id(self):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "highscore_channel_id"')
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def set_highscore_channel_id(self, channel_id):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', ('highscore_channel_id', channel_id))
        conn.commit()
        conn.close()
        self.highscore_channel_id = channel_id

    def get_dailyhighscore_channel_id(self):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "dailyhighscore_channel_id"')
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def set_dailyhighscore_channel_id(self, channel_id):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', ('dailyhighscore_channel_id', channel_id))
        conn.commit()
        conn.close()
        self.dailyhighscore_channel_id = channel_id

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setosrschannel(self, ctx, functionality, channel_id):
        functionality = functionality.lower()

        if functionality not in ['highscore', 'dailyhighscore']:
            await ctx.send("Invalid functionality. Please use 'highscore' or 'dailyhighscore'.")
            return

        if not channel_id.isdigit():
            await ctx.send("Invalid channel ID. Please provide a valid numerical channel ID.")
            return

        channel_id = int(channel_id)

        if functionality == 'highscore':
            self.set_highscore_channel_id(channel_id)
            await ctx.send(f"OSRS Highscore channel set to <#{channel_id}>.")
        elif functionality == 'dailyhighscore':
            self.set_dailyhighscore_channel_id(channel_id)
            await ctx.send(f"OSRS Daily Highscores channel set to <#{channel_id}>.")

async def setup(client):
    await client.add_cog(OSRSHiscores(client))
