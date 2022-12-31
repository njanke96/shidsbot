"""
Music commands

Excerpts from discord.py example "basic_voice"
"""

import asyncio
from typing import Optional, Tuple, List, Union

import discord
import youtube_dl

from discord.ext import commands, tasks

from shidsbot.bot_logging import log_info, log_error

TextOrVoiceChannel = Union[discord.TextChannel, discord.VoiceChannel]

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

        # messages to be sent in the event loop (populated by _after in the play command)
        self.message_queue: List[Tuple[TextOrVoiceChannel, str]] = []

        # music to start playing next tick (for !loop)
        self.play_next_tick: Optional[Tuple[discord.VoiceClient, str]] = None

        # start loops
        self.tick.start()
        self.disconnect_idle_voice_clients.start()

    @commands.command(name="play")
    async def play(
        self,
        ctx: commands.Context,
        *,
        url: str = commands.parameter(
            description="The URL or search to play music from"
        ),
        loop: bool = False
    ):
        """
        Plays music from a URL

        Example: !play https://www.youtube.com/watch?v=cscuCIzItZQ
        """

        def _after(err):
            if err:
                self.message_queue.append(
                    (ctx.channel, f"Could not play, reason: {err}")
                )

            voice_client_after: Optional[discord.VoiceClient] = ctx.voice_client
            if not voice_client_after:
                return

            if loop:
                self.play_next_tick = (voice_client_after, url)

        async with ctx.typing():
            try:
                player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            except youtube_dl.utils.DownloadError:
                await ctx.send("I can't play that. youtube-dl doesn't like that URL.")
                await self.disconnect_voice_client(ctx)
                return

            voice_client: Optional[discord.VoiceClient] = ctx.voice_client
            if voice_client is None:
                if not hasattr(ctx.author, "voice"):
                    await ctx.send("I can't play music in here.")
                    return

                if ctx.author.voice is not None:
                    voice_client = await ctx.author.voice.channel.connect()
                else:
                    await ctx.send("You are not connected to a voice channel.")
                    return

            elif voice_client.is_playing():
                voice_client.stop()

            voice_client.play(player, after=_after)

        await ctx.send(f"Now playing: {player.title}" + (". Will loop until !stop command is used." if loop else ""))
        log_info(f"{ctx.author.name} is now playing: {player.title}")

    @commands.command()
    async def loop(
        self,
        ctx: commands.Context,
        *,
        url: str = commands.parameter(
            description="The URL or search to play music from"
        ),
    ):
        """
        Plays and loops music from a URL

        Example: !loop https://www.youtube.com/watch?v=cscuCIzItZQ
        """
        await self.play(ctx, url=url, loop=True)

    @commands.command()
    async def stop(self, ctx: commands.Context):
        """Stops and disconnects the bot from voice"""

        await self.disconnect_voice_client(ctx)
        await ctx.send("Stopped playing.")

    @staticmethod
    async def disconnect_voice_client(ctx: commands.Context):
        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect(force=True)

    @tasks.loop(seconds=1)
    async def tick(self):
        # send messages in queue
        for message in self.message_queue:
            await message[0].send(message[1])

        self.message_queue = []

        # loop music
        if self.play_next_tick is None:
            return

        voice_client = self.play_next_tick[0]
        url = self.play_next_tick[1]

        # clear flag
        self.play_next_tick = None

        def _after(err):
            if err:
                log_error(f"Could not loop song due to an error: {err}")
                return

            # set the flag
            self.play_next_tick = (voice_client, url)

        # re-create the YTDLSource
        player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)

        if voice_client.is_connected():
            if voice_client.is_playing():
                voice_client.stop()

            voice_client.play(player, after=_after)

    @tasks.loop(seconds=30)
    async def disconnect_idle_voice_clients(self):
        for client in self.bot.voice_clients:
            client: discord.VoiceClient

            if not client.is_playing():
                log_info("Disconnecting an idle voice client...")
                await client.disconnect()

    @disconnect_idle_voice_clients.before_loop
    async def before_loops(self):
        await self.bot.wait_until_ready()
