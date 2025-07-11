import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет сообщение при команде /start"""
    await update.message.reply_text('🚀 Бот запущен!')

def main():
    """Запуск бота"""
    app = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    
    # Режим опроса (для теста без вебхуков)
    logger.info("Бот запущен в режиме polling...")
    app.run_polling()

if __name__ == '__main__':
    main()
