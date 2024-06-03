from src.interfaces.chat.extensions import (
    middlewares_handlers,
    filters_handlers,
    message_handlers,
    query_handlers,
)
from telebot.types import Update
from src.configs import TelegramConfig
from telebot import apihelper, TeleBot
from time import sleep

import logging
import json

# Enable middleware
apihelper.ENABLE_MIDDLEWARE = True

# Create a TeleBot instance
bot = TeleBot(
    token=TelegramConfig().TELEGRAM_TOKEN,
    skip_pending=False,
    num_threads=4,
    parse_mode="HTML",
)

# Configure logging
logging.basicConfig(level=logging.INFO)


def loads_updates(data: dict):
    bot.process_new_updates([Update.de_json(json.dumps(data))])


@bot.message_handler(func=lambda data: not data.from_user.username)
def username_not_exist(data: dict):
    message = (
        "Por favor, adicione um nome de usuário ao seu perfil do Telegram.\n\n"
        "Se você não souber como fazer isso, assista a este "
        "vídeo: https://youtu.be/50roLYHIKEs"
    )
    return bot.send_message(data.from_user.id, message)


def create_app():
    """
    Create the Telegram bot application
    """
    try:
        bot.delete_webhook(drop_pending_updates=True)
    except Exception as error:
        logging.error(str(error), exc_info=True)

    middlewares_handlers.register_middlewares(bot)
    filters_handlers.register_filters(bot)
    message_handlers.register_message_handlers(bot)
    query_handlers.register_callback_query_handlers(bot)

    if TelegramConfig().WEBHOOK_URL:
        url = f"{TelegramConfig().WEBHOOK_URL}/api/v1/webhook/telegram"
        key = TelegramConfig().WEBHOOK_KEY
        bot.set_webhook(url=url, secret_token=key, drop_pending_updates=True)
    else:
        while True:
            try:
                bot.polling(none_stop=True)
            except Exception as error:
                logging.info(error, exc_info=True)
                sleep(5)


def start():
    """
    Start the Telegram bot and keep it running
    """
    logging.info(f"Starting Chat Bot: https://t.me/{bot.get_me().username}")

    create_app()
