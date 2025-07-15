import threading
import os
import http.server
import socketserver

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

import httpx
import numpy as np

MY_CHAT_ID = 970254189
TOKEN = os.getenv("TELEGRAM_TOKEN")  # Убедись, что токен в переменной окружения

COINS = {
    "XRPUSDT": "XRPUSDT",
    "BTCUSDT": "BTCUSDT",
    "ETHUSDT": "ETHUSDT"
}

RSI_PERIOD = 14
TP_PERCENT = 0.03
SL_PERCENT = 0.015

last_signal = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Монеты", callback_data="menu_coins")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Главное меню:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_coins":
        keyboard = [[InlineKeyboardButton(coin[:-4], callback_data=f"coin_{coin}")] for coin in COINS.keys()]
        keyboard.append([InlineKeyboardButton("Назад", callback_data="back_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите монету:", reply_markup=reply_markup)

    elif data.startswith("coin_"):
        symbol = data.split("_")[1]
        details = await get_coin_details(symbol)
        if details is None:
            text = "Ошибка получения данных с Binance"
        else:
            text = (
                f"Монета: {symbol[:-4]}\n"
                f"Цена: ${details['price']:.4f}\n"
                f"RSI (14): {details['rsi']:.2f}\n"
                f"Объем (24ч): {details['volume_24h']:.2f}\n"
                f"Изменение (24ч): {details['price_change_percent']:.2f}%"
            )
        keyboard = [[InlineKeyboardButton("Назад", callback_data="menu_coins")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    elif data == "back_main":
        keyboard = [[InlineKeyboardButton("Монеты", callback_data="menu_coins")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Главное меню:", reply_markup=reply_markup)

async def get_coin_details(symbol: str):
    url_klines = "https://api.binance.com/api/v3/klines"
    params_klines = {"symbol": symbol, "interval": "1h", "limit": RSI_PERIOD + 1}
    url_ticker = "https://api.binance.com/api/v3/ticker/24hr"
    params_ticker = {"symbol": symbol}

    async with httpx.AsyncClient() as client:
        resp_klines = await client.get(url_klines, params=params_klines)
        resp_ticker = await client.get(url_ticker, params=params_ticker)

        if resp_klines.status_code != 200 or resp_ticker.status_code != 200:
            return None

        klines = resp_klines.json()
        ticker = resp_ticker.json()

    closes = [float(candle[4]) for candle in klines]
    rsi = calculate_rsi(closes, RSI_PERIOD)
    last_price = closes[-1]

    volume_24h = float(ticker.get("volume", 0))
    price_change_percent = float(ticker.get("priceChangePercent", 0))

    return {
        "price": last_price,
        "rsi": rsi,
        "volume_24h": volume_24h,
        "price_change_percent": price_change_percent,
    }

def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    seed = deltas[:period]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    if down == 0:
        return 100.0
    rs = up / down
    rsi = 100.0 - (100.0 / (1.0 + rs))

    for delta in deltas[period:]:
        upval = delta if delta > 0 else 0.0
        downval = -delta if delta < 0 else 0.0

        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period

        if down == 0:
            return 100.0
        rs = up / down
        rsi = 100.0 - (100.0 / (1.0 + rs))

    return rsi

async def check_signals(app):
    global last_signal
    for symbol in COINS.keys():
        details = await get_coin_details(symbol)
        if not details:
            continue

        price = details['price']
        rsi = details['rsi']

        signal = None
        if rsi < 30:
            signal = "LONG"
        elif rsi > 70:
            signal = "SHORT"

        if signal and last_signal.get(symbol) != signal:
            last_signal[symbol] = signal

            tp = price * (1 + TP_PERCENT if signal == "LONG" else 1 - TP_PERCENT)
            sl = price * (1 - SL_PERCENT if signal == "LONG" else 1 + SL_PERCENT)

            msg = (
                f"Сигнал по {symbol[:-4]}: {signal}\n"
                f"Цена входа: ${price:.2f}\n"
                f"Take Profit: ${tp:.2f}\n"
                f"Stop Loss: ${sl:.2f}\n"
                f"RSI: {rsi:.2f}"
            )
            await app.bot.send_message(chat_id=MY_CHAT_ID, text=msg)
            print("Отправлен сигнал:", msg)

async def periodic_check(context: ContextTypes.DEFAULT_TYPE):
    await check_signals(context.application)

def run_http_server():
    PORT = 8080
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"HTTP server running on port {PORT}")
        httpd.serve_forever()

def main():
    print("Запуск бота...")

    # Запускаем HTTP сервер в отдельном потоке
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    # Создаем и настраиваем приложение
    app = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Настраиваем периодическую проверку
    app.job_queue.run_repeating(periodic_check, interval=60.0, first=0.0)

    # Запускаем бота
    app.run_polling()

if __name__ == "__main__":
    # Убираем asyncio.run, так как run_polling уже управляет event loop
    main()
