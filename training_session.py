from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
import pandas as pd
from datetime import datetime, date
from utils import delete_message_with_retry, send_message_with_retry, column_types, read_excel_safe, get_main_menu_keyboard, get_user
import asyncio
from states import AWAITING_CHOICE

AWAITING_CHOICE, SESSION_CHOICE, EDIT_SESSION_CHOICE, EDIT_FIELD_CHOICE, EDIT_FIELD_VALUE, PILOT_CONFIRM, PILOT_NAME, CLASS_CONFIRM, CLASS_NAME, SESSION_NUMBER, CHASSIS_CONFIRM, CHASSIS_NUMBER, SPROCKET_CONFIRM, SPROCKET_RATIO, TIRE_PRESSURE, TIRE_CONDITION, LAP_TIME, SECOND_CHASSIS, CHASSIS_NUMBER_2, SPROCKET_RATIO_2, TIRE_PRESSURE_2, TIRE_CONDITION_2, LAP_TIME_2 = range(1, 24)

def get_cancel_keyboard():
    return ReplyKeyboardMarkup([['Cancel']], one_time_keyboard=True, resize_keyboard=True)

def get_yes_no_keyboard():
    return ReplyKeyboardMarkup([['Yes', 'No']], one_time_keyboard=True, resize_keyboard=True)

def get_class_keyboard():
    return ReplyKeyboardMarkup([['OK', 'OKJ'], ['KZ', 'KZ2']], one_time_keyboard=True, resize_keyboard=True)

async def start_training_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("You need to register first. Please use the /start command.")
        return ConversationHandler.END

    mechanic = user['fullname']
    context.user_data['mechanic'] = mechanic

    keyboard = ReplyKeyboardMarkup([['New', 'Edit']], one_time_keyboard=True, resize_keyboard=True)
    message = await update.message.reply_text("Would you like to start a new session or edit an existing one?", reply_markup=keyboard)
    context.user_data['last_message_id'] = message.message_id
    return SESSION_CHOICE

async def handle_session_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    if choice == 'New':
        return await start_new_session(update, context)
    elif choice == 'Edit':
        return await list_today_sessions(update, context)
    else:
        await update.message.reply_text("Invalid choice. Please select 'New' or 'Edit'.")
        return SESSION_CHOICE

async def start_new_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mechanic = context.user_data.get('mechanic', 'Unknown')
    
    df = read_excel_safe('mechanics.xlsx')
    mechanic_rows = df[df['mechanic'] == mechanic]
    
    if len(mechanic_rows) > 0:
        last_pilot = mechanic_rows['pilot_name'].iloc[-1]
        if pd.notna(last_pilot):
            message = await update.message.reply_text(f"Is the pilot still {last_pilot}?", reply_markup=get_yes_no_keyboard())
            context.user_data['last_pilot'] = last_pilot
            context.user_data['last_message_id'] = message.message_id
            return PILOT_CONFIRM
    
    return await ask_pilot_name(update, context)

async def list_today_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    df = read_excel_safe('mechanics.xlsx')
    today = date.today().strftime("%Y-%m-%d")
    
    # Убедимся, что столбец 'timestamp' содержит строки
    df['timestamp'] = df['timestamp'].astype(str)
    
    # Фильтруем сессии за сегодня
    today_sessions = df[df['timestamp'].str.startswith(today)]
    
    if today_sessions.empty:
        await update.message.reply_text("No sessions recorded today.")
        return await start_training_session(update, context)
    
    # Создаем список сессий, обрабатывая возможные NaN значения
    session_list = today_sessions.apply(lambda row: f"{row['timestamp']} - {row['pilot_name'] if pd.notna(row['pilot_name']) else 'Unknown'} ({row['kart_class'] if pd.notna(row['kart_class']) else 'Unknown'})", axis=1).tolist()
    
    keyboard = ReplyKeyboardMarkup([[session] for session in session_list] + [['Cancel']], one_time_keyboard=True, resize_keyboard=True)
    
    message = await update.message.reply_text("Select a session to edit:", reply_markup=keyboard)
    context.user_data['last_message_id'] = message.message_id
    context.user_data['today_sessions'] = today_sessions
    return EDIT_SESSION_CHOICE

# ... (предыдущий код остается без изменений)

