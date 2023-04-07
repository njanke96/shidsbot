from datetime import datetime
from os import environ

from discord.ext import commands, tasks
from httpx import AsyncClient
from shidsbot.bot_logging import log_error
from tabulate import tabulate

ACSPS_URL = environ.get("ACSPS_URL", "http://127.0.0.1:8000")

RECORD_CHECK_INTERVAL = 5
RACING_CHANNEL_ID = 1069836735439192114


def format_ms_time(millis: int) -> str:
    minutes, millis = divmod(millis, 60000)
    seconds, millis = divmod(millis, 1000)

    time_string = f"{minutes:02}:{seconds:02}.{millis:03}"
    return time_string


class Racing(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # http client factory
        self.http_client = lambda: AsyncClient(base_url=ACSPS_URL)

        # the most recent announced lap server record
        self.most_recent_record: datetime | None = None

        # start loop
        self.check_recent_records.start()

    @commands.command(name="laptimes")
    async def get_top_records(
        self,
        ctx: commands.Context,
    ):
        """
        Get top10 lap records link
        """
        async with ctx.typing():
            await ctx.send("http://montreal.codejank.ca:8000/records")
                
    @get_top_records.error
    async def laptimes_command_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("You are missing an argument, check !help laptimes")

    @tasks.loop(seconds=RECORD_CHECK_INTERVAL)
    async def check_recent_records(self):
        async with self.http_client() as client:
            result = await client.get("/records/server")

            if result.status_code != 200:
                log_error(
                    f"Got status {result.status_code} when requesting server records."
                )
                return

            str_to_datetime = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))

            result_json = result.json()
            timestamp = str_to_datetime(result_json["latest_timestamp"])

            if self.most_recent_record is None:
                self.most_recent_record = timestamp
            elif self.most_recent_record < timestamp:
                records = result_json["records"]
                new_records = [
                    record
                    for record in records
                    if str_to_datetime(record["timestamp"]) > self.most_recent_record
                ]
                self.most_recent_record = timestamp

                racing_channel = self.bot.get_channel(RACING_CHANNEL_ID)
                if racing_channel is None:
                    log_error(f"Channel id {RACING_CHANNEL_ID} not found.")
                    return

                for record in new_records:
                    await racing_channel.send(
                        f"\n**New Server Record**\n"
                        f"**{record['driver_name']}** set a server record on "
                        f"**{record['track_name']}/{record['track_config']}** for the class/car **{record['perf_class']}** "
                        f"with a time of **{format_ms_time(record['lap_time_ms'])}** !"
                    )
