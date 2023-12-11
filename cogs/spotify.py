import discord
from discord.ext import commands, tasks
import sqlite3

class Spotify(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.CHANNEL_ID = None
        self.last_song = {}

    @commands.Cog.listener()
    async def on_ready(self):
        self.CHANNEL_ID = self.get_spotify_channel_id()
        print(f'Loaded Spotify cog')
        self.spotify_check.start()

    def cog_unload(self):
        self.spotify_check.cancel()

    @tasks.loop(seconds=15)
    async def spotify_check(self):
        try:
            if self.CHANNEL_ID:
                channel = self.client.get_channel(int(self.CHANNEL_ID))
                if not channel:
                    print("Invalid channel ID. Exiting loop.")
                    return

                for guild in self.client.guilds:
                    for member in guild.members:
                        if member.activities:
                            for activity in member.activities:
                                if isinstance(activity, discord.Spotify):
                                    user_id = str(member.id)
                                    current_song = activity.title

                                    # Check if the user's last song is different
                                    if user_id not in self.last_song or self.last_song[user_id] != current_song:
                                        await self.send_spotify_embed(channel, member, activity)
                                        self.last_song[user_id] = current_song

            else:
                print("No valid channel ID set for Spotify. Skipping check.")

        except Exception as e:
            print(f"Error checking for latest Spotify activity: {str(e)}")

    async def send_spotify_embed(self, channel, member, activity):
        artists = activity.artist.split("; ")
        artists_str = ", ".join(artists)

        embed = discord.Embed(title=f"{activity.title}", url=f"https://open.spotify.com/track/{activity.track_id}", color=0x1ED760)

        embed.add_field(name="Album", value=activity.album, inline=True)
        embed.add_field(name="Artists", value=artists_str, inline=True)

        if activity.album_cover_url:
            embed.set_thumbnail(url=activity.album_cover_url)

        embed.set_author(name=member.display_name, icon_url=member.avatar.url)
        embed.set_footer(text='Spotify', icon_url='https://github.com/dave-kramer/ichika/blob/main/icons/spotify.png?raw=true')

        await channel.send(embed=embed)

    def get_spotify_channel_id(self):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "spotify_channel_id"')
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def set_spotify_channel_id(self, channel_id):
        conn = sqlite3.connect('db/mal_users.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', ('spotify_channel_id', str(channel_id)))
        conn.commit()
        conn.close()
        self.CHANNEL_ID = channel_id

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setspotifychannel(self, ctx, channel_id):
        self.set_spotify_channel_id(channel_id)

        channel = self.client.get_channel(int(channel_id))
        channel_name = channel.name if channel else "Unknown Channel"
        channel_link = f"https://discord.com/channels/{ctx.guild.id}/{channel_id}"

        await ctx.send(f"Spotify will now be found in [{channel_name}]({channel_link}), and announcements will be made.")

async def setup(client):
    await client.add_cog(Spotify(client))
