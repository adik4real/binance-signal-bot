import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
import aiohttp
import asyncio

TOKEN = '7697993850:AAFXT0gI310499hrGUWwE3YUZr40jlHLzzo'
CHAT_ID = '970254189'
COINS = ['BTCUSDT', 'XRPUSDT', 'SOLUSDT', 'ADAUSDT', 'ETHUSDT', 'TONUSDT', 'BNBUSDT']

logging.basicConfig(level=logging.INFO)
signals_sent = {coin: None for coin in COINS}

async def get_binance_data(symbol):
    url = f'https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                return None

async def get_rsi(symbol, interval='1m', limit=14):
    url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                closes = [float(candle[4]) for candle in data]
                return calculate_rsi(closes)
            else:
                return None

def calculate_rsi(prices):
    if len(prices) < 14:
        return None
    gains = []
    losses = []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i-1]
        gains.append(max(delta, 0))
        losses.append(abs(min(delta, 0)))
    avg_gain = sum(gains) / 14
    avg_loss = sum(losses) / 14
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)

async def send_signal(app, symbol, rsi, price):
    global signals_sent
    chat_id = CHAT_ID
    message = ""
    if rsi < 30 and signals_sent[symbol] != 'long':
        message = f"📈 Сигнал LONG на {symbol}\nRSI: {rsi}\nЦена: {price} USDT"
        signals_sent[symbol] = 'long'
    elif rsi > 70 and signals_sent[symbol] != 'short':
        message = f"📉 Сигнал SHORT на {symbol}\nRSI: {rsi}\nЦена: {price} USDT"
        signals_sent[symbol] = 'short'
    else:
        if 30 <= rsi <= 70:
            signals_sent[symbol] = None
        return

    if message:
        await app.bot.send_message(chat_id=chat_id, text=message)

async def monitor_prices(app):
    while True:
        for coin in COINS:
            data = await get_binance_data(coin)
            if not data:
                continue
            price = float(data['lastPrice'])
            rsi = await get_rsi(coin)
            if rsi is None:
                continue
            await send_signal(app, coin, rsi, price)
        await asyncio.sleep(5)  # проверка каждые 5 секунд

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(coin[:-4], callback_data=coin)] for coin in COINS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Выберите монету:', reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    symbol = query.data
    data = await get_binance_data(symbol)
    if not data:
        await query.edit_message_text(text="Ошибка получения данных.")
        return
    price = data['lastPrice']
    volume = data['quoteVolume']
    rsi = await get_rsi(symbol)
    rsi_text = str(rsi) if rsi else "Недоступно"
    text = (
        f"{symbol[:-4]} данные:\n"
        f"Цена: {price} USDT\n"
        f"Объем торгов за 24ч: {volume} USDT\n"
        f"RSI (14): {rsi_text}"
    )
    await query.edit_message_text(text=text)

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button))

    # Запускаем мониторинг в фоне через job_queue
    async def job_callback(context):
        await monitor_prices(app)

    app.job_queue.run_repeating(job_callback, interval=5, first=5)

    app.run_polling()

if __name__ == '__main__':
    main()
