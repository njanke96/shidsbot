"""
Music commands

Taken from discord.py example "basic_voice"
"""

import asyncio

import discord
import youtube_dl

from discord.ext import commands, tasks

from shidsbot.bot_logging import log_info

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ""


ytdl_format_options = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    "options": "-vn",
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get("title")
        self.url = data.get("url")

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream)
        )

        if "entries" in data:
            # take first item from a playlist
            data = data["entries"][0]

        filename = data["url"] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.disconnect_idle_voice_clients.start()

    @commands.command(name="play")
    async def play(
        self,
        ctx: commands.Context,
        *,
        url: str = commands.parameter(
            description="The URL to play music from (anything supported by youtube-dl.org)"
        ),
    ):
        """
        Plays music from a URL

        Example: !play https://www.youtube.com/watch?v=cscuCIzItZQ
        """

        def _after(err):
            if err:
                ctx.send(f"Could not play, reason: {err}")

        async with ctx.typing():
            try:
                player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            except youtube_dl.utils.DownloadError:
                await ctx.send("I can't play that. youtube-dl doesn't like that URL.")
                await self.disconnect_voice_client(ctx)
                return

            # noinspection PyUnresolvedReferences
            ctx.voice_client.play(player, after=_after)

        await ctx.send(f"Now playing: {player.title}")
        log_info(f"{ctx.author.name} is now playing: {player.title}")

    @commands.command()
    async def stop(self, ctx: commands.Context):
        """Stops and disconnects the bot from voice"""

        await self.disconnect_voice_client(ctx)
        await ctx.send("Stopped playing.")

    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

    @staticmethod
    async def disconnect_voice_client(ctx: commands.Context):
        await ctx.voice_client.disconnect(force=True)

    @tasks.loop(seconds=30)
    async def disconnect_idle_voice_clients(self):
        for client in self.bot.voice_clients:
            client: discord.VoiceClient

            if not client.is_playing():
                log_info("Disconnecting an idle voice client...")
                await client.disconnect()

    @disconnect_idle_voice_clients.before_loop
    async def before_disconnect_idle_voice_clients(self):
        await self.bot.wait_until_ready()
