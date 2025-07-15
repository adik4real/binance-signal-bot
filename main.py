import logging
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import aiohttp

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

class TradingBot:
    def __init__(self):
        self.signals_sent = {coin: None for coin in COINS}
        self.session = None
        self.application = None
        self.stop_event = asyncio.Event()

    async def start(self):
        """Initialize and run the bot"""
        self.session = aiohttp.ClientSession()
        self.application = Application.builder().token(TOKEN).build()
        
        # Register handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        
        # Start price monitoring
        self.application.job_queue.run_repeating(
            self.monitor_prices, 
            interval=CHECK_INTERVAL, 
            first=0.0
        )
        
        # Start HTTP server for health checks
        asyncio.create_task(self.run_health_check())
        
        # Run the bot
        await self.application.run_polling(stop_signals=[])

    async def run_health_check(self):
        """Simple HTTP server for health checks"""
        async def handle(request):
            return aiohttp.web.Response(text="OK")

        app = aiohttp.web.Application()
        app.router.add_get('/', handle)
        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()
        logger.info("Health check server running on port 8080")

    async def shutdown(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
        if self.application:
            await self.application.shutdown()
        logger.info("Bot shutdown complete")

    async def get_ticker_data(self, symbol):
        """Fetch ticker data from Binance"""
        url = f'https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}'
        try:
            async with self.session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    return await resp.json()
                logger.error(f"Binance API error for {symbol}: HTTP {resp.status}")
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
        return None

    async def monitor_prices(self, context: ContextTypes.DEFAULT_TYPE):
        """Check prices and send signals"""
        for coin in COINS:
            try:
                data = await self.get_ticker_data(coin)
                if not data:
                    continue
                    
                price = float(data['lastPrice'])
                rsi = await self.get_rsi(coin)
                await self.send_signal(coin, rsi, price)
            except Exception as e:
                logger.error(f"Error processing {coin}: {str(e)}")

    async def send_signal(self, symbol, rsi, price):
        """Send trading signal if conditions are met"""
        if rsi is None:
            return

        if rsi < 30 and self.signals_sent[symbol] != 'long':
            text = f"📈 LONG signal for {symbol}\nRSI: {rsi}\nPrice: {price} USDT"
            self.signals_sent[symbol] = 'long'
        elif rsi > 70 and self.signals_sent[symbol] != 'short':
            text = f"📉 SHORT signal for {symbol}\nRSI: {rsi}\nPrice: {price} USDT"
            self.signals_sent[symbol] = 'short'
        else:
            if 30 <= rsi <= 70:
                self.signals_sent[symbol] = None
            return
            
        try:
            await self.application.bot.send_message(chat_id=CHAT_ID, text=text)
            logger.info(f"Signal sent for {symbol}")
        except Exception as e:
            logger.error(f"Error sending signal: {str(e)}")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        keyboard = [[InlineKeyboardButton(coin[:-4], callback_data=coin)] for coin in COINS]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select a coin:", reply_markup=markup)

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button presses"""
        query = update.callback_query
        await query.answer()
        
        symbol = query.data
        data = await self.get_ticker_data(symbol)
        if not data:
            await query.edit_message_text("Error getting data.")
            return
            
        price = data['lastPrice']
        volume = data['quoteVolume']
        rsi = await self.get_rsi(symbol)
        rsi_text = str(rsi) if rsi else "N/A"
        
        await query.edit_message_text(
            f"{symbol[:-4]} data:\nPrice: {price} USDT\nVolume: {volume} USDT\nRSI: {rsi_text}"
        )

async def main():
    """Entry point with proper error handling"""
    bot = TradingBot()
    try:
        await bot.start()
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
    finally:
        await bot.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
