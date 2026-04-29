import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

queues = {}

YDL_PLAYLIST = {
    "format": "bestaudio/best",
    "quiet": True,
    "extract_flat": "in_playlist",
    "noplaylist": False,
}

YDL_AUDIO = {
    "format": "bestaudio/best",
    "quiet": True,
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn"
}


async def get_audio_url(url):
    loop = asyncio.get_event_loop()

    def run():
        with yt_dlp.YoutubeDL(YDL_AUDIO) as ydl:
            info = ydl.extract_info(url, download=False)
            return info["url"], info.get("title", "Unknown Title")

    return await loop.run_in_executor(None, run)


async def play_next(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    voice = interaction.guild.voice_client

    if not voice:
        return

    if guild_id not in queues or len(queues[guild_id]) == 0:
        await interaction.channel.send("✅ Queue sesh hoye geche.")
        return

    url, title = queues[guild_id].pop(0)
    audio_url, real_title = await get_audio_url(url)

    source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)

    voice.play(
        source,
        after=lambda e: asyncio.run_coroutine_threadsafe(
            play_next(interaction), bot.loop
        )
    )

    embed = discord.Embed(
        title="🎶 Now Playing",
        description=f"**{real_title}**",
        color=0x8A2BE2
    )
    await interaction.channel.send(embed=embed)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")
    print("✅ Slash commands synced")


@bot.tree.command(name="play", description="Play YouTube song or playlist")
@app_commands.describe(url="YouTube song/playlist link")
async def play(interaction: discord.Interaction, url: str):
    if not interaction.user.voice:
        return await interaction.response.send_message(
            "❌ Age voice channel e join koro.",
            ephemeral=True
        )

    await interaction.response.defer()

    if not interaction.guild.voice_client:
        await interaction.user.voice.channel.connect()

    guild_id = interaction.guild.id
    queues.setdefault(guild_id, [])

    await interaction.followup.send("🔎 Loading song/playlist...")

    loop = asyncio.get_event_loop()

    def extract():
        with yt_dlp.YoutubeDL(YDL_PLAYLIST) as ydl:
            return ydl.extract_info(url, download=False)

    info = await loop.run_in_executor(None, extract)

    if "entries" in info:
        count = 0
        for entry in info["entries"]:
            if entry:
                video_url = entry.get("url")
                if video_url and not video_url.startswith("http"):
                    video_url = "https://www.youtube.com/watch?v=" + video_url

                queues[guild_id].append(
                    (video_url, entry.get("title", "Unknown"))
                )
                count += 1

        await interaction.followup.send(
            f"✅ Playlist theke **{count}** ta song queue te add holo."
        )
    else:
        queues[guild_id].append((url, info.get("title", "Unknown")))
        await interaction.followup.send("✅ Song queue te add holo.")

    voice = interaction.guild.voice_client
    if not voice.is_playing():
        await play_next(interaction)


@bot.tree.command(name="skip", description="Skip current song")
async def skip(interaction: discord.Interaction):
    voice = interaction.guild.voice_client

    if voice and voice.is_playing():
        voice.stop()
        await interaction.response.send_message("⏭ Skipped.")
    else:
        await interaction.response.send_message("❌ Kichu play hocche na.")


@bot.tree.command(name="pause", description="Pause current song")
async def pause(interaction: discord.Interaction):
    voice = interaction.guild.voice_client

    if voice and voice.is_playing():
        voice.pause()
        await interaction.response.send_message("⏸ Paused.")
    else:
        await interaction.response.send_message("❌ Kichu play hocche na.")


@bot.tree.command(name="resume", description="Resume paused song")
async def resume(interaction: discord.Interaction):
    voice = interaction.guild.voice_client

    if voice and voice.is_paused():
        voice.resume()
        await interaction.response.send_message("▶️ Resumed.")
    else:
        await interaction.response.send_message("❌ Pause kora song nai.")


@bot.tree.command(name="queue", description="Show music queue")
async def queue(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    q = queues.get(guild_id, [])

    if not q:
        return await interaction.response.send_message("📭 Queue empty.")

    text = ""
    for i, song in enumerate(q[:10], start=1):
        text += f"**{i}.** {song[1]}\n"

    embed = discord.Embed(
        title="🎵 Music Queue",
        description=text,
        color=0x8A2BE2
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="stop", description="Stop music and disconnect")
async def stop(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    queues[guild_id] = []

    voice = interaction.guild.voice_client

    if voice:
        voice.stop()
        await voice.disconnect()

    await interaction.response.send_message("🛑 Music stopped & disconnected.")


bot.run(TOKEN)
