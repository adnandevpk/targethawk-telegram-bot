# user_commands.py

import os
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import bot_commands # Assuming this contains get_db_conn()

# Set up logging for this module
logger = logging.getLogger(__name__)

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Informs the user about available subscription plans."""
    text = "💰 Plans:\n🔹 Free: Track 1 signal, basic alerts\n🔸 Pro: $9.99/month - Track up to 10 signals, daily stats\n🏆 VIP: $49.99 one-time - Unlimited signals, full analytics"
    await update.message.reply_text(text)

async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides inline keyboard buttons for payment options."""
    kb = [
        [InlineKeyboardButton("Pay with Stripe", url="https://yourdomain.com/pay/stripe")],
        [InlineKeyboardButton("Pay with Crypto", url="https://yourdomain.com/pay/crypto")]
    ]
    await update.message.reply_text("🔐 Upgrade your plan:", reply_markup=InlineKeyboardMarkup(kb))

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides the user with their unique referral link."""
    user_id = update.effective_user.id
    with bot_commands.get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT referrals, tier FROM users WHERE user_id = %s", (user_id,))
            user = cur.fetchone()
            if not user:
                # Handle unregistered user gracefully
                await update.message.reply_text("❌ You are not registered. Please use /start first.")
                return

            referrals = user['referrals']
            tier = user['tier']

    link = f"https://t.me/TargetHwakBot?start={user_id}"
    await update.message.reply_text(
        f"🎁 Referral Program\n"
        f"Your link: {link}\n"
        f"Referrals: {referrals}\n"
        f"🎯 {referrals}/3 for Pro • {referrals}/10 for VIP\n"
        f"Invite 3 → 1 month Pro\n"
        f"Invite 10 → VIP Lifetime 💎\n"
        f"Current Plan: {tier}"
    )
    
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the user's current plan and active signals."""
    user_id = update.effective_user.id
    now = datetime.utcnow()
    with bot_commands.get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT tier, trial_expiry FROM users WHERE user_id = %s", (user_id,))
            user = cur.fetchone()
            if not user:
                await update.message.reply_text("❌ You are not registered.")
                return
            tier = user['tier']
            expiry = user['trial_expiry']

            cur.execute("SELECT COUNT(*) FROM signals WHERE user_id = %s AND status = 'active'", (user_id,))
            active_signals_count = cur.fetchone()['count']

            msg = f"📊 Plan: {tier}\n"
            if expiry:
                days_left = max((expiry - now).days, 0)
                msg += f"⏳ Trial expires in {days_left} day(s)\n"
            msg += f"📈 Active Signals: {active_signals_count}"
    await update.message.reply_text(msg)

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the top 10 users by referral count."""
    with bot_commands.get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, username, referrals FROM users ORDER BY referrals DESC LIMIT 10")
            top = cur.fetchall()

    lines = ["🏆 Top Referrers"]
    for i, row in enumerate(top, 1):
        name = f"@{row['username']}" if row['username'] else f"ID: {row['user_id']}"
        lines.append(f"{i}. {name} – {row['referrals']} referrals")
    await update.message.reply_text("\n".join(lines))
