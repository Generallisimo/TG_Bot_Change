import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
import requests

# Настройки логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ваш токен
TOKEN = os.getenv('TELEGRAM_TOKEN', '7312638510:AAFDeQhPyh5g8lVg1QSQq7eFConOXLFKuAI')
LARAVEL_URL = os.getenv('LARAVEL_URL', 'http://127.0.0.1:8000')

# Команда старт
def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    update.message.reply_markdown_v2(
        fr'Привет {user.mention_markdown_v2()}\!',
        reply_markup=ForceReply(selective=True),
    )

# Обработчик сообщений
def handle_message(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    if "Transaction ID" in text:
        transaction_id = text.split('\n')[1].split(': ')[1]
        keyboard = [
            [
                InlineKeyboardButton("Да", callback_data=f"confirm_{transaction_id}"),
                InlineKeyboardButton("Нет", callback_data=f"reject_{transaction_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Подтвердите транзакцию:', reply_markup=reply_markup)

# Обработчик нажатий на кнопки
def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    action, transaction_id = query.data.split('_')
    
    if action in ['confirm', 'reject']:
        response = requests.post(f'{LARAVEL_URL}/telegram/confirm', json={'transaction_id': transaction_id, 'action': action})
        if response.status_code == 200:
            query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([]))
            query.message.reply_text(text=f"Транзакция {transaction_id} {action}!")
            logger.info(f"Транзакция {transaction_id} {action} подтверждена.")
            # Добавляем новые кнопки
            keyboard = [
                [
                    InlineKeyboardButton("Done", callback_data=f"done_{transaction_id}"),
                    InlineKeyboardButton("Failed", callback_data=f"failed_{transaction_id}"),
                    InlineKeyboardButton("Cancelled", callback_data=f"cancelled_{transaction_id}"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.message.reply_text(text=f'Обновите статус транзакции:{transaction_id}', reply_markup=reply_markup)
        else:
            query.message.reply_text(text="Ошибка при обработке запроса.")
            logger.error(f"Ошибка при подтверждении транзакции {transaction_id}.")
    else:
        response = requests.post(f'{LARAVEL_URL}/telegram/status', json={'transaction_id': transaction_id, 'status': action})
        if response.status_code == 200:
            query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([]))
            query.message.reply_text(text=f"Транзакция {transaction_id} обновлена статусом: {action}!")
            logger.info(f"Транзакция {transaction_id} обновлена статусом: {action}.")
        else:
            query.message.reply_text(text="Ошибка при обновлении статуса.")
            logger.error(f"Ошибка при обновлении статуса транзакции {transaction_id}.")

def main() -> None:
    updater = Updater(TOKEN)

    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dispatcher.add_handler(CallbackQueryHandler(button))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
