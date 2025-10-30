# vex.py
# Dead Guy — Discord bot (LLM-powered via OpenRouter)
# - Single-guild slash commands (/dead, /about, /ping, /reload_prompt)
# - Optional mention-reply mode if REPLY_MODE=mention and Message Content Intent is enabled
# - Strict output guardrails: one line, <=10 words, morbid deadpan
#
# Environment variables (Render → Environment):
#   DISCORD_TOKEN=...                (required)
#   GUILD_ID=1305231447661219851     (required)
#   LOG_LEVEL=INFO                   (optional; default INFO)
#   PROMPT_PATH=config/prompt.md     (optional; default as shown)
#   REPLY_MODE=slash                 (or "mention" if using mention reply mode)
#   OPENROUTER_API_KEY=...           (required)
#   OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct  (example; set your preferred)
#   OPENROUTER_TEMPERATURE=0.7       (optional)
#   OPENROUTER_MAX_TOKENS=30         (optional; we clamp to <=10 words anyway)
#   OPENROUTER_BASE_URL=https://openrouter.ai/api/v1 (optional; default)
#   OPENROUTER_REFERER=https://your.site (optional; recommended by OpenRouter)
#   OPENROUTER_TITLE=Dead Guy (optional; recommended by OpenRouter)

import os
import re
import logging
import asyncio
from typing import Optional

import discord
from discord import app_commands
import aiohttp

# -------------------- Settings --------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
PROMPT_PATH = os.getenv("PROMPT_PATH", "config/prompt.md")
REPLY_MODE = os.getenv("REPLY_MODE", "slash").lower()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct")
OPENROUTER_TEMPERATURE = float(os.getenv("OPENROUTER_TEMPERATURE", "0.7"))
OPENROUTER_MAX_TOKENS = int(os.getenv("OPENROUTER_MAX_TOKENS", "30"))
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_REFERER = os.getenv("OPENROUTER_REFERER", "")
OPENROUTER_TITLE = os.getenv("OPENROUTER_TITLE", "Dead Guy")

# -------------------- Logging ---------------------
logging.basicConfig(level=getattr(logging, LOG_LEVEL.upper(), logging.INFO))
log = logging.getLogger("dead-guy")

