def main():
    token = os.getenv("TELEGRAM_TOKEN")
    app = Application.builder().token(token).build()
    
    # Ваши обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", get_id))
    
    # Webhook конфигурация
    url = f"https://{os.getenv('FLY_APP_NAME')}.fly.dev/"
    app.run_webhook(
        listen="0.0.0.0",
        port=8080,
        webhook_url=url
    )
