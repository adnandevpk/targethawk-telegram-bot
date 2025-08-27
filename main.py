import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
)
from dotenv import load_dotenv

import start_commands
import user_commands
import signal_management
import admin_commands
import bot_commands # Import the bot_commands file
import structure # Import the structure module

load_dotenv()

# === Environment & Logging ===
DB_URL = os.getenv("DATABASE_URL1")
logger = logging.getLogger(__name__)

# === Command Handlers ===
async def track_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adds a new signal to the database with tags."""
    args = context.args
    user_id = update.effective_user.id
    
    if len(args) < 4:
        await update.message.reply_text("❌ Usage: /track <symbol> <entry_price> <target_price_1> <stop_loss> [tags]")
        return
    
    symbol = args[0].upper()
    try:
        entry_price = float(args[1])
        target_price_1 = float(args[2])
        stop_loss = float(args[3])
    except ValueError:
        await update.message.reply_text("❌ Entry price, targets, and stop-loss must be numbers.")
        return
    
    tags = ' '.join(args[4:]) if len(args) > 4 else ""

    try:
        with bot_commands.get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO signals (user_id, symbol, entry_price, target_price_1, stop_loss, status, tags) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                    (user_id, symbol, entry_price, target_price_1, stop_loss, "Open", tags)
                )
                signal_id = cur.fetchone()['id']
            conn.commit()

        await update.message.reply_text(f"✅ Signal for {symbol} created with ID: {signal_id}. It is now being tracked.")
    except Exception as e:
        logger.error(f"Failed to add signal: {e}")
        await update.message.reply_text("❌ Failed to add signal. Please check your input and try again.")
        
async def list_signals_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the main signal management menu with buttons."""
    keyboard = [
        [
            InlineKeyboardButton("📈 List & Edit Signals", callback_data="show_signals_list"),
        ],
        [
            InlineKeyboardButton("🗑️ Delete Signals", callback_data="delete_signals"),
        ],
        [
            InlineKeyboardButton("➕ Add New Signal", callback_data="add_new_signal"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("What would you like to do with your signals?", reply_markup=reply_markup)

def register_handlers(app):
    """Registers all the command handlers with the Telegram bot application."""
    
    # 1. Register all basic command handlers
    app.add_handler(CommandHandler("start", start_commands.start_with_ref))
    app.add_handler(CommandHandler("plans", user_commands.plans))
    app.add_handler(CommandHandler("upgrade", user_commands.upgrade))
    app.add_handler(CommandHandler("refer", user_commands.refer))
    app.add_handler(CommandHandler("status", user_commands.status))
    app.add_handler(CommandHandler("leaderboard", user_commands.leaderboard))
    app.add_handler(CommandHandler("track", track_signal))
    
    # 2. Register the main signals menu command
    app.add_handler(CommandHandler("signals", list_signals_menu))
    
    # 2.1 Register the code structure command
    app.add_handler(CommandHandler("structure", structure.code_structure))
    
    # 3. Register the signal management conversation handlers
    # These handle the multi-step processes for editing and deleting signals.
    app.add_handler(signal_management.edit_signal_conv_handler)
    app.add_handler(signal_management.delete_signal_conv_handler)
    
    # 4. Register the admin commands
    # The 'admin_menu' command handles the main entry point for all admin actions.
    app.add_handler(CommandHandler("admin", admin_commands.admin_menu))
    # This handler processes all the buttons from the admin menu.
    app.add_handler(CallbackQueryHandler(admin_commands.handle_admin_menu_callback))
    # This is the conversation handler for the admin upgrade flow.
    app.add_handler(admin_commands.admin_upgrade_conv_handler)

    # 5. Add the new callback handlers for the inline buttons
    app.add_handler(CallbackQueryHandler(start_commands.show_plans_callback, pattern="^show_plans$"))
    app.add_handler(CallbackQueryHandler(start_commands.show_signals_callback, pattern="^show_signals_list$"))
    
    # 6. Log a message to confirm registration is complete
    logger.info("All command and callback handlers registered successfully.")

def main() -> None:
    """Entry point for the bot application."""
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN1")
    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN environment variable is not set.")
        return

    bot_commands.init_db()

    app = ApplicationBuilder().token(TOKEN).build()
    register_handlers(app)

    # Start the bot
    logger.info("🚀 Bot is starting...")
    app.run_polling()

if __name__ == '__main__':
    main()
