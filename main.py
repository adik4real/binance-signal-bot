import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
import aiohttp

TOKEN = 'твой_бот_токен_здесь'
CHAT_ID = твой_чат_id_или_группа_куда_отправлять_сигналы (например, int)

# Монеты для мониторинга и отображения
COINS = ['BTCUSDT', 'XRPUSDT', 'SOLUSDT', 'ADAUSDT', 'ETHUSDT', 'TONUSDT', 'BNBUSDT']

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Хранение состояний сигналов, чтобы не спамить
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
    # Получаем свечи для расчета RSI
    url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                closes = [float(candle[4]) for candle in data]  # цена закрытия
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
        if delta >= 0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(delta))
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
        # Если RSI в норме - сбрасываем состояние, чтобы можно было отправить сигнал позже
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
    keyboard = [
        [InlineKeyboardButton(coin[:-4], callback_data=coin)] for coin in COINS
    ]
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

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button))

    # Запускаем мониторинг в фоне
    asyncio.create_task(monitor_prices(app))

    await app.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