async def handle_edit_session_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.user_data.get('in_expense_tracking'):
        # If we're in expense tracking, we should not be here
        await update.message.reply_text("Invalid operation. Returning to main menu.", reply_markup=get_main_menu_keyboard())
        return AWAITING_CHOICE

    if 'today_sessions' not in context.user_data or not context.user_data['today_sessions']:
        await update.message.reply_text("No sessions available to edit. Please create a new session first.")
        return await start_training_session(update, context)

    today_sessions = context.user_data['today_sessions']
    choice = update.message.text
    
    try:
        session_index = int(choice) - 1
        if 0 <= session_index < len(today_sessions):
            context.user_data['editing_session'] = today_sessions[session_index]
            return await edit_session(update, context)
        else:
            await update.message.reply_text("Invalid choice. Please select a valid session number.")
            return EDIT_SESSION_CHOICE
    except ValueError:
        # If the input is not a number, it might be a main menu choice
        return await handle_menu_choice(update, context)

async def edit_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    session = context.user_data['editing_session']
    message = "Current session details:\n\n"
    for key, value in session.items():
        if key != 'timestamp' and key != 'mechanic':
            message += f"{key}: {value}\n"
    
    message += "\nWhich field would you like to edit?"
    await update.message.reply_text(message)
    return EDIT_FIELD_CHOICE

async def handle_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    if choice == 'Training Session':
        return await start_training_session(update, context)
    elif choice == 'Expenses':
        from expenses import start_expense_tracking
        return await start_expense_tracking(update, context)
    elif choice == 'Help':
        await update.message.reply_text("This is a help message. You can add more detailed instructions here.")
        await update.message.reply_text("What would you like to do next?", reply_markup=get_main_menu_keyboard())
        return AWAITING_CHOICE
    else:
        await update.message.reply_text("Invalid choice. Please select an option from the menu.", reply_markup=get_main_menu_keyboard())
        return AWAITING_CHOICE

# ... (остальной код остается без изменений)

async def handle_edit_field_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice == 'Cancel':
        await update.message.reply_text("Editing cancelled.", reply_markup=get_main_menu_keyboard())
        return AWAITING_CHOICE
    
    context.user_data['editing_field'] = choice
    current_value = context.user_data['editing_session'][choice]
    
    message = await update.message.reply_text(f"Current value of {choice}: {current_value}\nEnter new value:", reply_markup=get_cancel_keyboard())
    context.user_data['last_message_id'] = message.message_id
    return EDIT_FIELD_VALUE

async def handle_edit_field_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        await update.message.reply_text("Editing cancelled.", reply_markup=get_main_menu_keyboard())
        return AWAITING_CHOICE
    
    new_value = update.message.text
    field = context.user_data['editing_field']
    session = context.user_data['editing_session']
    
    df = read_excel_safe('mechanics.xlsx')
    df.loc[(df['timestamp'] == session['timestamp']) & (df['pilot_name'] == session['pilot_name']), field] = new_value
    df.to_excel('mechanics.xlsx', index=False)
    
    await update.message.reply_text(f"Updated {field} to: {new_value}")
    return await list_today_sessions(update, context)

async def confirm_pilot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        return await cancel_training_session(update, context)
    
    if update.message.text.lower() == 'yes':
        pilot_name = context.user_data['last_pilot']
        context.user_data['pilot_name'] = pilot_name
        return await ask_class(update, context)
    else:
        return await ask_pilot_name(update, context)

async def ask_pilot_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'last_message_id' in context.user_data:
        await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    message = await update.message.reply_text("Please enter the pilot's full name:", reply_markup=get_cancel_keyboard())
    context.user_data['last_message_id'] = message.message_id
    return PILOT_NAME

async def get_pilot_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        return await cancel_training_session(update, context)
    
    pilot_name = update.message.text
    context.user_data['pilot_name'] = pilot_name
    return await ask_class(update, context)

async def ask_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mechanic = context.user_data.get('mechanic', 'Unknown')
    df = read_excel_safe('mechanics.xlsx')
    mechanic_rows = df[df['mechanic'] == mechanic]
    
    if len(mechanic_rows) > 0:
        last_class = mechanic_rows['kart_class'].iloc[-1] if 'kart_class' in mechanic_rows.columns else None
        if pd.notna(last_class):
            message = await update.message.reply_text(f"Is the class still {last_class}?", reply_markup=get_yes_no_keyboard())
            context.user_data['last_class'] = last_class
            context.user_data['last_message_id'] = message.message_id
            return CLASS_CONFIRM
    
    return await ask_class_name(update, context)

async def confirm_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        return await cancel_training_session(update, context)
    
    if update.message.text.lower() == 'yes':
        class_name = context.user_data['last_class']
        context.user_data['kart_class'] = class_name
        return await create_session(update, context)
    else:
        return await ask_class_name(update, context)

