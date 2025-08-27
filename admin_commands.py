# admin_commands.py
import os
import logging
from typing import Optional, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import bot_commands
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()

# === Constants ===
VALID_TIERS = ['Free', 'Pro', 'VIP']
MAX_EXPIRY_DAYS = 365
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")

# === Conversation States for Admin Upgrade ===
ADMIN_UPGRADE_DETAILS = range(1)

# === Helper Functions ===
def is_admin(user_id: int) -> bool:
    """Checks if the user ID matches the admin user ID from environment variables.
    
    Args:
        user_id: The user ID to check
        
    Returns:
        True if user is admin, False otherwise
    """
    admin_id_str = os.getenv("ADMIN_USER_ID")
    if not admin_id_str:
        logger.warning("ADMIN_USER_ID not set in environment")
        return False
    
    try:
        return int(admin_id_str) == user_id
    except (ValueError, TypeError):
        logger.warning("Invalid ADMIN_USER_ID format in environment")
        return False

async def validate_user_exists(user_id: int) -> bool:
    """Check if user exists in database before upgrading.
    
    Args:
        user_id: The user ID to validate
        
    Returns:
        True if user exists, False otherwise
    """
    try:
        with bot_commands.get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
                return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"Error validating user existence: {e}")
        return False

# === Admin Command Handlers ===

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to show the admin menu.
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔️ You are not authorized to use this command.")
        return

    keyboard = [
        [InlineKeyboardButton("📈 Get Bot Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("🚀 Upgrade User Plan", callback_data="admin_upgrade_flow")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Admin Menu:", reply_markup=reply_markup)
    
async def handle_admin_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles callback queries from the admin menu.
    
    Args:
        update: Telegram update object
        context: Bot context
    """
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.edit_message_text("⛔️ You are not authorized to use this command.")
        return

    if query.data == "admin_stats":
        await admin_stats(update, context, is_callback=True)
    elif query.data == "admin_upgrade_flow":
        await admin_upgrade_start(update, context)

async def admin_upgrade_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation flow for admin upgrade.
    
    Args:
        update: Telegram update object
        context: Bot context
        
    Returns:
        Conversation state
    """
    await update.callback_query.edit_message_text(
        "✍️ Please provide the User ID, Tier, and (optional) duration in days, separated by spaces.\n\n"
        f"Usage: `<user_id> <tier> [days]`\n"
        f"Valid tiers: {', '.join(VALID_TIERS)}\n"
        f"Max duration: {MAX_EXPIRY_DAYS} days"
    )
    return ADMIN_UPGRADE_DETAILS

async def admin_upgrade_complete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Completes the admin upgrade and updates the database.
    
    Args:
        update: Telegram update object
        context: Bot context
        
    Returns:
        ConversationHandler.END
    """
    args = update.message.text.split()
    
    if len(args) < 2:
        await update.message.reply_text(
            f"❌ Usage: `<user_id> <tier> [days]`\n"
            f"Valid tiers: {', '.join(VALID_TIERS)}"
        )
        return ConversationHandler.END

    try:
        target_user_id = int(args[0])
        new_tier = args[1]
        expiry_days = int(args[2]) if len(args) > 2 else None
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid arguments. User ID and expiry days must be numbers.")
        return ConversationHandler.END

    # Validate tier
    if new_tier not in VALID_TIERS:
        await update.message.reply_text(f"❌ Invalid tier. Valid tiers are: {', '.join(VALID_TIERS)}.")
        return ConversationHandler.END
    
    # Validate expiry days
    if expiry_days is not None and (expiry_days <= 0 or expiry_days > MAX_EXPIRY_DAYS):
        await update.message.reply_text(f"❌ Invalid expiry days. Must be between 1 and {MAX_EXPIRY_DAYS}.")
        return ConversationHandler.END
    
    # Check if user exists
    if not await validate_user_exists(target_user_id):
        await update.message.reply_text(f"❌ User {target_user_id} does not exist in the database.")
        return ConversationHandler.END
        
    try:
        bot_commands.log_upgrade(target_user_id, new_tier, 'Admin Upgrade', expiry_days)
        
        # Notify the admin
        await update.message.reply_text(
            f"✅ Successfully upgraded user {target_user_id} to '{new_tier}'."
            f"{f' Trial will expire in {expiry_days} days.' if expiry_days else ''}"
        )
        
        # Notify the upgraded user
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"🎉 You have been upgraded to the {new_tier} plan by an administrator!"
                f"{f' This upgrade expires in {expiry_days} days.' if expiry_days else ''}"
            )
        except Exception as notification_error:
            logger.warning(f"Could not notify user {target_user_id}: {notification_error}")
            await update.message.reply_text("⚠️ User upgraded successfully but notification failed.")
            
    except psycopg2.Error as db_error:
        logger.error(f"Database error in admin upgrade for user {target_user_id}: {db_error}")
        await update.message.reply_text("❌ Database error occurred. Please try again.")
    except Exception as e:
        logger.error(f"Unexpected error in admin upgrade for user {target_user_id}: {e}")
        await update.message.reply_text("❌ An unexpected error occurred. Check logs for details.")
    
    return ConversationHandler.END

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False) -> None:
    """Provides key statistics about the bot's users and signals.
    
    Args:
        update: Telegram update object
        context: Bot context
        is_callback: Whether this was called from a callback query
    """
    if not is_admin(update.effective_user.id):
        error_message = "⛔️ You are not authorized to use this command."
        if is_callback:
            await update.callback_query.edit_message_text(error_message)
        else:
            await update.message.reply_text(error_message)
        return
        
    stats_text = "📊 Bot Statistics:\n\n"
    
    try:
        with bot_commands.get_db_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get comprehensive stats in fewer queries
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_users,
                        COUNT(CASE WHEN tier = 'Free' THEN 1 END) as free_users,
                        COUNT(CASE WHEN tier = 'Pro' THEN 1 END) as pro_users,
                        COUNT(CASE WHEN tier = 'VIP' THEN 1 END) as vip_users,
                        SUM(referrals) as total_referrals
                    FROM users
                """)
                user_stats = cur.fetchone()
                
                stats_text += f"👥 Total Users: {user_stats['total_users']}\n"
                stats_text += f"  - Free: {user_stats['free_users']}\n"
                stats_text += f"  - Pro: {user_stats['pro_users']}\n"
                stats_text += f"  - VIP: {user_stats['vip_users']}\n"
                stats_text += f"🔗 Total Referrals: {user_stats['total_referrals']}\n\n"
                    
                # Signal statistics
                cur.execute("""
                    SELECT 
                        COUNT(CASE WHEN status = 'Open' THEN 1 END) as active_signals,
                        COUNT(CASE WHEN status = 'Closed' THEN 1 END) as closed_signals,
                        COUNT(CASE WHEN status = 'Cancelled' THEN 1 END) as cancelled_signals
                    FROM signals
                """)
                signal_stats = cur.fetchone()
                
                stats_text += f"📈 Signal Statistics:\n"
                stats_text += f"  - Active: {signal_stats['active_signals']}\n"
                stats_text += f"  - Closed: {signal_stats['closed_signals']}\n"
                stats_text += f"  - Cancelled: {signal_stats['cancelled_signals']}\n\n"
                    
                # Top Referrers
                cur.execute("""
                    SELECT user_id, referrals  
                    FROM users 
                    WHERE referrals > 0 
                    ORDER BY referrals DESC 
                    LIMIT 5
                """)
                top_referrers = cur.fetchall()
                
                if top_referrers:
                    stats_text += "🏆 Top 5 Referrers:\n"
                    for row in top_referrers:
                        stats_text += f"  - User {row['user_id']}: {row['referrals']} referrals\n"
                else:
                    stats_text += "🏆 No referrals yet\n"
                        
    except psycopg2.Error as db_error:
        logger.error(f"Database error retrieving admin stats: {db_error}")
        stats_text = "❌ Database error occurred while retrieving stats."
    except Exception as e:
        logger.error(f"Unexpected error retrieving admin stats: {e}")
        stats_text = "❌ Failed to retrieve stats. Check logs for details."
    
    if is_callback:
        await update.callback_query.message.reply_text(stats_text)
    else:
        await update.message.reply_text(stats_text)

# === Conversation Handler Registration ===
admin_upgrade_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(admin_upgrade_start, pattern="^admin_upgrade_flow$")],
    states={
        ADMIN_UPGRADE_DETAILS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, admin_upgrade_complete),
        ],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
)
