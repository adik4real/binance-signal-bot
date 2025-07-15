import logging
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import aiohttp
from aiohttp import web

TOKEN = os.environ.get("BOT_TOKEN") or "твoй_токен"
CHAT_ID = "970254189"
COINS = ['BTCUSDT', 'XRPUSDT', 'SOLUSDT', 'ADAUSDT', 'ETHUSDT', 'TONUSDT', 'BNBUSDT']

logging.basicConfig(level=logging.INFO)
signals_sent = {coin: None for coin in COINS}

# Binance API
async def get_binance_data(symbol):
    url = f'https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json() if resp.status == 200 else None

async def get_rsi(symbol, interval='1m', limit=14):
    url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            closes = [float(c[4]) for c in data]
            return calculate_rsi(closes)

def calculate_rsi(prices):
    if len(prices) < 14:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i-1]
        gains.append(max(delta, 0))
        losses.append(abs(min(delta, 0)))
    avg_gain = sum(gains) / 14
    avg_loss = sum(losses) / 14
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

# Telegram Logic
async def send_signal(app: Application, symbol, rsi, price):
    global signals_sent
    if rsi < 30 and signals_sent[symbol] != 'long':
        text = f"📈 Сигнал LONG на {symbol}\nRSI: {rsi}\nЦена: {price} USDT"
        signals_sent[symbol] = 'long'
    elif rsi > 70 and signals_sent[symbol] != 'short':
        text = f"📉 Сигнал SHORT на {symbol}\nRSI: {rsi}\nЦена: {price} USDT"
        signals_sent[symbol] = 'short'
    else:
        if 30 <= rsi <= 70:
            signals_sent[symbol] = None
        return
    await app.bot.send_message(chat_id=CHAT_ID, text=text)

async def monitor_prices(app: Application):
    while True:
        for coin in COINS:
            data = await get_binance_data(coin)
            if not data:
                continue
            price = float(data['lastPrice'])
            rsi = await get_rsi(coin)
            if rsi is not None:
                await send_signal(app, coin, rsi, price)
        await asyncio.sleep(5)

# Telegram handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(coin[:-4], callback_data=coin)] for coin in COINS]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите монету:", reply_markup=markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    symbol = query.data
    data = await get_binance_data(symbol)
    if not data:
        await query.edit_message_text("Ошибка получения данных.")
        return
    price = data['lastPrice']
    volume = data['quoteVolume']
    rsi = await get_rsi(symbol)
    rsi_text = str(rsi) if rsi else "Недоступно"
    await query.edit_message_text(
        f"{symbol[:-4]} данные:\nЦена: {price} USDT\nОбъем: {volume} USDT\nRSI: {rsi_text}"
    )

# AIOHTTP healthcheck
async def handle(request):
    return web.Response(text="OK")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# Запуск всей логики
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    # Запуск мониторинга цен в фоне
    asyncio.create_task(monitor_prices(app))
    # Запуск http-сервера
    asyncio.create_task(start_web_server())

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
