import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)
logger.info("Бот запущен!")
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Бот запущен!")

def main():
    app = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    logger.info("Starting bot...")
    app.run_polling()

if __name__ == "__main__":
    main()
async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    await update.message.reply_text(f"Ваш Chat ID: `{chat_id}`", parse_mode='Markdown')
app.add_handler(CommandHandler("id", get_id))
