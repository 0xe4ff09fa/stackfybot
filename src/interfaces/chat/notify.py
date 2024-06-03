from src.services.helpers import format_cpf
from src.services.redis import redis
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from telebot import TeleBot
from src import database

import logging

class Notify:

    @staticmethod
    def notify_sell_order(
            bot:                          TeleBot, 
            txid:                         str,
            username:                     str,
            value_from_btc:               float,
            value_to_brl:                 float,
            identifier:                   str,
            address:                      str,
            network:                      str,
            identification_document_id:   str,
            identification_document_name: str,
            channel_id:                   str
        ):
        """
        Notifies a sell order to admin users with 
        the relevant details.
        """
        message = (
            "<b>🟥 [Venda] Detalhes de Pedido:</b>\n\n"
            f"<b>Usuário:</b> <i>@{username}</i>\n"
            f"<b>Nome:</b> <i><code>{identification_document_name}</code></i>\n"
            f"<b>CPF:</b> <i><code>{format_cpf(identification_document_id)}</code></i>\n"
            f"<b>Quantidade:</b> R$ <code>{value_to_brl:,.2f}</code> <i>(<code>{int(value_from_btc)}</code> sats)</i>\n"
            f"<b>ID:</b> <code>{identifier}</code>\n"
            f"<b>Método de Pagamento:</b> {network.upper()}\n"
            f"<b>Endereço de Pagamento:</b> <i><code>{address}</code></i>\n\n"
            f"<b>Txid:</b> <code>{txid}</code>\n\n"
            f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
        )

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Verificar", callback_data=f"SELL_TX_{txid}"))
        for user in database.User.select(database.User.id).where((database.User.is_operation == True)):
            try:
                bot.send_message(user.id, message, reply_markup=keyboard)
            except:
                pass
        
        if channel_id:
            try:
                bot.send_message(channel_id, message)
            except:
                pass

    @staticmethod
    def notify_purchase_order(
            bot:                          TeleBot, 
            txid:                         str,
            username:                     str,
            value_from_brl:               float,
            value_to_btc:                 float,
            identifier:                   str,
            address:                      str,
            bank_id:                      str,
            bank_name:                    str,
            bank_full_name:               str,
            bank_key:                     str,
            identification_document_id:   str,
            identification_document_name: str,
            channel_id:                   str
        ):
        """
        Notifies a purchase order to admin users with 
        the relevant details.
        """
        try:
            network = redis.redis_get(f"tx.address.{txid}")\
                .get("network", "LN")\
                    .upper()
        except Exception as error:
            logging.error(str(error), exc_info=True)
            network = None

        if network == "BTC":
            symbol_icon = "⛓️"
        elif network == "LIQUID":
            symbol_icon = "💧"
        else:
            symbol_icon = "⚡"

        message = (
            f"<b>{symbol_icon} [Compra] R$ {value_from_brl:,.2f}</b>\n\n"
            f"<b>Quantidade:</b> R$ <code>{value_from_brl:,.2f}</code> <i>(<code>{round(value_to_btc)}</code> sats)</i>\n"
            f"<b>Usuário:</b> <i>@{username}</i>\n"
            f"<b>Nome:</b> <i><code>{identification_document_name}</code></i>\n"
            f"<b>CPF:</b> <i><code>{format_cpf(identification_document_id)}</code></i>\n"
            f"<b>ID:</b> <code>{identifier}</code>\n"
            f"<b>Rede:</b> {network}\n"
            f"<b>Endereço de Pagamento:</b> <i><code>{address}</code></i>\n\n"
            "<b>Conta de Depósito:</b>\n"
            f"<b>ID:</b> {bank_id}\n"
            f"<b>Banco:</b> {bank_name}\n"
            f"<b>Nome:</b> <code>{bank_full_name}</code>\n"
            f"<b>Chave:</b> <code>{bank_key}</code>\n\n"
            f"<b>Txid:</b> <code>{txid}</code>\n\n"
            f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
        )
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Verificar", callback_data=f"BUY_TX_{txid}"))
        for user in (
                database.User
                    .select(database.User.id)
                    .where((database.User.is_operation == True))):
            bot.send_message(str(user.id), message, reply_markup=keyboard)
        
        if channel_id:
            bot.send_message(channel_id, message)

    def notify_new_user_verification(
            bot: TeleBot, 
            username: str, 
            email: str, 
            full_name: str,
            cpf: str,
            date_of_birth: str
        ):
        message = f"🔎 [Verificação]\n\n"
        message+= f"<b>Usuário:</b> {username}\n"
        message+= f"<b>E-Mail:</b> {email}\n"
        message+= f"<b>Nome Completo:</b> {full_name}\n"
        message+= f"<b>Data de Nascimento:</b> {date_of_birth}\n"
        message+= f"<b>CPF:</b> {format_cpf(cpf)}\n\n"
        message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Verificar", callback_data=f"USER_@{username}"))
        for user in (
                database.User
                    .select(database.User.id)
                    .where((database.User.is_admin == True))):
            bot.send_message(str(user.id), message, reply_markup=keyboard)

    def notify_user_status_verification(
            bot: TeleBot, 
            status: str, 
            user_id: str
        ):
        if status == "approved":
            message = "<b>Seu pedido de aumento de nivel foi aprovado com sucesso.</b>"
        else:
            message = "<b>Seu pedido de aumento de nível foi reprovado.</b>"
        
        return bot.send_message(str(user_id), message)