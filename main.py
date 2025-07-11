import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)
logger.info("Бот запущен!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот запущен!")

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    await update.message.reply_text(f"Ваш Chat ID: `{chat_id}`", parse_mode='Markdown')

def main():
    app = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", get_id))  # <-- внутри main
    logger.info("Starting bot...")
    try:
        app.run_polling()
    except Exception as e:
        logger.error(f"Ошибка запуска: {e}")

if __name__ == "__main__":
    main()