async def ask_class_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'last_message_id' in context.user_data:
        await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    message = await update.message.reply_text("Please select the class:", reply_markup=get_class_keyboard())
    context.user_data['last_message_id'] = message.message_id
    return CLASS_NAME

async def get_class_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        return await cancel_training_session(update, context)
    
    class_name = update.message.text
    if class_name not in ['OK', 'OKJ', 'KZ', 'KZ2']:
        message = await update.message.reply_text("Invalid class. Please select a valid class:", reply_markup=get_class_keyboard())
        context.user_data['last_message_id'] = message.message_id
        return CLASS_NAME
    
    context.user_data['kart_class'] = class_name
    return await create_session(update, context)

async def create_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mechanic = context.user_data.get('mechanic', 'Unknown')
    pilot_name = context.user_data.get('pilot_name', 'Unknown')
    kart_class = context.user_data.get('kart_class', 'Unknown')
    
    new_row = pd.DataFrame({
        'user_id': [user_id],
        'mechanic': [mechanic],
        'timestamp': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        'pilot_name': [pilot_name],
        'kart_class': [kart_class],
        'session_number': [''],
        'chassis_number': [''],
        'sprocket_ratio': [''],
        'tire_pressure': [''],
        'tire_condition': [''],
        'lap_time': [''],
        'chassis_number_2': [''],
        'sprocket_ratio_2': [''],
        'tire_pressure_2': [''],
        'tire_condition_2': [''],
        'lap_time_2': ['']
    })
    
    df = read_excel_safe('mechanics.xlsx')
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_excel('mechanics.xlsx', index=False)
    
    context.user_data['current_row'] = len(df) - 1
    
    await delete_message_with_retry(context, update.effective_chat.id, context.user_data.get('last_message_id'))
    message = await update.message.reply_text("Enter the session number:", reply_markup=get_cancel_keyboard())
    context.user_data['last_message_id'] = message.message_id
    return SESSION_NUMBER

async def get_session_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        return await cancel_training_session(update, context)
    
    session_number = update.message.text
    row_index = context.user_data['current_row']
    
    df = read_excel_safe('mechanics.xlsx')
    df.at[row_index, 'session_number'] = session_number
    df.to_excel('mechanics.xlsx', index=False)
    
    await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    await delete_message_with_retry(context, update.effective_chat.id, update.message.message_id)
    
    # Check if there's a previous chassis number
    mechanic = context.user_data.get('mechanic', 'Unknown')
    mechanic_rows = df[df['mechanic'] == mechanic]
    if len(mechanic_rows) > 1:
        last_chassis = mechanic_rows['chassis_number'].iloc[-2]
        if pd.notna(last_chassis):
            message = await update.message.reply_text(f"Is the chassis number still {last_chassis}?", reply_markup=get_yes_no_keyboard())
            context.user_data['last_chassis'] = last_chassis
            context.user_data['last_message_id'] = message.message_id
            return CHASSIS_CONFIRM
    
    return await ask_chassis_number(update, context)

async def confirm_chassis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        return await cancel_training_session(update, context)
    
    if update.message.text.lower() == 'yes':
        chassis_number = context.user_data['last_chassis']
        row_index = context.user_data['current_row']
        df = read_excel_safe('mechanics.xlsx')
        df.at[row_index, 'chassis_number'] = chassis_number
        df.to_excel('mechanics.xlsx', index=False)
        return await ask_sprocket_ratio(update, context)
    else:
        return await ask_chassis_number(update, context)

async def ask_chassis_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'last_message_id' in context.user_data:
        await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    message = await update.message.reply_text("Enter the chassis number:", reply_markup=get_cancel_keyboard())
    context.user_data['last_message_id'] = message.message_id
    return CHASSIS_NUMBER

async def get_chassis_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        return await cancel_training_session(update, context)
    
    chassis_number = update.message.text
    row_index = context.user_data['current_row']
    
    df = read_excel_safe('mechanics.xlsx')
    df.at[row_index, 'chassis_number'] = chassis_number
    df.to_excel('mechanics.xlsx', index=False)
    
    await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    await delete_message_with_retry(context, update.effective_chat.id, update.message.message_id)
    
    return await ask_sprocket_ratio(update, context)

