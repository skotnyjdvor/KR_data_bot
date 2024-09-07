from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import csv
from datetime import datetime
from utils import delete_message_with_retry, get_user, get_main_menu_keyboard
from states import AWAITING_CHOICE, EXPENSE_DESCRIPTION, EXPENSE_AMOUNT
import os

def get_cancel_keyboard():
    return ReplyKeyboardMarkup([['Cancel']], one_time_keyboard=True, resize_keyboard=True)

def get_user_expense_file(fullname):
    return f"{fullname} expenses.csv"

def create_expense_table(fullname):
    filename = get_user_expense_file(fullname)
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Date', 'Description', 'Amount'])
    return filename

async def start_expense_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("You need to register first. Please use the /start command.")
        return ConversationHandler.END

    fullname = user['fullname']
    filename = get_user_expense_file(fullname)
    
    if not os.path.exists(filename):
        create_expense_table(fullname)

    context.user_data['in_expense_tracking'] = True
    message = await update.message.reply_text("Please enter a description of the expense:", reply_markup=get_cancel_keyboard())
    context.user_data['last_message_id'] = message.message_id
    return EXPENSE_DESCRIPTION

async def get_expense_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        context.user_data['in_expense_tracking'] = False
        return await cancel_expense_tracking(update, context)
    
    description = update.message.text
    context.user_data['expense_description'] = description
    
    if 'last_message_id' in context.user_data:
        await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    
    message = await update.message.reply_text("Please enter the amount spent:", reply_markup=get_cancel_keyboard())
    context.user_data['last_message_id'] = message.message_id
    return EXPENSE_AMOUNT

async def get_expense_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        context.user_data['in_expense_tracking'] = False
        return await cancel_expense_tracking(update, context)
    
    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Please enter a valid number for the amount.")
        return EXPENSE_AMOUNT
    
    user = get_user(update.effective_user.id)
    fullname = user['fullname']
    description = context.user_data.get('expense_description', 'No description')
    
    filename = get_user_expense_file(fullname)
    
    with open(filename, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), description, amount])
    
    if 'last_message_id' in context.user_data:
        await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    
    await update.message.reply_text(f"Expense recorded: {description} - {amount}")
    await update.message.reply_text("What would you like to do next?", reply_markup=get_main_menu_keyboard())
    
    context.user_data['in_expense_tracking'] = False
    return AWAITING_CHOICE

async def cancel_expense_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['in_expense_tracking'] = False
    await update.message.reply_text("Expense tracking cancelled.", reply_markup=get_main_menu_keyboard())
    return AWAITING_CHOICE