import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from cogs.music import Music
from bot_logging import log_info

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=("!", "s!"),
    description="Shids Bot",
    intents=intents,
)


@bot.event
async def on_ready():
    log_info(f"Logged in as {bot.user} (ID: {bot.user.id})")


async def main():
    async with bot:
        await bot.add_cog(Music(bot))
        await bot.start(os.environ["DISCORD_TOKEN"])


if __name__ == "__main__":
    discord.utils.setup_logging()
    load_dotenv()
    asyncio.run(main())
