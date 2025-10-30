import os

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DISCORD_APP_ID = os.getenv("DISCORD_APP_ID", "")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))           # single target server
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
PROMPT_PATH = os.getenv("PROMPT_PATH", "config/prompt.md")
REPLY_MODE = os.getenv("REPLY_MODE", "slash")        # "slash" or "mention"
