import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, CommandHandler
import aiohttp

TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"

COINS = ["BTCUSDT", "XRPUSDT", "SOLUSDT", "ADAUSDT", "ETHUSDT", "TONUSDT", "BNBUSDT"]

async def fetch_binance_data(symbol):
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                return None

async def fetch_klines(symbol, interval='1h', limit=50):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                return None

def calculate_rsi(prices, period=14):
    gains = []
    losses = []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i-1]
        if delta > 0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(delta))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rsis = []
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)

def calculate_macd(prices, slow=26, fast=12, signal=9):
    # Простейшая реализация MACD на основе EMA, чтобы не усложнять
    # Можно использовать библиотеку ta-lib для точных расчетов
    def ema(prices, period):
        emas = []
        k = 2 / (period + 1)
        emas.append(prices[0])  # start ema с первого значения
        for price in prices[1:]:
            ema_val = price * k + emas[-1] * (1 - k)
            emas.append(ema_val)
        return emas

    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    macd_line = [f - s for f, s in zip(ema_fast[-len(ema_slow):], ema_slow)]
    signal_line = ema(macd_line, signal)
    macd_histogram = [m - s for m, s in zip(macd_line[-len(signal_line):], signal_line)]
    # Возвращаем последние значения MACD, signal и гистограммы
    if len(macd_line) == 0 or len(signal_line) == 0:
        return (0, 0, 0)
    return round(macd_line[-1], 4), round(signal_line[-1], 4), round(macd_histogram[-1], 4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(coin[:-4], callback_data=coin)] for coin in COINS
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите монету:", reply_markup=reply_markup)

async def coin_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    symbol = query.data

    data = await fetch_binance_data(symbol)
    if not data:
        await query.edit_message_text("Ошибка получения данных.")
        return

    klines = await fetch_klines(symbol)
    if not klines:
        await query.edit_message_text("Ошибка получения исторических данных.")
        return

    # Получаем цены закрытия для RSI и MACD
    closes = [float(kline[4]) for kline in klines]

    rsi = calculate_rsi(closes)
    macd_line, signal_line, macd_hist = calculate_macd(closes)

    price = float(data['lastPrice'])
    volume = float(data['quoteVolume'])
    price_change_percent = float(data['priceChangePercent'])

    # Сигналы RSI
    if rsi < 30:
        rsi_signal = "📈 RSI низкий — возможна покупка"
    elif rsi > 70:
        rsi_signal = "📉 RSI высокий — возможна продажа"
    else:
        rsi_signal = "RSI в нейтральной зоне"

    text = (
        f"Информация по {symbol[:-4]}:\n"
        f"Цена: {price:.4f} USDT\n"
        f"Объем торгов за 24ч: {volume:.2f} USDT\n"
        f"Изменение цены за 24ч: {price_change_percent:.2f}%\n\n"
        f"RSI: {rsi} — {rsi_signal}\n"
        f"MACD: {macd_line} (MACD линия)\n"
        f"Signal: {signal_line}\n"
        f"Histogram: {macd_hist}\n\n"
        "Для выбора другой монеты нажмите /start"
    )
    await query.edit_message_text(text)

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(coin_info))

    print("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
