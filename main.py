import os
from telegram.ext import Application, CommandHandler

def start(update, context):
    update.message.reply_text("Привет! Я бот.")

def get_id(update, context):
    update.message.reply_text(f"Твой ID: {update.effective_user.id}")

def main():
    print("Запуск бота...")
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        print("Ошибка: TELEGRAM_TOKEN не установлен")
        return
    print(f"Токен: {token[:5]}...")

    app = Application.builder().token(token).build()
    print("Приложение создано")

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", get_id))
    print("Обработчики добавлены")

    print("Запуск webhook...")
    app.run_webhook(
        listen="0.0.0.0",
        port=8080,
        webhook_url=f"https://{os.getenv('FLY_APP_NAME')}.fly.dev/",
        cert="cert.pem",
        key="key.pem"
    )
    print("Бот запущен")

if __name__ == "__main__":
    main()
