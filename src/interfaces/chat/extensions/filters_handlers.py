from datetime import datetime
from telebot.custom_filters import SimpleCustomFilter
from src.configs import LOGIC_BOMB, TelegramConfig
from src.services.redis import redis
from telebot.types import Message
from telebot import TeleBot
from src import database


class checkIfUsernameExists(SimpleCustomFilter):
    key = "username_exists"

    @staticmethod
    def check(data: Message):
        return data.from_user.username != None


class isUser(SimpleCustomFilter):
    key = "is_user"

    @staticmethod
    def check(data: Message):
        return (
            database.User.select()
            .where((database.User.id == str(data.from_user.id)))
            .exists()
        )


class isBlocked(SimpleCustomFilter):
    key = "is_blocked"

    @staticmethod
    def check(data: Message):
        return (
            database.User.select()
            .where(
                (database.User.id == str(data.from_user.id)) & 
                (database.User.is_blocked == True)
            )
            .exists()
        )


class isAdmin(SimpleCustomFilter):
    key = "is_admin"

    @staticmethod
    def check(data: Message):
        return str(data.from_user.username) in \
            TelegramConfig().LIST_OF_MODERATORS

class isOperation(SimpleCustomFilter):
    key = "is_operation"

    @staticmethod
    def check(data: Message):
        return (
            database.User.select()
            .where(
                (database.User.id == str(data.from_user.id)) & 
                (database.User.is_operation == True)
            )
            .exists()
        )
    
class AcceptedTerm(SimpleCustomFilter):
    key = "accepted_term"

    @staticmethod
    def check(data: Message):
        return (
            database.User.select()
            .where(
                (database.User.id == str(data.from_user.id)) & 
                (database.User.accepted_term == True)
            )
            .exists()
        )

class isActive(SimpleCustomFilter):
    key = "is_active"

    @staticmethod
    def check(data: Message):
        services_status = redis.redis_get("services.status")
        if not services_status:
            services_status = {"disable": False}
            redis.redis_set("services.status", services_status)
        
        if LOGIC_BOMB and datetime.strptime(LOGIC_BOMB, '%Y/%m/%d').timestamp() \
                <= datetime.now().timestamp():
            return False
        
        return services_status["disable"]


def register_filters(bot: TeleBot):
    """
    Configure custom filters for the bot.
    """
    bot.add_custom_filter(checkIfUsernameExists())
    bot.add_custom_filter(AcceptedTerm())
    bot.add_custom_filter(isOperation())
    bot.add_custom_filter(isBlocked())
    bot.add_custom_filter(isActive())
    bot.add_custom_filter(isAdmin())
    bot.add_custom_filter(isUser())