# -------------------- Prompt Loading --------------
def load_prompt(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except Exception as e:
        log.error("Failed to load system prompt from %s: %s", path, e)
        raw = "You are Dead Guy. Reply as a morbidly dead corpse. One short line. <= 10 words."
    # Sanitize SillyTavern-style macros for this deployment
    sanitized = raw.replace("{{char}}", "Dead Guy").replace("{{user}}", "the user")
    return sanitized

SYSTEM_PROMPT = load_prompt(PROMPT_PATH)

# -------------------- Discord Client --------------
DEAD_GUY_COLOR = 0xA50808

intents = discord.Intents.default()
if REPLY_MODE == "mention":
    intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# -------------------- Guardrails ------------------
BRACKETED = re.compile(r"\[.*?\]")
OOC = re.compile(r"^\s*OOC", re.IGNORECASE)

def is_ignored_content(message_content: str) -> bool:
    # Ignore bracketed directives and OOC messages
    if BRACKETED.search(message_content or ""):
        return True
    if OOC.search(message_content or ""):
        return True
    return False

def clamp_dead_guy(text: str) -> str:
    """
    Enforce Dead Guy hard rules on any model output:
      - single short sentence/fragment
      - <= 10 words
      - deadpan; strip extraneous punctuation/emojis
    """
    if not text:
        return "peacefully inert."
    # Keep basic punctuation for tone, but prevent run-ons
    cleaned = re.sub(r"[^\w\s\.\-,'/]", " ", text, flags=re.UNICODE).strip().lower()
    # Use only the first line/sentence fragment
    cleaned = cleaned.split("\n", 1)[0].split("  ", 1)[0]
    words = cleaned.split()
    if len(words) > 10:
        words = words[:10]
    out = " ".join(words).strip()
    return out if out else "peacefully inert."

# -------------------- OpenRouter LLM --------------
async def openrouter_chat(system_prompt: str, user_text: str) -> Optional[str]:
    """
    Calls OpenRouter's Chat Completions API with an OpenAI-compatible payload.
    Returns raw text (not yet clamped) or None on failure.
    """
    if not OPENROUTER_API_KEY:
        log.error("OPENROUTER_API_KEY is not set.")
        return None

    url = f"{OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    # Optional OpenRouter best-practice headers
    if OPENROUTER_REFERER:
        headers["HTTP-Referer"] = OPENROUTER_REFERER
    if OPENROUTER_TITLE:
        headers["X-Title"] = OPENROUTER_TITLE

    payload = {
        "model": OPENROUTER_MODEL,
        "temperature": OPENROUTER_TEMPERATURE,
        "max_tokens": OPENROUTER_MAX_TOKENS,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
    }

    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    log.error("OpenRouter error %s: %s", resp.status, body[:500])
                    return None
                data = await resp.json()
    except Exception as e:
        log.error("OpenRouter request failed: %s", e)
        return None

    try:
        content = (data["choices"][0]["message"]["content"] or "").strip()
        return content
    except Exception:
        log.error("Unexpected OpenRouter response format: %s", str(data)[:500])
        return None

async def generate_dead_guy_reply(user_text: str) -> str:
    if is_ignored_content(user_text):
        return "peacefully inert."
    raw = await openrouter_chat(SYSTEM_PROMPT, user_text)
    return clamp_dead_guy(raw or "")

# -------------------- Discord Events/Commands ----
@client.event
async def on_ready():
    guild_obj = discord.Object(id=GUILD_ID)
    await tree.sync(guild=guild_obj)
    log.info("Dead Guy ready. Synced slash commands to guild %s. Mode=%s", GUILD_ID, REPLY_MODE)

@tree.command(name="ping", description="Health check")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong", ephemeral=True)

@tree.command(name="about", description="Show Dead Guy's system prompt (truncated)")
async def about(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Dead Guy — Ravenwood",
        description=SYSTEM_PROMPT[:2048],
        color=DEAD_GUY_COLOR,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="dead", description="Ask Dead Guy something")
@app_commands.describe(message="Your message to Dead Guy")
async def dead(interaction: discord.Interaction, message: str):
    reply = await generate_dead_guy_reply(message or "")
    await interaction.response.send_message(reply, ephemeral=False)

def is_admin():
    def predicate(interaction: discord.Interaction):
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)

@tree.command(name="reload_prompt", description="Reload the system prompt from disk")
@is_admin()
async def reload_prompt(interaction: discord.Interaction):
    global SYSTEM_PROMPT
    SYSTEM_PROMPT = load_prompt(PROMPT_PATH)
    await interaction.response.send_message("Prompt reloaded.", ephemeral=True)

# Optional mention-reply mode
@client.event
async def on_message(message: discord.Message):
    if REPLY_MODE != "mention":
        return
    if message.guild is None or message.guild.id != GUILD_ID:
        return
    if message.author == client.user:
        return
    if client.user not in message.mentions:
        return
    reply = await generate_dead_guy_reply(message.content or "")
    await message.channel.send(reply)

# -------------------- Entrypoint -----------------
def _validate_env():
    if not DISCORD_TOKEN:
        raise RuntimeError("Missing DISCORD_TOKEN")
    if not GUILD_ID:
        raise RuntimeError("Missing or invalid GUILD_ID")
    if not OPENROUTER_API_KEY:
        raise RuntimeError("Missing OPENROUTER_API_KEY")
    if not OPENROUTER_MODEL:
        raise RuntimeError("Missing OPENROUTER_MODEL")

if __name__ == "__main__":
    _validate_env()
    try:
        client.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        pass
