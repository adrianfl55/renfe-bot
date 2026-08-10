"""Module to manage the configuration of the bot."""

import configparser
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CONFIG_FILE = "config.ini"


def get_bot_token() -> str:
    """Read environment variables or config file to obtain the bot's secret token.

    :return: The bot instance secret token
    :rtype: str
    """
    env_token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_SECRET_TOKEN")
    if env_token and env_token.strip():
        return env_token.strip()

    config = configparser.ConfigParser()
    if Path(CONFIG_FILE).exists():
        config.read(CONFIG_FILE)
        if "Telegram" in config and "secret_token" in config["Telegram"]:
            token = config["Telegram"]["secret_token"].strip()
            if token:
                return token

    raise RuntimeError(
        "No se encontró el TELEGRAM_TOKEN en las variables de entorno (.env o config.ini). "
        "Por favor, asegúrate de configurar TELEGRAM_TOKEN=tu_token en tu archivo .env o en Portainer."
    )