async def ask_sprocket_ratio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mechanic = context.user_data.get('mechanic', 'Unknown')
    df = read_excel_safe('mechanics.xlsx')
    mechanic_rows = df[df['mechanic'] == mechanic]
    
    if len(mechanic_rows) > 1:
        last_sprocket = mechanic_rows['sprocket_ratio'].iloc[-2]
        if pd.notna(last_sprocket):
            message = await update.message.reply_text(f"Is the sprocket ratio still {last_sprocket}?", reply_markup=get_yes_no_keyboard())
            context.user_data['last_sprocket'] = last_sprocket
            context.user_data['last_message_id'] = message.message_id
            return SPROCKET_CONFIRM
    
    message = await update.message.reply_text("Enter the sprocket ratio:", reply_markup=get_cancel_keyboard())
    context.user_data['last_message_id'] = message.message_id
    return SPROCKET_RATIO

async def confirm_sprocket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        return await cancel_training_session(update, context)
    
    if update.message.text.lower() == 'yes':
        sprocket_ratio = context.user_data['last_sprocket']
        row_index = context.user_data['current_row']
        df = read_excel_safe('mechanics.xlsx')
        df.at[row_index, 'sprocket_ratio'] = sprocket_ratio
        df.to_excel('mechanics.xlsx', index=False)
        return await ask_tire_pressure(update, context)
    else:
        return await ask_sprocket_ratio(update, context)

async def get_sprocket_ratio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        return await cancel_training_session(update, context)
    
    sprocket_ratio = update.message.text
    row_index = context.user_data['current_row']
    
    df = read_excel_safe('mechanics.xlsx')
    df.at[row_index, 'sprocket_ratio'] = sprocket_ratio
    df.to_excel('mechanics.xlsx', index=False)
    
    await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    await delete_message_with_retry(context, update.effective_chat.id, update.message.message_id)
    
    return await ask_tire_pressure(update, context)

async def ask_tire_pressure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = await update.message.reply_text("Enter the tire pressure:", reply_markup=get_cancel_keyboard())
    context.user_data['last_message_id'] = message.message_id
    return TIRE_PRESSURE

async def get_tire_pressure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        return await cancel_training_session(update, context)
    
    tire_pressure = update.message.text
    row_index = context.user_data['current_row']
    
    df = read_excel_safe('mechanics.xlsx')
    df.at[row_index, 'tire_pressure'] = tire_pressure
    df.to_excel('mechanics.xlsx', index=False)
    
    await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    await delete_message_with_retry(context, update.effective_chat.id, update.message.message_id)
    
    message = await send_message_with_retry(context, update.effective_chat.id, "Enter the tire condition (e.g., new, used, worn):", reply_markup=get_cancel_keyboard())
    if message:
        context.user_data['last_message_id'] = message.message_id
    await asyncio.sleep(0.5)
    return TIRE_CONDITION

async def get_tire_condition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        return await cancel_training_session(update, context)
    
    tire_condition = update.message.text
    row_index = context.user_data['current_row']
    
    df = read_excel_safe('mechanics.xlsx')
    df.at[row_index, 'tire_condition'] = tire_condition
    df.to_excel('mechanics.xlsx', index=False)
    
    await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    await delete_message_with_retry(context, update.effective_chat.id, update.message.message_id)
    
    message = await send_message_with_retry(context, update.effective_chat.id, "Enter the lap time:", reply_markup=get_cancel_keyboard())
    if message:
        context.user_data['last_message_id'] = message.message_id
    await asyncio.sleep(0.5)
    return LAP_TIME

async def get_lap_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        return await cancel_training_session(update, context)
    
    lap_time = update.message.text
    row_index = context.user_data['current_row']
    
    df = read_excel_safe('mechanics.xlsx')
    df.at[row_index, 'lap_time'] = lap_time
    df.to_excel('mechanics.xlsx', index=False)
    
    await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    await delete_message_with_retry(context, update.effective_chat.id, update.message.message_id)
    
    message = await update.message.reply_text("Was a second chassis used in this session?", reply_markup=get_yes_no_keyboard())
    context.user_data['last_message_id'] = message.message_id
    return SECOND_CHASSIS

async def handle_second_chassis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        return await cancel_training_session(update, context)
    
    if update.message.text.lower() == 'yes':
        message = await update.message.reply_text("Enter the second chassis number:", reply_markup=get_cancel_keyboard())
        context.user_data['last_message_id'] = message.message_id
        return CHASSIS_NUMBER_2
    else:
        return await finish_session(update, context)

