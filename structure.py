# structure.py
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def code_structure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Lists the project file structure with brief descriptions.
    """
    try:
        structure_message = (
            "*🏗️ TargetHawk Bot - Project Structure:*\n\n"
            "• **main.py** - Entry point; sets up the bot and registers command handlers.\n"
            "• **db.py** - Manages database connections and initializes tables.\n"
            "• **bot_commands.py** - Contains shared DB functions, logging, and initialization routines.\n"
            "• **start_commands.py** - Handles the /start command and referral logic.\n"
            "• **user_commands.py** - Provides user commands (plans, upgrade, refer, status, leaderboard).\n"
            "• **signal_management.py** - Handles signal tracking, editing, and deletion flows.\n"
            "• **admin_commands.py** - Admin-only commands and upgrade/statistics functionality.\n"
            "• **payment.py** - Displays available payment options and plans.\n"
            "• **upgrade.py** - Logs and processes user upgrades.\n"
            "• **referral.py** - Manages referral tracking and related functionality.\n"
            "• **structure.py** - Provides project structure listing (this file).\n"
            "• **README.md** - Basic project documentation.\n\n"
            "_Use these files to understand the bot's architecture and functionality._"
        )

        # Send the formatted message using markdown
        await update.message.reply_text(structure_message, parse_mode="Markdown")
        logger.info(f"Code structure requested by user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error while listing project structure: {e}")
        await update.message.reply_text("❌ An error occurred while listing the project structure.")
