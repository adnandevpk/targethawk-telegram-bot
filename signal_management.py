# signal_management.py
import os
import logging
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
)
from datetime import datetime, timedelta
# Import database connection from your main file
import bot_commands 

logger = logging.getLogger(__name__)

# === States for ConversationHandler ===
EDIT_SIGNAL, EDIT_FIELD, EDIT_VALUE = range(3)
DELETE_SIGNAL, DELETE_CONFIRM = range(2)

# === Callback Query Handlers for the Main Menu ===

async def handle_signals_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the user's selection from the /signals menu."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "add_new_signal":
        await query.edit_message_text("Use the /track command to add a new signal.")
        return
        
    elif query.data == "show_signals_list":
        await list_and_edit_signals(update, context)
        return
        
    elif query.data == "delete_signals":
        await start_delete_flow(update, context)
        return
    
# === Edit Signal Conversation Flow ===

async def list_and_edit_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists signals and prompts for editing."""
    user_id = update.effective_user.id
    signals = await bot_commands.list_user_signals(user_id)
    
    if not signals:
        await update.callback_query.edit_message_text("You have no signals to edit.")
        return ConversationHandler.END
        
    keyboard = [[InlineKeyboardButton(f"🆔 {s[0]} | 📈 {s[1]} | Status: {s[2]}", callback_data=str(s[0]))] for s in signals]
    keyboard.append([InlineKeyboardButton("🔙 Back to menu", callback_data="cancel_edit")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text("Choose a signal to edit:", reply_markup=reply_markup)
    return EDIT_SIGNAL

async def select_signal_to_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompts for field to edit after a signal is selected."""
    query = update.callback_query
    await query.answer()
    
    signal_id = int(query.data)
    context.user_data['signal_id'] = signal_id
    
    keyboard = [
        ["symbol", "entry_price", "target_price_1"],
        ["target_price_2", "target_price_3", "stop_loss"],
        ["tags", "cancel"]
    ]
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(text, callback_data=text) for text in row] for row in keyboard
    ])
    
    await query.edit_message_text(f"⚙️ Which field of signal {signal_id} would you like to edit?", reply_markup=reply_markup)
    return EDIT_FIELD

async def select_field_to_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompts for the new value of the selected field."""
    query = update.callback_query
    await query.answer()
    
    field_to_edit = query.data
    context.user_data['field_to_edit'] = field_to_edit
    
    if field_to_edit == 'cancel':
        await query.edit_message_text("✅ Edit cancelled.")
        return ConversationHandler.END
        
    await query.edit_message_text(f"✍️ Please send the new value for '{field_to_edit}'.")
    return EDIT_VALUE

async def update_signal_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Updates the signal in the database and ends the conversation."""
    new_value = update.message.text
    signal_id = context.user_data['signal_id']
    field_to_edit = context.user_data['field_to_edit']
    
    try:
        # Simple validation for numerical fields
        if field_to_edit in ['entry_price', 'target_price_1', 'target_price_2', 'target_price_3', 'stop_loss']:
            new_value = float(new_value)

        with bot_commands.get_db_conn() as conn:
            with conn.cursor() as cur:
                query = f"UPDATE signals SET {field_to_edit} = %s WHERE id = %s"
                cur.execute(query, (new_value, signal_id))
            conn.commit()

        await update.message.reply_text(f"✅ Successfully updated signal {signal_id}'s {field_to_edit} to '{new_value}'.")
    except ValueError:
        await update.message.reply_text("❌ Invalid input. Please enter a valid number for this field.")
    except Exception as e:
        logger.error(f"Failed to update signal: {e}")
        await update.message.reply_text("❌ An error occurred while updating the signal.")
    finally:
        context.user_data.clear()
        return ConversationHandler.END

# === Delete Signal Conversation Flow ===

async def start_delete_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists signals for deletion and allows multi-selection."""
    user_id = update.effective_user.id
    signals = await bot_commands.list_user_signals(user_id)
    
    if not signals:
        await update.callback_query.edit_message_text("You have no signals to delete.")
        return ConversationHandler.END
        
    context.user_data['signals_to_delete'] = []
    
    keyboard = [[InlineKeyboardButton(f"🗑️ {s[1]}", callback_data=f"delete_{s[0]}") for s in signals]]
    keyboard.append([InlineKeyboardButton("✅ Confirm Deletion", callback_data="confirm_delete"),
                     InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text("Select signals to delete. Use the confirm button when you are done.", reply_markup=reply_markup)
    return DELETE_SIGNAL

async def handle_delete_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adds/removes a signal from the deletion list."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("delete_"):
        signal_id = int(data.split('_')[1])
        if signal_id in context.user_data['signals_to_delete']:
            context.user_data['signals_to_delete'].remove(signal_id)
        else:
            context.user_data['signals_to_delete'].append(signal_id)
        
        selected_ids = context.user_data['signals_to_delete']
        new_text = f"Selected signals for deletion: {selected_ids}\n\nSelect more or confirm."
        await query.edit_message_text(new_text, reply_markup=query.message.reply_markup)
        
    elif data == "confirm_delete":
        await confirm_delete(update, context)
        return ConversationHandler.END
    elif data == "cancel_delete":
        await query.edit_message_text("✅ Deletion cancelled.")
        return ConversationHandler.END
        
    return DELETE_SIGNAL

async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deletes selected signals from the database."""
    signals_to_delete = context.user_data.get('signals_to_delete', [])
    if not signals_to_delete:
        await update.callback_query.edit_message_text("❌ No signals were selected for deletion.")
        return
        
    user_id = update.effective_user.id
    try:
        with bot_commands.get_db_conn() as conn:
            with conn.cursor() as cur:
                # Ensure the user owns the signals before deleting
                cur.execute("DELETE FROM signals WHERE user_id = %s AND id IN %s", (user_id, tuple(signals_to_delete)))
            conn.commit()
        
        await update.callback_query.edit_message_text(f"✅ Successfully deleted {len(signals_to_delete)} signals.")
    except Exception as e:
        logger.error(f"Failed to delete signals: {e}")
        await update.callback_query.edit_message_text("❌ An error occurred during deletion.")
    finally:
        context.user_data.clear()
        return

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ends any active conversation."""
    await update.message.reply_text("✅ Operation cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

# === Conversation Handlers ===

edit_signal_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(list_and_edit_signals, pattern="^show_signals_list$")],
    states={
        EDIT_SIGNAL: [CallbackQueryHandler(select_signal_to_edit, pattern="^\d+$")],
        EDIT_FIELD: [CallbackQueryHandler(select_field_to_edit)],
        EDIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_signal_value)]
    },
    fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_edit$")],
)

delete_signal_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_delete_flow, pattern="^delete_signals$")],
    states={
        DELETE_SIGNAL: [CallbackQueryHandler(handle_delete_selection)]
    },
    fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_delete$")],
)
