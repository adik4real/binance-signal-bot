import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher
from aiogram.types import Message
import asyncio
import logging
import os

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# — HTTP server —
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_http_server():
    server = HTTPServer(('0.0.0.0', 8080), SimpleHandler)
    logging.info("HTTP server running on port 8080")
    server.serve_forever()

# — Telegram handler —
@dp.message()
async def handle_message(message: Message):
    await message.reply("Бот работает!")

# — Telegram bot runner —
def run_bot():
    asyncio.run(dp.start_polling(bot))

# — Main entry point —
def main():
    logging.basicConfig(level=logging.INFO)

    # Запускаем HTTP сервер в отдельном потоке
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    # Запускаем бота в основном потоке
    run_bot()

if __name__ == "__main__":
    main()
