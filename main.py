import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from binance.client import Client

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Бот запущен! Используйте /signal")

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price = client.get_symbol_ticker(symbol="BTCUSDT")["price"]
    await update.message.reply_text(f"📊 BTC/USDT: {price}")

if __name__ == "__main__":
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal))
    app.run_polling()
