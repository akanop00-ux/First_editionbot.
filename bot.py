import os
import logging
import feedparser
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
from feeds import FEEDS

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8443))
WEBHOOK_URL = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")  # optional: auto-post target

WELCOME = (
    "📰 *First Edition*\n\n"
    "Discover useful updates, exclusive content, and new opportunities "
    "in one place.\n\n"
    "*Commands:*\n"
    "/latest – Latest headlines\n"
    "/tech – Tech news\n"
    "/world – World news\n"
    "/opportunities – Grants, jobs, scholarships\n"
    "/subscribe – Get auto updates here\n"
    "/help – Show this again"
)


def fetch_feed(url, limit=5):
    """Pull top N items from an RSS feed."""
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:limit]:
        items.append({
            "title": entry.get("title", "No title"),
            "link": entry.get("link", ""),
            "summary": entry.get("summary", "")[:300],
        })
    return items


def format_items(items, category):
    if not items:
        return f"No {category} news right now. Try again later."
    lines = [f"📌 *{category.title()}*\n"]
    for i, item in enumerate(items, 1):
        lines.append(
            f"{i}. [{item['title']}]({item['link']})\n"
            f"_{item['summary']}..._\n"
        )
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        WELCOME, parse_mode="Markdown", disable_web_page_preview=True
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        WELCOME, parse_mode="Markdown", disable_web_page_preview=True
    )


async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fetching latest... ⏳")
    all_items = []
    for category, urls in FEEDS.items():
        for url in urls:
            all_items.extend(fetch_feed(url, limit=3))
    text = format_items(all_items[:8], "Latest Headlines")
    await update.message.reply_text(
        text, parse_mode="Markdown", disable_web_page_preview=True
    )


async def category_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /tech, /world, /opportunities."""
    cmd = update.message.text.lstrip("/").split()[0].lower()
    if cmd not in FEEDS:
        await update.message.reply_text("Unknown category.")
        return
    items = []
    for url in FEEDS[cmd]:
        items.extend(fetch_feed(url, limit=5))
    text = format_items(items[:8], cmd)
    await update.message.reply_text(
        text, parse_mode="Markdown", disable_web_page_preview=True
    )


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # Store subscribers — for production use a DB
    context.bot_data.setdefault("subscribers", set()).add(chat_id)
    await update.message.reply_text(
        "✅ Subscribed. You'll receive news updates here automatically."
    )


async def auto_post(context: ContextTypes.DEFAULT_TYPE):
    """Scheduled job — runs every N minutes."""
    subscribers = context.bot_data.get("subscribers", set())
    if CHANNEL_ID:
        subscribers.add(int(CHANNEL_ID))
    if not subscribers:
        return

    items = []
    for urls in FEEDS.values():
        for url in urls:
            items.extend(fetch_feed(url, limit=2))

    if not items:
        return

    text = format_items(items[:5], "Today's Edition")
    for chat_id in list(subscribers):
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.warning(f"Failed to send to {chat_id}: {e}")


def main():
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("latest", latest))
    app.add_handler(CommandHandler("subscribe", subscribe))
    for cat in FEEDS:
        app.add_handler(CommandHandler(cat, category_cmd))

    # Auto-post every 60 minutes
    app.job_queue.run_repeating(auto_post, interval=3600, first=60)

    if WEBHOOK_URL:
        webhook = f"https://{WEBHOOK_URL}/webhook"
        logger.info(f"Starting webhook on {webhook}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="/webhook",
            webhook_url=webhook,
        )
    else:
        logger.info("Polling mode (local dev)")
        app.run_polling()


if __name__ == "__main__":
    main()
