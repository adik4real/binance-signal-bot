import os
import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
import aiohttp
from aiohttp import web

# Configuration
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def start(update, context):
    await update.message.reply_text("Bot is running!")

async def health_check(request):
    return web.Response(text="OK")

async def run_bot():
    # Create Telegram application
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    # Start HTTP server for health checks
    runner = web.AppRunner(web.Application())
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("Health check server started on port 8080")
    
    # Run bot
    await app.initialize()
    await app.start()
    logger.info("Bot started successfully")
    
    # Keep running
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
