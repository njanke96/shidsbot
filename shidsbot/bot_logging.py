import logging

logger = logging.getLogger("discord.shidsbot")
logger.setLevel(logging.INFO)


def log_info(msg: str):
    logger.log(logging.INFO, msg)
