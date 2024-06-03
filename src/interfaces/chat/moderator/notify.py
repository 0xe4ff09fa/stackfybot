from src.services.helpers import calculate_percentage
from src.services.redis import redis
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from src.configs import PURCHASE_FEERATE_PRICE
from bitpreco import BitPreco
from datetime import datetime
from telebot import TeleBot
from base64 import b64decode, b64encode
from uuid import uuid4
from src import database

import concurrent.futures

# Initialize BitPreco
bitpreco = BitPreco()

class Notify:

    def notify_menu(data: Message, bot: TeleBot):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass
        
        message = "Selecione uma das opções abaixo para enviar notificações a os usuários:"

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Cotação", callback_data="NOTIFICATION_PRICE"))
        keyboard.add(InlineKeyboardButton("Customizado", callback_data="NOTIFICATION_CUSTOM"))
        return bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def notify_custom(data: Message, bot: TeleBot):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        message = "<b>Envie a sua mensagem personalizada abaixo:</b>"
        message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
        return bot.send_message(data.from_user.id, message, reply_markup=ForceReply(selective=False))
    
    def notify_custom_add(data: Message, bot: TeleBot):
        message = ""
        photo = None
        content_type = data.content_type
        if content_type == "photo":
            message = data.caption
            photo = bot.download_file(
                file_path=bot.get_file(data.photo[-1].file_id).file_path)
        else:
            message = data.text

        txid = str(uuid4())
        value = {
            "message": message,
            "photo": photo
        }
        if photo:
            value["photo"] = b64encode(photo).decode()
        
        redis.redis_set(f"tx.notify.message.{txid}", value, 25)
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(
            "Enviar Para Todos", callback_data=f"SEND_ALL_MESSAGE_{txid}"))
        if photo:
            return bot.send_photo(data.from_user.id, photo, message, reply_markup=keyboard)
        else:
            return bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def notify_stop_service(data: Message, bot: TeleBot):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        services_status = redis.redis_get("services.status")
        if not services_status:
            services_status = {"disable": False}

        if services_status["disable"]:
            message = "<b>🟩 Prezado cliente, nosso bot está ativo agora e disponível para ajudar. Sinta-se à vontade para utilizar nossos serviços a qualquer momento.</b>"
        else:
            message = "<b>⚠️ Caro cliente, nosso bot está desabilitado no momento, voltaremos em breve.</b>"

        txid = str(uuid4())
        value = { "message": message }
        if services_status["disable"]:
            value["keyboards"] = [{
                "key": "Comprar Bitcoin", 
                "callback_data": "MENU_CUSTOMER"
            }]

        redis.redis_set(f"tx.notify.message.{txid}", value, 25)

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(
            "Enviar Para Todos", callback_data=f"SEND_ALL_MESSAGE_{txid}"))
        return bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def notify_price(data: Message, bot: TeleBot):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        price = bitpreco.get_price()
        price["SELL"] += calculate_percentage(
            x=price["SELL"], 
            y=PURCHASE_FEERATE_PRICE
        )
        ratio = price["RATIO"]
        if ratio < 0:
            message = f"🔻 <b>Cotação atual R$ {price['SELL']:,.2f} ({price['RATIO']:,.2f}% 24h)</b>\n\n"
            message+= "Bitcoin em queda, aproveite para acumular mais sats."
        else:
            message = f"🟢 <b>Cotação atual R$ {price['SELL']:,.2f} ({price['RATIO']:,.2f}% 24h)</b>\n\n"
            message+= "O valor do BTC está decolando para novas alturas! 🚀 "
            message+= "Prepare-se para uma jornada emocionante na toca do coelho! 🌐"
        
        txid = str(uuid4())
        redis.redis_set(f"tx.notify.message.{txid}", {
            "message": message,
            "keyboards": [{
                "key": "Comprar Bitcoin", 
                "callback_data": "MENU_CUSTOMER"
            }]
        }, 25)

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(
            "Enviar Para Todos", callback_data=f"SEND_ALL_MESSAGE_{txid}"))
        return bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def notify_all_users(data: Message, bot: TeleBot):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass
        
        txid = data.data.split("_")[-1]    
        tx = redis.redis_get(f"tx.notify.message.{txid}")
        if not tx:
            message = "Tente enviar novamente sua mensagem de notificação.\n\n"
            message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            return bot.send_message(data.from_user.id, message)
    
        message = tx["message"] + "\n\n"
        message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
    
        keyboard = None
        if bool(tx.get("keyboards", [])):
            keyboard = InlineKeyboardMarkup()
            for k in tx.get("keyboards", []):        
                keyboard.add(InlineKeyboardButton(
                    k["key"], callback_data=k["callback_data"]))
        
        photo = tx.get("photo")
        if photo:
            photo = b64decode(photo)

        def send_message_to_user(user_id):
            if photo:
                bot.send_photo(user_id, photo, message, reply_markup=keyboard)
            else:
                bot.send_message(user_id, message, reply_markup=keyboard)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(send_message_to_user, [str(user.id) for user in 
                                                database.User.select(database.User.id).where(
                                                    (database.User.is_admin == False) & 
                                                    (database.User.is_operation == False))])

        message = "<b>Notificação enviada com sucesso!</b>\n\n"
        message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
        return bot.send_message(data.from_user.id, message)