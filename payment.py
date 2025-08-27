from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "💰 Plans:\n🔹 Free: 1 signal\n🔸 Pro: $9.99/month\n🏆 VIP: $49.99 lifetime"
    await update.message.reply_text(text)

async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("Pay with Stripe", url="https://yourdomain.com/pay/stripe")],
        [InlineKeyboardButton("Pay with Crypto", url="https://yourdomain.com/pay/crypto")]
    ]
    await update.message.reply_text("🔐 Upgrade your plan:", reply_markup=InlineKeyboardMarkup(kb))
