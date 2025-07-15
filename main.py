import logging
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import aiohttp
from aiohttp import web

# Configuration
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

CHAT_ID = "970254189"
COINS = ['BTCUSDT', 'XRPUSDT', 'SOLUSDT', 'ADAUSDT', 'ETHUSDT', 'TONUSDT', 'BNBUSDT']
CHECK_INTERVAL = 60  # seconds

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

signals_sent = {coin: None for coin in COINS}

class BinanceAPI:
    def __init__(self):
        self.session = aiohttp.ClientSession()

    async def close(self):
        await self.session.close()

    async def get_ticker_data(self, symbol):
        url = f'https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}'
        try:
            async with self.session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    return await resp.json()
                logger.error(f"Binance API error for {symbol}: HTTP {resp.status}")
                return None
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None

    async def get_rsi(self, symbol, interval='1h', limit=14):
        url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'
        try:
            async with self.session.get(url, timeout=5) as resp:
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
            
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [max(d, 0) for d in deltas]
        losses = [abs(min(d, 0)) for d in deltas]
        
        avg_gain = sum(gains[:14]) / 14
        avg_loss = sum(losses[:14]) / 14
        
        if avg_loss == 0:
            return 100
            
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 2)

class TradingBot:
    def __init__(self):
        self.binance = BinanceAPI()
        self.app = None

    async def send_signal(self, symbol, rsi, price):
        if rsi is None:
            return

        global signals_sent
        
        if rsi < 30 and signals_sent[symbol] != 'long':
            text = f"📈 LONG signal for {symbol}\nRSI: {rsi}\nPrice: {price} USDT"
            signals_sent[symbol] = 'long'
        elif rsi > 70 and signals_sent[symbol] != 'short':
            text = f"📉 SHORT signal for {symbol}\nRSI: {rsi}\nPrice: {price} USDT"
            signals_sent[symbol] = 'short'
        else:
            if 30 <= rsi <= 70:
                signals_sent[symbol] = None
            return
            
        try:
            await self.app.bot.send_message(chat_id=CHAT_ID, text=text)
            logger.info(f"Signal sent for {symbol}")
        except Exception as e:
            logger.error(f"Error sending signal for {symbol}: {str(e)}")

    async def monitor_prices(self):
        while True:
            try:
                for coin in COINS:
                    data = await self.binance.get_ticker_data(coin)
                    if not data:
                        continue
                        
                    price = float(data['lastPrice'])
                    rsi = await self.binance.get_rsi(coin)
                    await self.send_signal(coin, rsi, price)
                    
                await asyncio.sleep(CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(10)  # Wait before retrying

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [[InlineKeyboardButton(coin[:-4], callback_data=coin)] for coin in COINS]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select a coin:", reply_markup=markup)

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        symbol = query.data
        data = await self.binance.get_ticker_data(symbol)
        if not data:
            await query.edit_message_text("Error getting data.")
            return
            
        price = data['lastPrice']
        volume = data['quoteVolume']
        rsi = await self.binance.get_rsi(symbol)
        rsi_text = str(rsi) if rsi else "N/A"
        
        await query.edit_message_text(
            f"{symbol[:-4]} data:\nPrice: {price} USDT\nVolume: {volume} USDT\nRSI: {rsi_text}"
        )

    async def health_check(self, request):
        return web.Response(text="OK")

    async def start_web_server(self):
        app = web.Application()
        app.router.add_get("/", self.health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.environ.get("PORT", 8080))
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"Web server started on port {port}")

    async def run(self):
        # Create Telegram application
        self.app = Application.builder().token(TOKEN).build()
        
        # Add handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CallbackQueryHandler(self.button_handler))

        # Start background tasks
        asyncio.create_task(self.monitor_prices())
        asyncio.create_task(self.start_web_server())

        # Run the bot
        await self.app.run_polling()

    async def shutdown(self):
        await self.binance.close()
        logger.info("Bot shutdown complete")

async def main():
    bot = TradingBot()
    try:
        await bot.run()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
    finally:
        await bot.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
