import logging
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
import aiohttp

# Configuration
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

CHAT_ID = "970254189"
COINS = ["BTCUSDT", "XRPUSDT", "SOLUSDT", "ADAUSDT", "ETHUSDT", "TONUSDT", "BNBUSDT"]
CHECK_INTERVAL = 60  # seconds

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class BinanceTradingBot:
    def __init__(self):
        self.signals_sent = {coin: None for coin in COINS}
        self.http_session = None
        self.application = None

    async def initialize(self):
        self.http_session = aiohttp.ClientSession()
        self.application = Application.builder().token(TOKEN).build()
        
        # Register handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        
        # Start background tasks
        self.application.job_queue.run_repeating(
            self.monitor_prices, interval=CHECK_INTERVAL, first=0.0
        )

    async def shutdown(self):
        if self.http_session:
            await self.http_session.close()
        logger.info("Bot shutdown complete")

    async def get_ticker_data(self, symbol):
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
        try:
            async with self.http_session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    return await resp.json()
                logger.error(f"Binance API error for {symbol}: HTTP {resp.status}")
                return None
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None

    async def get_rsi(self, symbol, interval="1h", limit=14):
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            async with self.http_session.get(url, timeout=5) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                closes = [float(c[4]) for c in data]
                return self.calculate_rsi(closes)
        except Exception as e:
            logger.error(f"Error fetching RSI for {symbol}: {str(e)}")
            return None

    @staticmethod
    def calculate_rsi(prices):
        if len(prices) < 14:
            return None

        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [max(d, 0) for d in deltas]
        losses = [abs(min(d, 0)) for d in deltas]

        avg_gain = sum(gains[:14]) / 14
        avg_loss = sum(losses[:14]) / 14

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 2)

    async def send_signal(self, symbol, rsi, price):
        if rsi is None:
            return

        if rsi < 30 and self.signals_sent[symbol] != "long":
            text = f"📈 LONG signal for {symbol}\nRSI: {rsi}\nPrice: {price} USDT"
            self.signals_sent[symbol] = "long"
        elif rsi > 70 and self.signals_sent[symbol] != "short":
            text = f"📉 SHORT signal for {symbol}\nRSI: {rsi}\nPrice: {price} USDT"
            self.signals_sent[symbol] = "short"
        else:
            if 30 <= rsi <= 70:
                self.signals_sent[symbol] = None
            return

        try:
            await self.application.bot.send_message(chat_id=CHAT_ID, text=text)
            logger.info(f"Signal sent for {symbol}")
        except Exception as e:
            logger.error(f"Error sending signal for {symbol}: {str(e)}")

    async def monitor_prices(self, context: ContextTypes.DEFAULT_TYPE):
        for coin in COINS:
            try:
                data = await self.get_ticker_data(coin)
                if not data:
                    continue

                price = float(data["lastPrice"])
                rsi = await self.get_rsi(coin)
                await self.send_signal(coin, rsi, price)
            except Exception as e:
                logger.error(f"Error processing {coin}: {str(e)}")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton(coin[:-4], callback_data=coin)] for coin in COINS
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select a coin:", reply_markup=markup)

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        symbol = query.data
        data = await self.get_ticker_data(symbol)
        if not data:
            await query.edit_message_text("Error getting data.")
            return

        price = data["lastPrice"]
        volume = data["quoteVolume"]
        rsi = await self.get_rsi(symbol)
        rsi_text = str(rsi) if rsi else "N/A"

        await query.edit_message_text(
            f"{symbol[:-4]} data:\nPrice: {price} USDT\nVolume: {volume} USDT\nRSI: {rsi_text}"
        )

async def run_bot():
    bot = BinanceTradingBot()
    try:
        await bot.initialize()
        await bot.application.run_polling()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
    finally:
        await bot.shutdown()

def main():
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()
