"""
Vex Bot - Multi-platform Discord and Revolt Bot
"""
import os
import logging
import asyncio
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("vex-bot")

# Load environment variables from .env file if present
load_dotenv()

# Entry point
if __name__ == "__main__":
    try:
        # Try the multi-platform approach
        from vex import main
        logger.info("Starting Vex multi-platform bot...")
        asyncio.run(main())
    except ImportError as e:
        logger.error(f"Failed to import multi-platform code: {e}")
        
        # Fallback to original Discord-only bot if multi-platform fails
        try:
            logger.info("Attempting to fall back to Discord-only bot...")
            # This import is likely working, but the execution is missing
            import vex
            
            # If vex doesn't have a main() function, it might be expecting to be executed directly
            # Let's check if it has run function or bot.run
            if hasattr(vex, 'main'):
                asyncio.run(vex.main())
            elif hasattr(vex, 'bot') and hasattr(vex.bot, 'run') and hasattr(vex, 'DISCORD_TOKEN'):
                vex.bot.run(vex.DISCORD_TOKEN)
            else:
                logger.error("Could not find a way to start the bot in the vex module")
        except Exception as e:
            logger.critical(f"Could not start bot: {e}")
            raise