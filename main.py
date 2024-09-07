from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters
from utils import get_main_menu_keyboard, save_user, get_user
from training_session import (
    start_training_session, handle_session_choice, start_new_session,
    list_today_sessions, handle_edit_session_choice, handle_edit_field_choice,
    handle_edit_field_value, confirm_pilot, get_pilot_name, 
    confirm_class, get_class_name, get_session_number,
    confirm_chassis, get_chassis_number, confirm_sprocket, get_sprocket_ratio,
    get_tire_pressure, get_tire_condition, get_lap_time, cancel_training_session,
    handle_second_chassis, get_chassis_number_2, get_sprocket_ratio_2,
    get_tire_pressure_2, get_tire_condition_2, get_lap_time_2,
    SESSION_CHOICE, EDIT_SESSION_CHOICE, EDIT_FIELD_CHOICE, 
    EDIT_FIELD_VALUE, PILOT_CONFIRM, PILOT_NAME, CLASS_CONFIRM, CLASS_NAME,
    SESSION_NUMBER, CHASSIS_CONFIRM, CHASSIS_NUMBER, SPROCKET_CONFIRM, 
    SPROCKET_RATIO, TIRE_PRESSURE, TIRE_CONDITION, LAP_TIME, SECOND_CHASSIS,
    CHASSIS_NUMBER_2, SPROCKET_RATIO_2, TIRE_PRESSURE_2, TIRE_CONDITION_2, LAP_TIME_2
)
from expenses import start_expense_tracking, get_expense_description, get_expense_amount, cancel_expense_tracking
from states import FULLNAME, AWAITING_CHOICE, EXPENSE_DESCRIPTION, EXPENSE_AMOUNT

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = get_user(update.effective_user.id)
    if user:
        context.user_data['mechanic'] = user['fullname']
        await update.message.reply_text(
            f"Welcome back, {user['fullname']}! What would you like to do?",
            reply_markup=get_main_menu_keyboard()
        )
        return AWAITING_CHOICE
    else:
        await update.message.reply_text("Welcome! Please enter your full name (first name and last name) to register.")
        return FULLNAME

async def get_fullname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    fullname = update.message.text
    if len(fullname.split()) < 2:
        await update.message.reply_text("Please enter both your first name and last name separated by a space.")
        return FULLNAME

    user_id = update.effective_user.id
    username = update.effective_user.username

    save_user(user_id, fullname, username)
    
    context.user_data['mechanic'] = fullname
    await update.message.reply_text(
        f"Thank you for registering, {fullname}! Your expense tracking table has been created.",
    )
    await update.message.reply_text(
        "What would you like to do?",
        reply_markup=get_main_menu_keyboard()
    )
    return AWAITING_CHOICE

async def handle_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    if choice == 'Training Session':
        return await start_training_session(update, context)
    elif choice == 'Expenses':
        return await start_expense_tracking(update, context)
    elif choice == 'Help':
        await update.message.reply_text("This is a help message. You can add more detailed instructions here.")
        await update.message.reply_text("What would you like to do next?", reply_markup=get_main_menu_keyboard())
        return AWAITING_CHOICE
    else:
        await update.message.reply_text("Invalid choice. Please select an option from the menu.", reply_markup=get_main_menu_keyboard())
        return AWAITING_CHOICE

def main() -> None:
    application = Application.builder().token("7154116674:AAHzyP00px9R_IhqDM3HBtrMMmYzrY8oZf4").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            FULLNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fullname)],
            AWAITING_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_choice)],
            EXPENSE_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_expense_description)],
            EXPENSE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_expense_amount)],
            SESSION_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_session_choice)],
            EDIT_SESSION_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_session_choice)],
            EDIT_FIELD_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_field_choice)],
            EDIT_FIELD_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_field_value)],
            PILOT_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Cancel$'), confirm_pilot),
                MessageHandler(filters.Regex('^Cancel$'), cancel_training_session)
            ],
            PILOT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Cancel$'), get_pilot_name),
                MessageHandler(filters.Regex('^Cancel$'), cancel_training_session)
            ],
            CLASS_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Cancel$'), confirm_class),
                MessageHandler(filters.Regex('^Cancel$'), cancel_training_session)
            ],
            CLASS_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Cancel$'), get_class_name),
                MessageHandler(filters.Regex('^Cancel$'), cancel_training_session)
            ],
            SESSION_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Cancel$'), get_session_number),
                MessageHandler(filters.Regex('^Cancel$'), cancel_training_session)
            ],
            CHASSIS_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Cancel$'), confirm_chassis),
                MessageHandler(filters.Regex('^Cancel$'), cancel_training_session)
            ],
            CHASSIS_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Cancel$'), get_chassis_number),
                MessageHandler(filters.Regex('^Cancel$'), cancel_training_session)
            ],
            SPROCKET_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Cancel$'), confirm_sprocket),
                MessageHandler(filters.Regex('^Cancel$'), cancel_training_session)
            ],
            SPROCKET_RATIO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Cancel$'), get_sprocket_ratio),
                MessageHandler(filters.Regex('^Cancel$'), cancel_training_session)
            ],
            TIRE_PRESSURE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Cancel$'), get_tire_pressure),
                MessageHandler(filters.Regex('^Cancel$'), cancel_training_session)
            ],
            TIRE_CONDITION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Cancel$'), get_tire_condition),
                MessageHandler(filters.Regex('^Cancel$'), cancel_training_session)
            ],
            LAP_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Cancel$'), get_lap_time),
                MessageHandler(filters.Regex('^Cancel$'), cancel_training_session)
            ],
            SECOND_CHASSIS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Cancel$'), handle_second_chassis),
                MessageHandler(filters.Regex('^Cancel$'), cancel_training_session)
            ],
            CHASSIS_NUMBER_2: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Cancel$'), get_chassis_number_2),
                MessageHandler(filters.Regex('^Cancel$'), cancel_training_session)
            ],
            SPROCKET_RATIO_2: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Cancel$'), get_sprocket_ratio_2),
                MessageHandler(filters.Regex('^Cancel$'), cancel_training_session)
            ],
            TIRE_PRESSURE_2: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Cancel$'), get_tire_pressure_2),
                MessageHandler(filters.Regex('^Cancel$'), cancel_training_session)
            ],
            TIRE_CONDITION_2: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Cancel$'), get_tire_condition_2),
                MessageHandler(filters.Regex('^Cancel$'), cancel_training_session)
            ],
            LAP_TIME_2: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^Cancel$'), get_lap_time_2),
                MessageHandler(filters.Regex('^Cancel$'), cancel_training_session)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_training_session)],
    )

    application.add_handler(conv_handler)

    print("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()