import os
import discord
from discord.ext import commands
import requests
import sqlite3
from datetime import datetime

class User(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Loaded /mal/user cog')

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def adduser(self, ctx, mal_username):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()

        response = requests.get(f'https://api.jikan.moe/v4/users/{mal_username}/full')

        if response.status_code == 200:
            current_time = datetime.utcnow().timestamp()
            c.execute('INSERT INTO mal_users (mal_username, last_check) VALUES (?, ?)', (mal_username, current_time))
            conn.commit()
            conn.close()

            data = response.json()
            thumbnail_url = data['data']['images']['jpg']['image_url']
            gender = data['data']['gender']
            birthday = data['data']['birthday']

            if birthday is not None:
                birthday = datetime.strptime(birthday, "%Y-%m-%dT%H:%M:%S+00:00").strftime("%b %d, %Y")
            else:
                birthday = "N/A"

            location = data['data']['location']
            total_anime = data['data']['statistics']['anime']['total_entries']
            days_watched = data['data']['statistics']['anime']['days_watched']
            mean_score = data['data']['statistics']['anime']['mean_score']
            completed_anime = data['data']['statistics']['anime']['completed']
            total_episodes = data['data']['statistics']['anime']['episodes_watched']
            dropped_anime = data['data']['statistics']['anime']['dropped']
            favorite_anime = data['data']['favorites']['anime'][:10]
            favorite_characters = data['data']['favorites']['characters'][:10]

            favorite_anime_list = "\n".join([f"[{anime['title']}]({anime['url']})" for anime in favorite_anime])
            favorite_characters_list = "\n".join([f"[{character['name']}]({character['url']})" for character in favorite_characters])

            embed = discord.Embed(title=f"Added {mal_username} to Watch Updates", url=f"https://myanimelist.net/profile/{mal_username}", color=0x00ff00)
            embed.set_thumbnail(url=thumbnail_url)
            embed.add_field(name="Gender", value=gender, inline=True)
            embed.add_field(name="Birthday", value=birthday, inline=True)
            embed.add_field(name="Location", value=location, inline=True)
            embed.add_field(name="Total anime", value=total_anime, inline=True)
            embed.add_field(name="Days watched", value=days_watched, inline=True)
            embed.add_field(name="Mean score", value=mean_score, inline=True)
            embed.add_field(name="Completed", value=completed_anime, inline=True)
            embed.add_field(name="Total episodes", value=total_episodes, inline=True)
            embed.add_field(name="Dropped", value=dropped_anime, inline=True)
            embed.add_field(name="Favorite Anime", value=favorite_anime_list, inline=False)
            embed.add_field(name="Favorite Characters", value=favorite_characters_list, inline=False)

            await ctx.send(embed=embed)
        else:
            await ctx.send(f"{mal_username} does not exist on MyAnimeList.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def removeuser(self, ctx, mal_username):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('DELETE FROM mal_users WHERE mal_username = ?', (mal_username,))
        conn.commit()
        conn.close()

        await ctx.send(f"{mal_username} removed from MyAnimeList user updates")

async def setup(client):
    await client.add_cog(User(client))

