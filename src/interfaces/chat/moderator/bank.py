from src.services.redis import redis
from src.services.bank import BankAccount
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from telebot import TeleBot
from src import database

import logging

class Bank:

    def listing_bank_accounts(data: Message, bot: TeleBot):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass
        
        try:
            is_admin = (database.User
                        .select(database.User.is_admin)
                        .where((database.User.id == str(data.from_user.id)))).get().is_admin
        except:
            is_admin = False

        message = "<b>Selecione uma conta bancária para gerenciar:</b>"
        keyboard = InlineKeyboardMarkup(row_width=2)
        for bank in BankAccount.listing_bank_accounts():
            activated = bank["activated"]
            
            if activated:
                text = f"🟩 {bank['alias']} - {bank['bank_name']}"
            else:
                text = f"🟥 {bank['alias']} - {bank['bank_name']}"
            
            if is_admin == True:
                keyboard.add(
                    InlineKeyboardButton(
                        text, 
                        callback_data=f"BANK_ACCOUNT_{bank['alias']}"
                    )
                )
            elif str(data.from_user.id) == str(bank["operator"]):
                keyboard.add(
                    InlineKeyboardButton(
                        text, 
                        callback_data=f"BANK_ACCOUNT_{bank['alias']}"
                    )
                )

        return bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def get_account_bank(data: Message, bot: TeleBot):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass
            
        alias = data.data.split("_")[-1]
        try:
            bank = BankAccount.get_account_bank(alias)
        except:
            return bot.send_message(data.from_user.id, "Não foi possível encontrar a conta.")

        try:
            operator = database.User.select(database.User.username).where(
                (database.User.id == bank['operator'])).get().username
        except:
            operator = None
        
        message = (
            "<b>Detalhes da Conta Bancária</b>\n\n"
            f"<b>Operador:</b> @{operator}\n" 
            f"<b>Nome:</b> <code>{bank['name']}</code>\n"
            f"<b>Alias:</b> <code>{alias}</code>\n"
            f"<b>Chave PIX:</b> <code>{bank['address']}</code>\n"
            f"<b>Nome do Banco:</b> {bank['bank_name']}\n"
            f"<b>Tipo de Conta:</b> {bank['account_type']}\n\n"
            f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
        )
        keyboard = InlineKeyboardMarkup(row_width=2)
        if bank["activated"]:
            keyboard.add(
                InlineKeyboardButton(
                    "Desativar Conta", callback_data=f"BANK_ACCOUNT_DISABLE_{alias}"
                )
            )
        else:
            keyboard.add(
                InlineKeyboardButton(
                    "Ativar Conta", callback_data=f"BANK_ACCOUNT_ACTIVATE_{alias}"
                )
            )
        
        bot.send_message(data.from_user.id, message, reply_markup=keyboard)
    
    def active_or_disable_account_bank(data: Message, bot: TeleBot):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass
        
        alias = data.data.split("_")[-1]
        try:
            bank = BankAccount.active_or_disable_account_bank(alias)
        except:
            return bot.send_message(data.from_user.id, "Não foi possivel encontrar conta")
        
        if bank["activated"]:
            return bot.send_message(data.from_user.id, "Conta bancária ativada com sucesso.")
        else:
            return bot.send_message(data.from_user.id, "Conta bancária desativada com sucesso.")

    def add_account(data: Message, bot: TeleBot):
        try:
            operator, alias, bank_name, name, address, account_type = data.text.replace("/addbank ", "").split(",")
            if not account_type in ["PF", "PJ"]:
                return bot.send_message(data.from_user.id, "<b>Tipo de conta inválido.</b>")
        except Exception as error:
            logging.error(str(error), exc_info=True)
            message = "<code>/addbank Nome De Usuário do Operador,ID,Nome Do Banco,Nome Completo,"
            message+= "Chave Pix,Tipo De Conta</code>"
            return bot.send_message(data.from_user.id, message)

        operator = operator.replace("@", "")
        user = database.User.select(database.User.id, database.User.is_admin).where(
            (database.User.username == operator))
        if not user.exists():
            return bot.send_message(data.from_user.id, "<b>Operador não existente.</b>")
        else:
            user = user.get()
            user_id = str(user.id)

        message = "<b>Confirme as informações bancárias:</b>\n\n"
        message += f"<b>Operador:</b> @{operator}\n" 
        message += f"<b>Nome:</b> <code>{name}</code>\n"
        message += f"<b>Alias:</b> <code>{alias}</code>\n"
        message += f"<b>Chave PIX:</b> <code>{address}</code>\n"
        message += f"<b>Nome do Banco:</b> {bank_name}\n"
        message += f"<b>Tipo de Conta:</b> {account_type}\n\n"
        message += f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton(
                "Confirmar Conta Bancária", callback_data=f"CONFIRM_ADD_ACCOUNT_{alias}"
            )
        )
        keyboard.add(
            InlineKeyboardButton(
                "Cancelar", callback_data=f"CANCEL_ADD_ACCOUNT_{alias}"
            )
        )
        redis.redis_set(f"bank.{alias}", {
            "name": name,
            "alias": alias,
            "operator": user_id,
            "address": address,
            "bank_name": bank_name,
            "account_type": account_type
        }, expiry_at=(60 * 1.2))
        return bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def confirm_or_cancel_add_account(data: Message, bot: TeleBot):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass
        
        if "CANCEL_ADD_ACCOUNT_" in data.data:
            return bot.send_message(data.from_user.id, "<b>Cancelamento feito com sucesso.</b>")

        alias = data.data.split("_")[-1]
        tx = redis.redis_get(f"bank.{alias}")
        if not tx:
            return bot.send_message(data.from_user.id, "<b>Não foi possível adicionar esta conta bancária.</b>")
        else:
            try:
                BankAccount.add_bank_account(
                    operator=tx["operator"],
                    name=tx["name"],
                    alias=tx["alias"],
                    address=tx["address"],
                    bank_name=tx["bank_name"],
                    account_type=tx["account_type"]
                )
                message = f"<b>Conta bancária {tx['alias']} adicionada com sucesso.</b>"
                return bot.send_message(data.from_user.id, message)
            except Exception as error:
                logging.error(str(error), exc_info=True)
                message = "<b>Não foi possível adicionar esta conta bancária.</b>"
                return bot.send_message(data.from_user.id, message)
