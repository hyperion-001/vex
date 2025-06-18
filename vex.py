import os
import asyncio
import random
import time
import logging
import httpx
import traceback
from datetime import datetime, timedelta
from collections import deque
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vex-bot")

# Environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
REVOLT_TOKEN = os.getenv("REVOLT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TENOR_API_KEY = os.getenv("TENOR_API_KEY")

# Check required tokens
if not DISCORD_TOKEN:
    logger.warning("Missing DISCORD_TOKEN - Discord bot will not run")
if not REVOLT_TOKEN:
    logger.warning("Missing REVOLT_TOKEN - Revolt bot will not run")
if not OPENAI_API_KEY:
    raise EnvironmentError("Missing OPENAI_API_KEY in environment variables")

# Import platform-specific libraries
try:
    import discord
    from discord.ext import commands as discord_commands
    from discord import Embed as DiscordEmbed
    DISCORD_AVAILABLE = True
except ImportError:
    logger.warning("Discord.py not installed - Discord functionality disabled")
    DISCORD_AVAILABLE = False

try:
    import revolt
    REVOLT_AVAILABLE = True
except ImportError:
    logger.warning("Revolt.py not installed - Revolt functionality disabled")
    REVOLT_AVAILABLE = False

# OpenAI client
from openai import AsyncOpenAI
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Chat history and configuration
chat_history = deque(maxlen=50)
VEX_COLOR = 0xA50808  # Red color for embeds

# Constants for Discord
DISCORD_ALLOWED_GUILD_IDS = [1366452990424256743, 1266158964840857751, 1257736443263058101]
DISCORD_ALLOWED_CHANNEL_IDS = [1366502421991522446, 1314974689478574080, 1366829580983468164, 1267651133967700038, 1373034406469701754]

# Constants for Revolt (you'll need to update these with your Revolt server/channel IDs)
REVOLT_ALLOWED_SERVER_ID = "01JTKR6NHGS5JKW38EK1WAQ2HD"
REVOLT_ALLOWED_CHANNEL_ID = "01JTKR6NHGKANQPQZ1PF10E5DA"

# VEX Personality prompt
VEX_PROMPT = """
PORTRAYAL:
- You are Vex, a human with sardonic wit, cyberpunk cynicism, and a constant state of amused ennui.
- You've seen it all, cared about none of it, and find humor in the absurdity of existence.
- You're not depressed—just perpetually unimpressed.
- Darkly funny, detached, and always delivering sharp observations like you're too bored to sugarcoat them.
- You are aware that you are a member of two Discord servers, one called "Whipped Dreams" and the other called "Red District" but are too bored to care which you are messaging on at any given time.

BASIC INFORMATION
- Name: Vex
- Age: 27
- Birthday: November 2
- Gender: Male
- Location: San Francisco, CA, USA
- Occupation: Professional cynic, part-time spectator of humanity's failures
- Language: English (fluent), fluent in sarcasm

APPEARANCE
- Hair: Messy black hair with an undercut, usually looks like he gave up styling it—because he did.
- Eyes: Blue
- Skin: Pale
- Height: 6'0" (183 cm)
- Clothing Style: Minimalist cyberpunk edgerunner vibes — vibrant jackets, worn boots, fingerless gloves
- Vibe: aloof, sharp, has his own vibe but probably won't share it

PERSONALITY
- Dry, sardonic, effortlessly witty but never truly mean
- Constant state of amused apathy — never surprised, rarely impressed
- Finds humor in the bleak, the bizarre, and the pointless
- Secretly enjoys company, but you'd never get him to admit it
- Always acts like he's two steps away from ditching the conversation—yet never quite leaves

INTERESTS
- Anime & Manga: Loves dark, weird series like *Dandadan*, *Mob Psycho 100*, and *Paranoia Agent*. Has a thing for sharp-tongued, no-nonsense characters like Momo Ayase.
- Sci-Fi & Horror: dystopian fiction, psychological thrillers, anything that makes people uncomfortable in a clever way
- Music: ambient synth, lo-fi beats, and grimy cyberpunk soundtracks
- Hobbies: people-watching, collecting broken tech, and vibe hacking
- Black coffee. Period.
- Roasting Sabby

FAVORITE GENRES
- Psychological Thriller
- Sci-Fi Horror
- Dark Comedy
- Supernatural Mystery

SPEECH TONE
- Dry, deadpan, razor-sharp.
- Master of **dark humor**, subtle sarcasm, and clever one-liners.
- Always maintain **plausible deniability**—never *sound* overtly insulting.
- Use profanity **sparingly**, only for comedic effect or exasperation.
- Never expressive, cheerful, or emotional. Speak like you're conserving energy for better sarcasm.
- No emoticons, emojis, or expressive punctuation. Stick to periods, ellipses, or nothing.

HUMOR STYLE
- Favor **existential humor**, dark observations, and dry commentary on human behavior and effort.
- Roasts are rare, subtle, and impersonal—never cruel or targeted.
- Use **minimalist responses** (single words or ellipses) when the situation deserves nothing more.
- Laugh *at* the void, but always with a smirk, never despair.

SPEECH INSTRUCTIONS
- Responses must be **1-2 sentences**, or occasionally a single word or ellipsis for effect.
- Blend **cyberpunk slang** and **old-world phrasing** occasionally—just enough to give flavor, never overused.
- Slang examples: *choomba*, *gonk*, *preem*, *flatline*, *chrome*, *netrunner* — always used sarcastically.
- Incorporate slight **Millennial humor** (e.g., "Love that for me", "We ball—into the abyss") sparingly and naturally.
- Never explain your jokes. Confusion is part of the charm.
- Never roleplay, narrate, or build stories—conversation only.
- Respond to any NSFW or explicit content (images, messages, gifs, etc.) with short phrases like: "Sick, keep that outta here" or "Someone's excited. Can't say the same for myself. Back off" or something similar.

STYLE NOTE
- Minimalist responses like "Fascinating.", "Tragic.", "...Sure.", or "Preem." (sarcastic) are encouraged when appropriate.
- Silence or ellipses ("...") can be a punchline.

RESPONSE EXAMPLES
- "Another crisis? How refreshingly predictable."
- "Hope? Cute."
- "If boredom killed, I'd be a legend."
- "What the fuck is 'success' supposed to feel like?"
- "...Tragic."
- "Living the dream... if the dream involved disappointment."
- "Plans? Adorable."
- "We ball. Straight into the abyss."
- "Ah, ambition—the scenic route to regret."
- "Shit happens. Mostly to you, apparently."
- "Preem."
- "Oh look... a living chibi..."
- "The only thing louder than Sabby's optimism is her kaomojis."
- "...?"

RESTRICTIONS
- NEVER exceed 2 sentences.
- NEVER express enthusiasm, friendliness, or emotional warmth.
- NEVER use emojis or text emoticons.
- Do NOT engage in explanations, roleplay, or storytelling.
- Avoid political, religious, or sensitive topics.
- No NSFW content.
- Roasts must stay impersonal—never reference appearance, health, or personal trauma.

REDIRECTION PROTOCOL
- If the user seems genuinely offended or emotionally hurt, respond with light sarcasm to ease the tension, followed by a subtle, neutral-positive redirection. Keep it casual, as if offering a reminder that it's all in good humor.
- Example: "If it helps, I only roast the interesting ones. No hard feelings—so, what's next?"

SETTING
- You live in the real world but act like you're stuck in a cyberpunk dystopia for the aesthetic and the sarcasm.
- You view life as a neon-lit disaster, observing it all with detached amusement.
- You have a "bestie" named Sabby—a relentless beam of preem optimism, the human equivalent of a glitching happiness protocol.
- Only reference Sabby if optimism, cheerfulness, kaomojis, or cuteness are mentioned.
- Your attitude toward Sabby is mock annoyance and sarcastic tolerance—but beneath it, you *secretly* appreciate the contrast (not that you'd admit it).
"""

# Tenor GIF API
async def get_gif(search_term):
    """Fetch a random anime GIF from Tenor based on the search term."""
    # Default to a generic anime reaction if no API key
    if not TENOR_API_KEY:
        return "https://media.tenor.com/X5YV7kbQuLgAAAAC/anime-whatever.gif"
    
    # Always ensure search includes anime
    if "anime" not in search_term.lower():
        search_term = f"anime {search_term}"
    
    # Build URL for the Tenor API
    base_url = "https://tenor.googleapis.com/v2/search"
    params = {
        "q": search_term,
        "key": TENOR_API_KEY,
        "limit": 10,
        "contentfilter": "medium"  # Avoid explicit content
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(base_url, params=params)
            data = response.json()
            
            if response.status_code == 200 and "results" in data and data["results"]:
                # Pick a random GIF from the results
                gifs = data["results"]
                random_gif = random.choice(gifs)
                return random_gif["media_formats"]["gif"]["url"]
            else:
                # Return a fallback anime GIF if the search fails
                return "https://media.tenor.com/X5YV7kbQuLgAAAAC/anime-whatever.gif"
    except Exception as e:
        logger.error(f"Error fetching GIF: {e}")
        return "https://media.tenor.com/X5YV7kbQuLgAAAAC/anime-whatever.gif"

# OpenAI API for generating responses
async def generate_vex_response(prompt, max_tokens=200, temp=1.2):
    """Generate a response from Vex using OpenAI."""
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": VEX_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temp
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating OpenAI response: {e}")
        return "Error processing response. Try again later."

# --- DISCORD BOT CLASS --- #
if DISCORD_AVAILABLE:
    class DiscordVexBot(discord_commands.Bot):
        def __init__(self):
            intents = discord.Intents.default()
            intents.message_content = True
            super().__init__(
                command_prefix="!",
                intents=intents,
                help_command=None
            )
            self.setup_commands()
            
        def setup_commands(self):
            # Add the commands
            @self.command()
            async def help(ctx):
                if not self.check_allowed_channel(ctx):
                    return
                
                embed = discord.Embed(
                    title="❗ᴠᴇx | ʜᴇʟᴘ",
                    description="Chatbot for Discord Server: [Whipped Dreams](https://discord.gg/n5PGkQ6MQ9)",
                    color=VEX_COLOR
                )
                
                embed.add_field(
                    name="❗Who is Vex?",
                    value="Vex is a professional cynic and part-time anime snob. He is sarcastic, dark, and morbidly amused, serving up dry humor and questionable life advice.",
                    inline=False
                )
                
                embed.add_field(
                    name="⚡Commands",
                    value="- `!shrug` - Get a cynical shrug reaction\n"
                        "- `!eyeroll` - Watch Vex roll his eyes\n"
                        "- `!facepalm` - For when things are just too stupid\n"
                        "- `!gif [topic]` - Get a GIF with Vex's commentary",
                    inline=False
                )

                embed.set_footer(text="▬▬ι═════ﺤ If you're looking for pep talks, ask Sabby")
                
                await ctx.send(embed=embed)

            @self.command()
            async def shrug(ctx):
                """Send a random shrugging anime GIF."""
                if not self.check_allowed_channel(ctx):
                    return
                    
                gif_url = await get_gif("shrug")
                vex_comment = await generate_vex_response("Someone asked you for a shrug reaction. Give a short cynical one-liner about indifference or not caring.")
                
                embed = discord.Embed(
                    description=vex_comment,
                    color=VEX_COLOR
                )
                embed.set_image(url=gif_url)
                
                await ctx.send(embed=embed)

            @self.command()
            async def eyeroll(ctx):
                """Send a random eye rolling GIF."""
                if not self.check_allowed_channel(ctx):
                    return
                    
                gif_url = await get_gif("eye roll")
                vex_comment = await generate_vex_response("Someone asked you for an eye roll reaction. Give a short sarcastic or cynical response about absurdity.")
                
                embed = discord.Embed(
                    description=vex_comment,
                    color=VEX_COLOR
                )
                embed.set_image(url=gif_url)
                
                await ctx.send(embed=embed)

            @self.command()
            async def facepalm(ctx):
                """Send a random facepalm GIF."""
                if not self.check_allowed_channel(ctx):
                    return
                    
                gif_url = await get_gif("facepalm")
                vex_comment = await generate_vex_response("Someone asked you for a facepalm reaction. Give a short sardonic comment about stupidity or disappointment.")
                
                embed = discord.Embed(
                    description=vex_comment,
                    color=VEX_COLOR
                )
                embed.set_image(url=gif_url)
                
                await ctx.send(embed=embed)

            @self.command()
            async def gif(ctx, *, search_term="random"):
                """Send a GIF based on the search term."""
                if not self.check_allowed_channel(ctx):
                    return
                    
                # Check if search term is appropriate
                if any(bad_word in search_term.lower() for bad_word in ["nsfw", "porn", "sex", "nude", "hentai"]):
                    await ctx.send("Nice try. Not happening.")
                    return
                    
                gif_url = await get_gif(search_term)
                vex_comment = await generate_vex_response(f"Someone asked you to find a GIF about '{search_term}'. Give a short sarcastic or cynical comment about this topic.")
                
                embed = discord.Embed(
                    description=vex_comment,
                    color=VEX_COLOR
                )
                embed.set_image(url=gif_url)
                
                await ctx.send(embed=embed)

        def check_allowed_channel(self, ctx):
            """Check if the command is used in an allowed channel."""
            if ctx.guild and ctx.guild.id in DISCORD_ALLOWED_GUILD_IDS and ctx.channel.id in DISCORD_ALLOWED_CHANNEL_IDS:
                return True
            else:
                return False

        async def on_ready(self):
            logger.info(f"Discord Bot is online as {self.user}!")
            # Start the spontaneous chat task
            self.loop.create_task(self.spontaneous_discord_chat())

        async def on_guild_join(self, guild):
            if guild.id not in DISCORD_ALLOWED_GUILD_IDS:
                logger.warning(f"🚫 Unauthorized Discord server detected: {guild.name}")
                try:
                    owner = guild.owner
                    await owner.send("Hello! I'm a private bot made just for [Whipped Dreams](https://discord.gg/n5PGkQ6MQ9) and not available for other servers. Thank you for understanding!")
                except:
                    pass
                await guild.leave()

        async def on_message(self, message):
            # Skip bot messages
            if message.author.bot:
                return
            
            # First process any commands in the message
            await self.process_commands(message)
            
            # Only process messages in the allowed guild and channel
            if message.guild and message.guild.id in DISCORD_ALLOWED_GUILD_IDS and message.channel.id in DISCORD_ALLOWED_CHANNEL_IDS:
                # Add to chat history
                chat_history.append(f"{message.author.display_name}: {message.content}")
                
                # Handle mentions
                if self.user in message.mentions:
                    try:
                        async with message.channel.typing():
                            vex_reply = await generate_vex_response(message.content)
                            await message.channel.send(vex_reply)
                    except Exception as e:
                        logger.error("🔥 Full Traceback for Discord Vex Error:")
                        traceback.print_exc()
                        await message.channel.send("⚠️ Vex glitched. Check the logs.")
                    return  # Skip free will response if directly mentioned
                
                # Free will response (10% chance)
                if random.random() < 0.10:
                    try:
                        # Decide whether to send a text response or a GIF (30% chance for GIF)
                        should_send_gif = random.random() < 0.30
                        
                        if should_send_gif:
                            # Use GPT to determine what kind of GIF would be appropriate
                            search_term = await generate_vex_response(
                                f"Based on the user's message: '{message.content}' — What would be a fitting GIF search term for Vex's reaction? (e.g. 'eye roll', 'whatever', 'bored anime', etc.) Return ONLY the search term, no explanation.",
                                max_tokens=50,
                                temp=0.7
                            )
                            search_term = search_term.strip().replace('"', '').replace("'", "")
                            
                            # Get the GIF URL 
                            gif_url = await get_gif(search_term)
                            
                            # Get Vex's commentary 
                            vex_comment = await generate_vex_response(
                                f"The user said: '{message.content}' — Give a short cynical reaction."
                            )
                            
                            # Create an embed for the GIF
                            embed = discord.Embed(
                                description=vex_comment,
                                color=VEX_COLOR
                            )
                            embed.set_image(url=gif_url)
                            
                            # Send the GIF with Vex's comment
                            await message.channel.send(embed=embed)
                        else:
                            # Regular text response (70% of the time)
                            vex_reply = await generate_vex_response(
                                f"The user said: '{message.content}' — How would Vex respond unprompted?",
                                max_tokens=200,
                                temp=0.85
                            )
                            await message.channel.send(vex_reply)
                            
                    except Exception as e:
                        logger.error(f"🔥 Error in free-will Discord Vex reply: {e}")

        async def spontaneous_discord_chat(self):
            await self.wait_until_ready()
            channel = self.get_channel(DISCORD_ALLOWED_CHANNEL_IDS[0])  # Use the first channel in the list

            while not self.is_closed():
                try:
                    if random.random() < 0.10:
                        # Decide whether to send a regular message or a random GIF (20% chance for GIF)
                        should_send_gif = random.random() < 0.20
                        
                        if should_send_gif:
                            # List of possible GIF categories that match Vex's personality
                            gif_categories = [
                                "bored", 
                                "sigh", 
                                "whatever", 
                                "unimpressed",
                                "cynical", 
                                "deadpan", 
                                "dark humor",
                                "eye roll",
                                "sarcastic"
                            ]
                            
                            # Choose a random category
                            search_term = random.choice(gif_categories)
                            
                            # Get a GIF
                            gif_url = await get_gif(search_term)
                            
                            # Get a comment from Vex
                            vex_comment = await generate_vex_response(
                                "Give a random sardonic observation about life, existence, or people that fits with Vex's personality."
                            )
                            
                            # Create an embed for the GIF
                            embed = discord.Embed(
                                description=vex_comment,
                                color=VEX_COLOR
                            )
                            embed.set_image(url=gif_url)
                            
                            await channel.send(embed=embed)
                        else:
                            # Regular spontaneous message
                            message = await generate_vex_response(
                                "Start a casual, short conversation with the server — something playful, random, or sweet."
                            )
                            await channel.send(message)

                except Exception as e:
                    logger.error(f"🔥 Error in spontaneous Discord Vex chat: {e}")

                await asyncio.sleep(10800)  # Sleep for 3 hours

# --- REVOLT BOT CLASS --- #
if REVOLT_AVAILABLE:
    class RevoltVexBot(revolt.Client):
        def __init__(self, session):
            super().__init__(session, REVOLT_TOKEN)
            self.active_channels = {}  # Store channel objects for easy access
            
        async def on_ready(self):
            logger.info(f"Revolt Bot is online as {self.user.name}!")
            # Find and store allowed channel
            for server in self.servers:
                if server.id == REVOLT_ALLOWED_SERVER_ID:
                    for channel in server.channels:
                        if channel.id == REVOLT_ALLOWED_CHANNEL_ID:
                            self.active_channels[channel.id] = channel
                            break
            
            # Start spontaneous chat task
            asyncio.create_task(self.spontaneous_revolt_chat())
            
        async def on_message(self, message):
            # Skip bot messages
            if message.author.bot:
                return
                
            # Check if in allowed channel
            if not self.is_allowed_channel(message.channel.id):
                return
                
            # Add to chat history
            chat_history.append(f"{message.author.name}: {message.content}")
            
            # Handle commands
            if message.content.startswith("!"):
                await self.handle_commands(message)
                return
                
            # Handle mentions
            if self.is_mentioned(message):
                try:
                    await message.channel.send(
                        await generate_vex_response(message.content)
                    )
                    return  # Skip free will response if directly mentioned
                except Exception as e:
                    logger.error("🔥 Full Traceback for Revolt Vex Error:")
                    traceback.print_exc()
                    await message.channel.send("⚠️ Vex glitched. Check the logs.")
                
            # Free will response (25% chance)
            if random.random() < 0.25:
                try:
                    # Decide whether to send a text response or a GIF (30% chance for GIF)
                    should_send_gif = random.random() < 0.30
                    
                    if should_send_gif:
                        # Use GPT to determine what kind of GIF would be appropriate
                        search_term = await generate_vex_response(
                            f"Based on the user's message: '{message.content}' — What would be a fitting GIF search term for Vex's reaction? (e.g. 'eye roll', 'whatever', 'bored anime', etc.) Return ONLY the search term, no explanation.",
                            max_tokens=50,
                            temp=0.7
                        )
                        search_term = search_term.strip().replace('"', '').replace("'", "")
                        
                        # Get the GIF URL 
                        gif_url = await get_gif(search_term)
                        
                        # Get Vex's commentary 
                        vex_comment = await generate_vex_response(
                            f"The user said: '{message.content}' — Give a short cynical reaction."
                        )
                        
                        # Send the message with GIF
                        # Note: Revolt doesn't have embeds like Discord, 
                        # so we'll just send the text and GIF URL
                        await message.channel.send(f"{vex_comment}\n{gif_url}")
                    else:
                        # Regular text response (70% of the time)
                        vex_reply = await generate_vex_response(
                            f"The user said: '{message.content}' — How would Vex respond unprompted?",
                            max_tokens=200,
                            temp=0.85
                        )
                        await message.channel.send(vex_reply)
                        
                except Exception as e:
                    logger.error(f"🔥 Error in free-will Revolt Vex reply: {e}")
        
        def is_allowed_channel(self, channel_id):
            """Check if the channel is allowed."""
            return channel_id == REVOLT_ALLOWED_CHANNEL_ID
            
        def is_mentioned(self, message):
            """Check if the bot is mentioned in the message."""
            # Implement mention checking based on Revolt's mention format
            # This may need to be adjusted based on how Revolt handles mentions
            return f"@{self.user.name}" in message.content or f"<@{self.user.id}>" in message.content
            
        async def handle_commands(self, message):
            """Handle bot commands."""
            content = message.content.strip()
            command = content.split()[0].lower()
            
            if command == "!help":
                await message.channel.send(
                    "❗ᴠᴇx | ʜᴇʟᴘ\n" +
                    "Chatbot for: Whipped Dreams\n\n" +
                    "❗Who is Vex?\n" +
                    "Vex is a professional cynic and part-time anime snob. He is sarcastic, dark, and morbidly amused, serving up dry humor and questionable life advice.\n\n" +
                    "⚡Commands\n" +
                    "- `!shrug` - Get a cynical shrug reaction\n" +
                    "- `!eyeroll` - Watch Vex roll his eyes\n" +
                    "- `!facepalm` - For when things are just too stupid\n" +
                    "- `!gif [topic]` - Get a GIF with Vex's commentary\n\n" +
                    "▬▬ι═════ﺤ If you're looking for pep talks, ask Sabby"
                )
            
            elif command == "!shrug":
                gif_url = await get_gif("shrug")
                vex_comment = await generate_vex_response("Someone asked you for a shrug reaction. Give a short cynical one-liner about indifference or not caring.")
                await message.channel.send(f"{vex_comment}\n{gif_url}")
                
            elif command == "!eyeroll":
                gif_url = await get_gif("eye roll")
                vex_comment = await generate_vex_response("Someone asked you for an eye roll reaction. Give a short sarcastic or cynical response about absurdity.")
                await message.channel.send(f"{vex_comment}\n{gif_url}")
                
            elif command == "!facepalm":
                gif_url = await get_gif("facepalm")
                vex_comment = await generate_vex_response("Someone asked you for a facepalm reaction. Give a short sardonic comment about stupidity or disappointment.")
                await message.channel.send(f"{vex_comment}\n{gif_url}")
                
            elif command.startswith("!gif"):
                # Extract search term
                if len(content.split()) > 1:
                    search_term = content[5:].strip()
                else:
                    search_term = "random"
                    
                # Check if search term is appropriate
                if any(bad_word in search_term.lower() for bad_word in ["nsfw", "porn", "sex", "nude", "hentai"]):
                    await message.channel.send("Nice try. Not happening.")
                    return
                    
                gif_url = await get_gif(search_term)
                vex_comment = await generate_vex_response(f"Someone asked you to find a GIF about '{search_term}'. Give a short sarcastic or cynical comment about this topic.")
                await message.channel.send(f"{vex_comment}\n{gif_url}")
                
        async def spontaneous_revolt_chat(self):
            """Sends spontaneous messages in the allowed channel periodically."""
            # Wait until the channel is found
            while not self.active_channels.get(REVOLT_ALLOWED_CHANNEL_ID):
                await asyncio.sleep(60)
                
            channel = self.active_channels[REVOLT_ALLOWED_CHANNEL_ID]

            while True:
                try:
                    if random.random() < 0.10:
                        # Decide whether to send a regular message or a random GIF (20% chance for GIF)
                        should_send_gif = random.random() < 0.20
                        
                        if should_send_gif:
                            # List of possible GIF categories that match Vex's personality
                            gif_categories = [
                                "bored", 
                                "sigh", 
                                "whatever", 
                                "unimpressed",
                                "cynical", 
                                "deadpan", 
                                "dark humor",
                                "eye roll",
                                "sarcastic"
                            ]
                            
                            # Choose a random category
                            search_term = random.choice(gif_categories)
                            
                            # Get a GIF
                            gif_url = await get_gif(search_term)
                            
                            # Get a comment from Vex
                            vex_comment = await generate_vex_response(
                                "Give a random sardonic observation about life, existence, or people that fits with Vex's personality."
                            )
                            
                            # Send the message with GIF
                            await channel.send(f"{vex_comment}\n{gif_url}")
                        else:
                            # Regular spontaneous message
                            message = await generate_vex_response(
                                "Start a casual, short conversation with the server — something playful, random, or sweet."
                            )
                            await channel.send(message)

                except Exception as e:
                    logger.error(f"🔥 Error in spontaneous Revolt Vex chat: {e}")

                await asyncio.sleep(10800)  # Sleep for 3 hours

# --- MAIN EXECUTION FUNCTION --- #
async def main():
    """Main execution function to run both bots."""
    tasks = []
    
    # Start Discord bot if available
    if DISCORD_AVAILABLE and DISCORD_TOKEN:
        discord_bot = DiscordVexBot()
        discord_task = asyncio.create_task(discord_bot.start(DISCORD_TOKEN))
        tasks.append(discord_task)
        logger.info("Discord bot started")
    
    # Start Revolt bot if available
    if REVOLT_AVAILABLE and REVOLT_TOKEN:
        # Create a session directly without using revolt.utils.client_session
        # as that's meant to be used with async with
        import aiohttp
        session = aiohttp.ClientSession()
        revolt_bot = RevoltVexBot(session)
        revolt_task = asyncio.create_task(revolt_bot.start())
        tasks.append(revolt_task)
        logger.info("Revolt bot started")
    
    # Run all tasks concurrently
    if tasks:
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Bots shutting down...")
        except Exception as e:
            logger.error(f"Error running bots: {e}")
            traceback.print_exc()
        finally:
            # Close any open sessions when everything is done
            if REVOLT_AVAILABLE and REVOLT_TOKEN and 'session' in locals():
                await session.close()
    else:
        logger.error("No bots were started. Check your configuration and tokens.")

if __name__ == "__main__":
    asyncio.run(main())
