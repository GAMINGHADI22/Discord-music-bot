import os
import asyncio
import discord
from discord.ext import commands
import yt_dlp

TOKEN = os.getenv("DISCORD_TOKEN") or "YOUR_BOT_TOKEN_HERE"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

queues = {}

YDL_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "extract_flat": "in_playlist",
    "noplaylist": False,
}

FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn"
}

async def get_audio(url):
    loop = asyncio.get_event_loop()

    def extract():
        with yt_dlp.YoutubeDL({"format": "bestaudio/best", "quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return info["url"], info.get("title", "Unknown Title")

    return await loop.run_in_executor(None, extract)

async def play_next(ctx):
    guild_id = ctx.guild.id

    if guild_id not in queues or len(queues[guild_id]) == 0:
        await ctx.send("✅ Queue sesh hoye geche.")
        return

    url, title = queues[guild_id].pop(0)
    audio_url, real_title = await get_audio(url)

    source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTS)

    ctx.voice_client.play(
        source,
        after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
    )

    await ctx.send(f"🎶 Now Playing: **{real_title}**")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def join(ctx):
    if not ctx.author.voice:
        return await ctx.send("❌ Age voice channel e join koro first.")

    channel = ctx.author.voice.channel

    if ctx.voice_client:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect()

    await ctx.send("✅ Voice channel e join korlam.")

@bot.command()
async def play(ctx, *, url):
    if not ctx.author.voice:
        return await ctx.send("❌ First voice channel e join koro.")

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    guild_id = ctx.guild.id
    queues.setdefault(guild_id, [])

    await ctx.send("🔎 Playlist/song load hocche...")

    loop = asyncio.get_event_loop()

    def extract_playlist():
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            return ydl.extract_info(url, download=False)

    info = await loop.run_in_executor(None, extract_playlist)

    if "entries" in info:
        count = 0
        for entry in info["entries"]:
            if entry:
                video_url = entry.get("url")
                if not video_url.startswith("http"):
                    video_url = "https://www.youtube.com/watch?v=" + video_url
                queues[guild_id].append((video_url, entry.get("title", "Unknown")))
                count += 1

        await ctx.send(f"✅ Playlist theke **{count}** ta song queue te add holo.")
    else:
        queues[guild_id].append((url, info.get("title", "Unknown")))
        await ctx.send("✅ Song queue te add holo.")

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭ Skipped.")
    else:
        await ctx.send("❌ Kichu play hocche na.")

@bot.command()
async def stop(ctx):
    guild_id = ctx.guild.id
    queues[guild_id] = []

    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()

    await ctx.send("🛑 Music stopped & bot disconnected.")

@bot.command()
async def queue(ctx):
    guild_id = ctx.guild.id
    q = queues.get(guild_id, [])

    if not q:
        return await ctx.send("📭 Queue empty.")

    msg = "🎵 **Music Queue:**\n"
    for i, item in enumerate(q[:10], start=1):
        msg += f"{i}. {item[1]}\n"

    await ctx.send(msg)

bot.run(TOKEN)
