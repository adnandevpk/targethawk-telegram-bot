# start_commands.py
import os
import logging
import psycopg2
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import bot_commands
import signal_management  # Import the signal_management module

# Configure logging for this module
logger = logging.getLogger(__name__)

async def start_with_ref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /start command, registering new users and processing referrals.
    Sends a more engaging welcome message with inline buttons.
    """
    user_id = update.effective_user.id
    username = update.effective_user.username
    args = context.args
    now = datetime.utcnow()

    # Safely parse the referrer ID from the command arguments
    referrer_id = None
    if args and args[0].isdigit():
        try:
            referrer_id = int(args[0])
        except (ValueError, IndexError):
            logger.warning(f"Invalid referrer ID provided: '{args[0]}'")

    # Use the shared database connection function
    with bot_commands.get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, tier, trial_expiry FROM users WHERE user_id = %s", (user_id,))
            user = cur.fetchone()

            if not user:
                # This is a new user: insert them into the DB with a Pro Trial
                cur.execute(
                    "INSERT INTO users (user_id, username, tier, trial_expiry) VALUES (%s, %s, 'Pro Trial', %s)",
                    (user_id, username, now + timedelta(days=3))
                )
                conn.commit()

                if referrer_id and referrer_id != user_id:
                    # Check if the referral has already been recorded
                    cur.execute("SELECT 1 FROM referrals WHERE referred_id = %s", (user_id,))
                    referral_exists = cur.fetchone()

                    if not referral_exists:
                        # Record the referral and update the referrer's count
                        cur.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (%s, %s)", (referrer_id, user_id))
                        cur.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = %s RETURNING referrals, tier", (referrer_id,))
                        ref_info = cur.fetchone()
                        conn.commit()

                        if ref_info:
                            new_count = ref_info['referrals']
                            referrer_tier = ref_info['tier']
                            
                            # Send message to referrer
                            await context.bot.send_message(referrer_id, f"🎉 You received a new referral! You now have {new_count} referrals.")
                            
                            # Check for referral tier upgrades
                            if new_count == 3 and referrer_tier not in ['Pro', 'VIP']:
                                bot_commands.log_upgrade(referrer_id, 'Pro', 'Referral Bonus', expiry_days=30)
                                await context.bot.send_message(referrer_id, "🎁 Congrats! You've been upgraded to Pro for 1 month!")
                            elif new_count == 10 and referrer_tier != 'VIP':
                                bot_commands.log_upgrade(referrer_id, 'VIP', 'Referral Bonus')
                                await context.bot.send_message(referrer_id, "🏆 Amazing! You're now a VIP after 10 referrals!")
            else:
                # Existing user, just update their username if it's new
                cur.execute("UPDATE users SET username = %s WHERE user_id = %s", (username, user_id))
                conn.commit()
    
    # --- New Welcome Message Logic ---
    welcome_text = (
        "👋 Welcome to TargetHawkBot, your intelligent partner for tracking crypto signals!\n\n"
        "I'm here to help you monitor prices, get real-time alerts, and manage your trades with ease.\n\n"
        "Key Features:\n"
        "📈  **Track Signals:** Monitor entry, target, and stop-loss prices.\n"
        "🔔  **Instant Alerts:** Get notified when a price is hit.\n"
        "📊  **Performance Analytics:** See how your signals are performing."
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📊 My Signals", callback_data="show_signals_list"),
            InlineKeyboardButton("💰 Plans & Upgrade", callback_data="show_plans"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text=welcome_text,
        reply_markup=reply_markup
    )

async def show_plans_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback to show the plans menu."""
    query = update.callback_query
    await query.answer()
    
    text = "💰 Plans:\n🔹 Free: Track 1 signal, basic alerts\n🔸 Pro: $9.99/month - Track up to 10 signals, daily stats\n🏆 VIP: $49.99 one-time - Unlimited signals, full analytics"
    await query.edit_message_text(text)
    # Note: For full functionality, you should add buttons here
    # to link to the upgrade URLs, similar to the original /upgrade command.

async def show_signals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback to show the signals menu."""
    query = update.callback_query
    await query.answer()
    await signal_management.list_and_edit_signals(update, context)


