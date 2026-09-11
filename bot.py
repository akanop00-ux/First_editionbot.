import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8443))
WEBHOOK_URL = os.environ.get("RAILWAY_PUBLIC_DOMAIN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Discover useful updates, exclusive content, and new opportunities in one place. "
        "Start the bot to explore what's available and stay updated."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Available commands: /start, /help")

def main():
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return

    # Build application
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Determine webhook URL
    if WEBHOOK_URL:
        webhook_url = f"https://{WEBHOOK_URL}/webhook"
        logger.info(f"Starting webhook on {webhook_url}")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="/webhook",
            webhook_url=webhook_url,
            secret_token=os.environ.get("WEBHOOK_SECRET", ""),
        )
    else:
        # Fallback to polling for local testing
        logger.info("Starting polling mode (local development)")
        application.run_polling()

if __name__ == "__main__":
    main()
