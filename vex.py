# vex.py
import os
import logging
import random
import re
from collections import deque

import discord
from discord import app_commands

from config.settings import DISCORD_TOKEN, GUILD_ID, LOG_LEVEL, PROMPT_PATH, REPLY_MODE

# ---------- Logging ----------
logging.basicConfig(level=getattr(logging, LOG_LEVEL.upper(), logging.INFO))
log = logging.getLogger("dead-guy")

# ---------- Prompt loading ----------
def load_prompt(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        log.error("Failed to load system prompt from %s: %s", path, e)
        return "SYSTEM PROMPT NOT FOUND"

SYSTEM_PROMPT = load_prompt(PROMPT_PATH)

# ---------- Visuals ----------
DEAD_GUY_COLOR = 0xA50808

# ---------- Discord client ----------
# For mention-reply mode, MESSAGE CONTENT intent is required.
intents = discord.Intents.default()
if REPLY_MODE.lower() == "mention":
    intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

chat_history = deque(maxlen=50)

# ---------- Dead Guy reply logic ----------
BRACKETED = re.compile(r"\[.*?\]")
OOC = re.compile(r"^\s*OOC", re.IGNORECASE)

# A small bank of corpse-appropriate fragments; all ≤10 words.
DEAD_FRAGMENTS = [
    "continues rotting.",
    "remains dead. no competition.",
    "developing character. and mold.",
    "decomposing in silence.",
    "not hungry. simply deceased.",
    "unmoved. unmoving.",
    "dead since 1759. still punctual.",
    "breathless, by design.",
    "peacefully inert.",
    "stone-still. remarkably consistent.",
]

def is_ignored_content(message_content: str) -> bool:
    if BRACKETED.search(message_content):
        return True
    if OOC.search(message_content):
        return True
    return False

def enforce_dead_guy_rules(text: str) -> str:
    # One short sentence or fragment, ≤10 words
    words = text.strip().split()
    if len(words) > 10:
        words = words[:10]
    out = " ".join(words)
    return out if out else "peacefully inert."

def generate_dead_guy_reply(user_text: str) -> str:
    # Dead Guy never initiates; this function is only called in response.
    # Ignore directives / OOC by returning a neutral dead fragment.
    if is_ignored_content(user_text):
        return enforce_dead_guy_rules("peacefully inert.")

    lowered = user_text.lower()

    if any(k in lowered for k in ["hello", "hi", "hey"]):
        return enforce_dead_guy_rules("dead. not social.")

    if any(k in lowered for k in ["hungry", "food", "sandwich"]):
        return enforce_dead_guy_rules("decomposing in silence, not hungry.")

    if "help" in lowered:
        return enforce_dead_guy_rules("beyond assistance. thoroughly dead.")

    if "who" in lowered:
        return enforce_dead_guy_rules("dead guy. accurate and final.")

    # Default: random dead fragment
    return enforce_dead_guy_rules(random.choice(DEAD_FRAGMENTS))

# ---------- Lifecycle ----------
@client.event
async def on_ready():
    guild_obj = discord.Object(id=GUILD_ID)
    await tree.sync(guild=guild_obj)
    log.info("Dead Guy ready. Synced slash commands to guild %s. Mode=%s", GUILD_ID, REPLY_MODE)

# ---------- Slash Commands (guild-scoped) ----------
@tree.command(name="ping", description="Health check")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong", ephemeral=True)

@tree.command(name="about", description="What is Dead Guy?")
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
    reply = generate_dead_guy_reply(message or "")
    await interaction.response.send_message(reply, ephemeral=False)

def is_admin():
    def predicate(interaction: discord.Interaction):
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)

@tree.command(name="reload_prompt", description="Reload system prompt from disk")
@is_admin()
async def reload_prompt(interaction: discord.Interaction):
    global SYSTEM_PROMPT
    SYSTEM_PROMPT = load_prompt(PROMPT_PATH)
    await interaction.response.send_message("Prompt reloaded.", ephemeral=True)

# ---------- Optional mention reply mode ----------
@client.event
async def on_message(message: discord.Message):
    # Only in the configured guild, ignore self
    if message.guild is None or message.guild.id != GUILD_ID:
        return
    if message.author == client.user:
        return
    if REPLY_MODE.lower() != "mention":
        return
    # Respond only if bot is mentioned
    if client.user in message.mentions:
        reply = generate_dead_guy_reply(message.content)
        await message.channel.send(reply)

# ---------- Entrypoint ----------
if __name__ == "__main__":
    if not DISCORD_TOKEN or not GUILD_ID:
        raise RuntimeError("Missing DISCORD_TOKEN or GUILD_ID")
    client.run(DISCORD_TOKEN)
