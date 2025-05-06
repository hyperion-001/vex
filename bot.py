"""
Vex Bot - Multi-platform Discord and Revolt Bot
"""
import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("vex-bot")

# Load environment variables from .env file if present
load_dotenv()

# Import the multi-platform bot code
try:
    from vex_multiplatform import main
    logger.info("Starting Vex multi-platform bot...")
    
    # Execute the main function
    if __name__ == "__main__":
        import asyncio
        asyncio.run(main())
        
except ImportError as e:
    logger.error(f"Failed to import multi-platform code: {e}")
    
    # Fallback to original Discord-only bot if multi-platform fails
    try:
        logger.info("Attempting to fall back to Discord-only bot...")
        import vex
        logger.info("Discord-only bot started.")
    except ImportError:
        logger.critical("Could not import either bot implementation. Check your installation.")
        raise