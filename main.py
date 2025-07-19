import os
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
WEBHOOK_URL = f"https://{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = int(os.getenv("PORT", 8080))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот работает через webhook!")


async def handle(request):
    # Обработчик POST запроса от Telegram
    app = request.app['telegram_app']
    update = Update.de_json(await request.json(), app.bot)
    await app.update_queue.put(update)
    return web.Response(text='OK')


async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    # Создаем aiohttp приложение
    web_app = web.Application()
    web_app['telegram_app'] = app
    web_app.router.add_post(WEBHOOK_PATH, handle)

    # Устанавливаем webhook
    await app.bot.delete_webhook()
    await app.bot.set_webhook(WEBHOOK_URL)

    # Запускаем бота и aiohttp сервер параллельно
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    print(f"🚀 Webhook запущен: {WEBHOOK_URL}")

    # Запуск обработки апдейтов
    await app.initialize()
    await app.start()
    await app.updater.start_polling()  # или лучше app.updater.start_webhook(), но здесь мы запускаем через aiohttp свой сервер
    await app.updater.wait()


if __name__ == "__main__":
    asyncio.run(main())
