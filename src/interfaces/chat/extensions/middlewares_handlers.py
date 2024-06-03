from telebot.types import Message, CallbackQuery
from src.configs import TelegramConfig
from telebot import TeleBot
from src import database

import logging

def logger(bot: TeleBot, data: Message):
    """
    Middleware handler to log user interactions
    """
    if isinstance(data, Message):
        if data.content_type in ["photo"]:
            logger_info = f"ID: {data.from_user.id} - User: {data.from_user.username} - Content Type: {data.content_type}"
            logging.info(logger_info)
        else:
            logger_info = f"ID: {data.from_user.id} - User: {data.from_user.username} - Text: {data.text} - Content Type: {data.content_type}"
            logging.info(logger_info)
    elif isinstance(data, CallbackQuery):
        logger_info = f"ID: {data.from_user.id} - User: {data.from_user.username} - Button: {data.data}"
        logging.info(logger_info)

def update_user_info(bot: TeleBot, data: Message):
    """
    Update user information in the database.

    This middleware is responsible for updating user information such as username and first name whenever a message
    or callback_query is received.

    Args:
        bot (TeleBot): The Telegram bot instance.
        data (Message): The incoming message or callback_query data.
    """
    user = database.User.get_or_create(
        id=str(data.from_user.id))[0]
    if user.username != data.from_user.username:
        user.username = data.from_user.username

    if user.first_name != data.from_user.first_name:
        user.first_name = data.from_user.first_name

    is_admin = data.from_user.username in \
        TelegramConfig().LIST_OF_MODERATORS
    if is_admin:
        user.is_operation = True
    
    if user.is_admin != is_admin:
        user.is_admin = is_admin
    
    user.save()

def register_middlewares(bot: TeleBot):
    bot.add_middleware_handler(logger, update_types=["message", "callback_query"])
    bot.add_middleware_handler(update_user_info, update_types=["message"])
