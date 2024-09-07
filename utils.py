from telegram import ReplyKeyboardMarkup
from telegram.error import NetworkError
import asyncio
import pandas as pd

column_types = {
    'user_id': 'object',    'mechanic': 'str',
    'timestamp': 'str',
    'pilot_name': 'str',
    'session_number': 'str',
    'chassis_number': 'str',
    'tire_pressure': 'str',
    'tire_condition': 'str',
    'sprocket_ratio': 'str',  
    'lap_time': 'str'
}

def get_main_menu_keyboard():
    return ReplyKeyboardMarkup([['Training Session', 'Expenses'], ['Help']], resize_keyboard=True)

async def delete_message_with_retry(context, chat_id, message_id, max_retries=3):
    for attempt in range(max_retries):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            return
        except NetworkError as e:
            if attempt == max_retries - 1:
                print(f"Failed to delete message after {max_retries} attempts: {e}")
            else:
                await asyncio.sleep(1)  

async def send_message_with_retry(context, chat_id, text, reply_markup=None, max_retries=3):
    for attempt in range(max_retries):
        try:
            message = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
            return message
        except NetworkError as e:
            if attempt == max_retries - 1:
                print(f"Failed to send message after {max_retries} attempts: {e}")
                return None
            else:
                await asyncio.sleep(1)  

def read_excel_safe(file_path):
    try:
        df = pd.read_excel(file_path, dtype=column_types)
        df['user_id'] = pd.to_numeric(df['user_id'], errors='coerce').astype('Int64')
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=column_types.keys()).astype(column_types)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return pd.DataFrame(columns=column_types.keys()).astype(column_types)

def save_user(user_id, fullname, username):
    df = read_excel_safe('users.xlsx')
    new_user = pd.DataFrame({
        'user_id': [user_id],
        'fullname': [fullname],
        'username': [username]
    })
    df = pd.concat([df, new_user], ignore_index=True)
    df.to_excel('users.xlsx', index=False)

def get_user(user_id):
    df = read_excel_safe('users.xlsx')
    user = df[df['user_id'] == user_id]
    if not user.empty:
        return user.iloc[0].to_dict()
    return None