async def get_chassis_number_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        return await cancel_training_session(update, context)
    
    chassis_number_2 = update.message.text
    row_index = context.user_data['current_row']
    
    df = read_excel_safe('mechanics.xlsx')
    df.at[row_index, 'chassis_number_2'] = chassis_number_2
    df.to_excel('mechanics.xlsx', index=False)
    
    await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    message = await update.message.reply_text("Enter the sprocket ratio for the second chassis:", reply_markup=get_cancel_keyboard())
    context.user_data['last_message_id'] = message.message_id
    return SPROCKET_RATIO_2

async def get_sprocket_ratio_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        return await cancel_training_session(update, context)
    
    sprocket_ratio_2 = update.message.text
    row_index = context.user_data['current_row']
    
    df = read_excel_safe('mechanics.xlsx')
    df.at[row_index, 'sprocket_ratio_2'] = sprocket_ratio_2
    df.to_excel('mechanics.xlsx', index=False)
    
    await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    message = await update.message.reply_text("Enter the tire pressure for the second chassis:", reply_markup=get_cancel_keyboard())
    context.user_data['last_message_id'] = message.message_id
    return TIRE_PRESSURE_2

async def get_tire_pressure_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        return await cancel_training_session(update, context)
    
    tire_pressure_2 = update.message.text
    row_index = context.user_data['current_row']
    
    df = read_excel_safe('mechanics.xlsx')
    df.at[row_index, 'tire_pressure_2'] = tire_pressure_2
    df.to_excel('mechanics.xlsx', index=False)
    
    await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    message = await update.message.reply_text("Enter the tire condition for the second chassis:", reply_markup=get_cancel_keyboard())
    context.user_data['last_message_id'] = message.message_id
    return TIRE_CONDITION_2

async def get_tire_condition_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        return await cancel_training_session(update, context)
    
    tire_condition_2 = update.message.text
    row_index = context.user_data['current_row']
    
    df = read_excel_safe('mechanics.xlsx')
    df.at[row_index, 'tire_condition_2'] = tire_condition_2
    df.to_excel('mechanics.xlsx', index=False)
    
    await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    message = await update.message.reply_text("Enter the lap time for the second chassis:", reply_markup=get_cancel_keyboard())
    context.user_data['last_message_id'] = message.message_id
    return LAP_TIME_2

async def get_lap_time_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'cancel':
        return await cancel_training_session(update, context)
    
    lap_time_2 = update.message.text
    row_index = context.user_data['current_row']
    
    df = read_excel_safe('mechanics.xlsx')
    df.at[row_index, 'lap_time_2'] = lap_time_2
    df.to_excel('mechanics.xlsx', index=False)
    
    await delete_message_with_retry(context, update.effective_chat.id, context.user_data['last_message_id'])
    await delete_message_with_retry(context, update.effective_chat.id, update.message.message_id)
    
    return await finish_session(update, context)

async def finish_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    row_index = context.user_data['current_row']
    df = read_excel_safe('mechanics.xlsx')
    session_data = df.iloc[row_index]
    
    message = f"Training session data recorded:\n"
    message += f"Pilot: {session_data['pilot_name']}\n"
    message += f"Class: {session_data['kart_class']}\n"
    message += f"Session: {session_data['session_number']}\n"
    message += f"Chassis 1: {session_data['chassis_number']}\n"
    message += f"Tire Pressure 1: {session_data['tire_pressure']}\n"
    message += f"Tire Condition 1: {session_data['tire_condition']}\n"
    message += f"Sprocket Ratio 1: {session_data['sprocket_ratio']}\n"
    message += f"Lap Time 1: {session_data['lap_time']}\n"
    
    if pd.notna(session_data.get('chassis_number_2')):
        message += f"\nChassis 2: {session_data['chassis_number_2']}\n"
        message += f"Tire Pressure 2: {session_data['tire_pressure_2']}\n"
        message += f"Tire Condition 2: {session_data['tire_condition_2']}\n"
        message += f"Sprocket Ratio 2: {session_data['sprocket_ratio_2']}\n"
        message += f"Lap Time 2: {session_data['lap_time_2']}\n"
    
    await update.message.reply_text(message)
    await update.message.reply_text("What would you like to do next?", reply_markup=get_main_menu_keyboard())
    
    return AWAITING_CHOICE

async def cancel_training_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'current_row' in context.user_data:
        row_index = context.user_data['current_row']
        df = read_excel_safe('mechanics.xlsx')
        df = df.drop(row_index)
        df.to_excel('mechanics.xlsx', index=False)
    
    await update.message.reply_text("Training session cancelled.", reply_markup=get_main_menu_keyboard())
    return AWAITING_CHOICE
