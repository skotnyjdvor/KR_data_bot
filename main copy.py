import asyncio
import pandas as pd
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, ContextTypes
from telegram.ext import filters
from telegram.error import NetworkError, TelegramError
import httpx

# Определяем состояния разговора
FULLNAME, AWAITING_CHOICE, PILOT_NAME, SESSION_NUMBER, CHASSIS_NUMBER, TIRE_PRESSURE, TIRE_CONDITION, LAP_TIME = range(8)

# Определение типов столбцов
column_types = {
    'user_id': 'int64',
    'mechanic': 'str',
    'timestamp': 'str',
    'pilot_name': 'str',
    'session_number': 'str',
    'chassis_number': 'str',
    'tire_pressure': 'str',
    'tire_condition': 'str',
    'lap_time': 'str'
}

def get_main_menu_keyboard():
    keyboard = [
        ['Training Session'],
        ['Help']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        df = pd.read_excel('mechanics.xlsx', dtype=column_types)
        if 'user_id' in df.columns and user_id in df['user_id'].values:
            mechanic = df[df['user_id'] == user_id]['mechanic'].values[0]
            context.user_data['user_id'] = user_id
            context.user_data['mechanic'] = mechanic
            await update.message.reply_text(f"Welcome back, {mechanic}!", reply_markup=get_main_menu_keyboard())
            return AWAITING_CHOICE
    except FileNotFoundError:
        df = pd.DataFrame(columns=column_types.keys()).astype(column_types)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        await update.message.reply_text("An error occurred. Please try again later.")
        return ConversationHandler.END
    
    await update.message.reply_text("Hello! Please enter your full name:")
    return FULLNAME

async def get_fullname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    full_name = update.message.text
    user_id = update.effective_user.id
    try:
        df = pd.read_excel('mechanics.xlsx', dtype=column_types)
    except FileNotFoundError:
        df = pd.DataFrame(columns=column_types.keys()).astype(column_types)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        df = pd.DataFrame(columns=column_types.keys()).astype(column_types)

    new_row = pd.DataFrame({'user_id': [user_id], 'mechanic': [full_name]})
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_excel('mechanics.xlsx', index=False)

    context.user_data['user_id'] = user_id
    context.user_data['mechanic'] = full_name

    await update.message.reply_text(
        f"Thank you, {full_name}! Your information has been saved.",
        reply_markup=get_main_menu_keyboard()
    )
    return AWAITING_CHOICE

async def handle_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice == 'Training Session':
        return await start_training_session(update, context)
    elif choice == 'Help':
        await update.message.reply_text("This bot helps you record training sessions. Use the 'Training Session' option to start.")
        return AWAITING_CHOICE
    else:
        await update.message.reply_text("Invalid option. Please use the provided buttons.")
        return AWAITING_CHOICE

async def start_training_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mechanic = context.user_data.get('mechanic', 'Unknown')
    
    # Create a new row in the DataFrame
    new_row = pd.DataFrame({
        'user_id': [user_id],
        'mechanic': [mechanic],
        'timestamp': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        'pilot_name': [''],
        'session_number': [''],
        'chassis_number': [''],
        'tire_pressure': [''],
        'tire_condition': [''],
        'lap_time': ['']
    })
    
    # Save the new row to the Excel file
    try:
        df = pd.read_excel('mechanics.xlsx', dtype=column_types)
    except FileNotFoundError:
        df = pd.DataFrame(columns=column_types.keys()).astype(column_types)
    
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_excel('mechanics.xlsx', index=False)
    
    # Store the index of the new row in context.user_data
    context.user_data['current_row'] = len(df) - 1
    
    message = await update.message.reply_text("Please enter the pilot's full name:")
    context.user_data['last_message_id'] = message.message_id
    return PILOT_NAME

async def delete_message_with_retry(context, chat_id, message_id, max_retries=3):
    for attempt in range(max_retries):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            return
        except NetworkError as e:
            if attempt == max_retries - 1:
                print(f"Failed to delete message after {max_retries} attempts: {e}")
            else:
                await asyncio.sleep(1)  # Wait for 1 second before retrying

async def send_message_with_retry(context, chat_id, text, max_retries=3):
    for attempt in range(max_retries):
        try:
            message = await context.bot.send_message(chat_id=chat_id, text=text)
            return message
        except NetworkError as e:
            if attempt == max_retries - 1:
                print(f"Failed to send message after {max_retries} attempts: {e}")
                return None
            else:
                await asyncio.sleep(1)  # Wait for 1 second before retrying

async def get_pilot_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pilot_name = update.message.text
    row_index = context.user_data['current_row']
    
    # Update the Excel file
    df = pd.read_excel('mechanics.xlsx', dtype=column_types)
    df.at[row_index, 'pilot_name'] = pilot_name
    df.to_excel('mechanics.xlsx', index=False)
    
    # Delete the previous message
    await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    
    # Delete user's message
    await delete_message_with_retry(context, update.effective_chat.id, update.message.message_id)
    
    # Send new message and store its ID
    message = await send_message_with_retry(context, update.effective_chat.id, "Enter the session number:")
    if message:
        context.user_data['last_message_id'] = message.message_id
    
    await asyncio.sleep(0.5)  # Add a small delay
    return SESSION_NUMBER

async def get_session_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session_number = update.message.text
    row_index = context.user_data['current_row']
    
    # Update the Excel file
    df = pd.read_excel('mechanics.xlsx', dtype=column_types)
    df.at[row_index, 'session_number'] = session_number
    df.to_excel('mechanics.xlsx', index=False)
    
    # Delete the previous message
    await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    
    # Delete user's message
    await delete_message_with_retry(context, update.effective_chat.id, update.message.message_id)
    
    # Send new message and store its ID
    message = await send_message_with_retry(context, update.effective_chat.id, "Enter the chassis number:")
    if message:
        context.user_data['last_message_id'] = message.message_id
    
    await asyncio.sleep(0.5)  # Add a small delay
    return CHASSIS_NUMBER

async def get_chassis_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chassis_number = update.message.text
    row_index = context.user_data['current_row']
    
    # Update the Excel file
    df = pd.read_excel('mechanics.xlsx', dtype=column_types)
    df.at[row_index, 'chassis_number'] = chassis_number
    df.to_excel('mechanics.xlsx', index=False)
    
    # Delete the previous message
    await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    
    # Delete user's message
    await delete_message_with_retry(context, update.effective_chat.id, update.message.message_id)
    
    # Send new message and store its ID
    message = await send_message_with_retry(context, update.effective_chat.id, "Enter the tire pressure:")
    if message:
        context.user_data['last_message_id'] = message.message_id
    
    await asyncio.sleep(0.5)  # Add a small delay
    return TIRE_PRESSURE

async def get_tire_pressure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tire_pressure = update.message.text
    row_index = context.user_data['current_row']
    
    # Update the Excel file
    df = pd.read_excel('mechanics.xlsx', dtype=column_types)
    df.at[row_index, 'tire_pressure'] = tire_pressure
    df.to_excel('mechanics.xlsx', index=False)
    
    # Delete the previous message
    await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    
    # Delete user's message
    await delete_message_with_retry(context, update.effective_chat.id, update.message.message_id)
    
    # Send new message and store its ID
    message = await send_message_with_retry(context, update.effective_chat.id, "Enter the tire condition (e.g., new, used, worn):")
    if message:
        context.user_data['last_message_id'] = message.message_id
    
    await asyncio.sleep(0.5)  # Add a small delay
    return TIRE_CONDITION

async def get_tire_condition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tire_condition = update.message.text
    row_index = context.user_data['current_row']
    
    # Update the Excel file
    df = pd.read_excel('mechanics.xlsx', dtype=column_types)
    df.at[row_index, 'tire_condition'] = tire_condition
    df.to_excel('mechanics.xlsx', index=False)
    
    # Delete the previous message
    await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    
    # Delete user's message
    await delete_message_with_retry(context, update.effective_chat.id, update.message.message_id)
    
    # Send new message and store its ID
    message = await send_message_with_retry(context, update.effective_chat.id, "Enter the lap time:")
    if message:
        context.user_data['last_message_id'] = message.message_id
    
    await asyncio.sleep(0.5)  # Add a small delay
    return LAP_TIME

async def get_lap_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lap_time = update.message.text
    row_index = context.user_data['current_row']
    
    # Update the Excel file
    df = pd.read_excel('mechanics.xlsx', dtype=column_types)
    df.at[row_index, 'lap_time'] = lap_time
    df.to_excel('mechanics.xlsx', index=False)
    
    # Delete the previous message
    await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    
    # Delete user's message
    await delete_message_with_retry(context, update.effective_chat.id, update.message.message_id)
    
    # Get all the data for the final message
    session_data = df.iloc[row_index]
    
    await update.message.reply_text(
        f"Training session data recorded:\n"
        f"Pilot: {session_data['pilot_name']}\n"
        f"Session: {session_data['session_number']}\n"
        f"Chassis: {session_data['chassis_number']}\n"
        f"Tire Pressure: {session_data['tire_pressure']}\n"
        f"Tire Condition: {session_data['tire_condition']}\n"
        f"Lap Time: {session_data['lap_time']}"
    )
    return AWAITING_CHOICE

async def main() -> None:
    application = Application.builder().token("7154116674:AAHzyP00px9R_IhqDM3HBtrMMmYzrY8oZf4").build()

    # Increase the connection pool size and timeout
    application.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=20, read=20, write=20, pool=5),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FULLNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fullname)],
            AWAITING_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_choice)],
            PILOT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_pilot_name)],
            SESSION_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_session_number)],
            CHASSIS_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_chassis_number)],
            TIRE_PRESSURE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tire_pressure)],
            TIRE_CONDITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tire_condition)],
            LAP_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_lap_time)],
        },
        fallbacks=[]
    )

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        lambda update, context: update.message.reply_text("Please use the provided buttons.")
    ))

    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    print("Bot is running. Press Ctrl+C to stop.")

    # Run the bot until you press Ctrl-C
    while True:
        try:
            await asyncio.sleep(1)
        except KeyboardInterrupt:
            break

    # Gracefully stop the bot
    await application.stop()
    await application.shutdown()

if __name__ == '__main__':
    asyncio.run(main())
