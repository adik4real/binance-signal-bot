import os
import asyncio
from telegram.ext import Application, CommandHandler

TOKEN = os.getenv("BOT_TOKEN")

async def start(update, context):
    await update.message.reply_text("Бот запущен и работает!")

async def run_bot():
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчик команды /start
    app.add_handler(CommandHandler("start", start))
    
    # Запускаем бота
    await app.initialize()
    await app.start()
    print("Бот успешно запущен")
    
    # Бесконечный цикл для поддержания работы
    while True:
        await asyncio.sleep(3600)  # Спим 1 час

    # Эти строки никогда не выполнятся, но оставляем для правильной структуры
    await app.stop()
    await app.shutdown()

def main():
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("Бот остановлен пользователем")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    main()
