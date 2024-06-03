from src.interfaces.chat.notify import Notify
from src.services.helpers import format_cpf
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from datetime import datetime
from telebot import TeleBot
from src import database

import logging

class User:

    def get_list_users_pending_approval(data: Message, bot: TeleBot):
        """
        Display a list of users pending approval.

        Args:
            data (telebot.types.Message): The received message object.
            bot (telebot.TeleBot): The Telegram bot object.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        message = (
            "<b>Lista de usuários pendentes de aprovação.</b>\n\n"
            "Para acessar qualquer uma dos usuários, clique no botão correspondente abaixo:"
        )

        keyboard = InlineKeyboardMarkup()
        for doc in (
                database.IdentificationDocument
                .select()
                .where(
                    (database.IdentificationDocument.status == "pending")
                )):
            keyboard.add(InlineKeyboardButton(f"{doc.user.id}", callback_data=f"USER_{doc.user.id}"))
        
        bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def get_user_info(data: Message, bot: TeleBot):
        """
        Get information about a user and send it as a message.
    
        Args:
            data (telebot.types.Message): The received message object.
            bot (telebot.TeleBot): The Telegram bot object.
        """
        try:
            username = data.text.split()[-1]
        except:
            try:
                bot.delete_message(data.from_user.id, data.message.message_id)
            except:
                pass
        
            username = data.data.split("_")[-1]

        try:
            if '@' in username:
                user = database.User.select().where(
                    (database.User.username == username.replace("@", ""))).get()
            else:
                user = database.User.select().where(
                    (database.User.id == username)).get()
        except Exception as error:
            logging.error(str(error), exc_info=True)
            return bot.send_message(data.from_user.id, "Este usuário não existe.")

        user_id = str(user.id)
        identification_document = database.IdentificationDocument.select().where(
            (database.IdentificationDocument.user == str(user_id)) &
            (database.IdentificationDocument.document_type == "CPF")) 
        if not identification_document.exists():
            identification_document_id = None
            identification_document_name = None
            identification_document_status = None
        else:
            identification_document = identification_document.get()
            identification_document_id = identification_document.document_number
            identification_document_name = identification_document.document_name
            identification_document_status = identification_document.status

        if not identification_document_name:
            identification_document_name = user.first_name

        keyboard = InlineKeyboardMarkup(row_width=2)
        if user.is_blocked:
            keyboard.add(
                InlineKeyboardButton(
                    "Desbloquear", callback_data=f"BLOCK_{user_id}"
                )
            )
        else:
            keyboard.add(
                InlineKeyboardButton(
                    "Bloquear", callback_data=f"UNLOCK_{user_id}"
                )
            )

        if identification_document_status == "approved":
            keyboard.add(
                InlineKeyboardButton(
                    "Rejeitar Conta", callback_data=f"REJECT_ACCOUNT_{user_id}"
                )
            )

        if identification_document_status == "rejected":
            keyboard.add(
                InlineKeyboardButton(
                    "Aprovar Conta", callback_data=f"APPROVE_ACCOUNT_{user_id}"
                )
            )
                
        if identification_document_status == "pending":
            keyboard.add(
                InlineKeyboardButton(
                    "Aprovar Conta", callback_data=f"APPROVE_ACCOUNT_{user_id}"
                )
            )
            keyboard.add(
                InlineKeyboardButton(
                    "Rejeitar Conta", callback_data=f"REJECT_ACCOUNT_{user_id}"
                )
            )

        if user.is_operation:
            keyboard.add(
                InlineKeyboardButton(
                    "Desativar Operador", callback_data=f"OPERATOR_DISABLE_{user_id}"
                )
            )
        else:
            keyboard.add(
                InlineKeyboardButton(
                    "Ativa Operador", callback_data=f"OPERATOR_ACTIVE_{user_id}"
                )
            )

        if user.is_partner:
            keyboard.add(
                InlineKeyboardButton(
                    "Desativar Parceiro", callback_data=f"PARTNER_DISABLE_{user_id}"
                )
            )
        else:
            keyboard.add(
                InlineKeyboardButton(
                    "Ativa Parceiro", callback_data=f"PARTNER_ACTIVE_{user_id}"
                )
            )

        total_order = ( 
            database.RampBUYAndSELL.select().where(
                (database.RampBUYAndSELL.user == user_id) &
                (database.RampBUYAndSELL.status == "settled")
            ).count()
        )

        try:
            affiliate_code = user.affiliate_code
        except:
            affiliate_code = None

        message = "<b>Informações de usuário</b>\n\n"
        message+= f"<b>Usuário:</b> <code>{user.username}</code>\n"
        message+= f"<b>E-mail:</b> <code>{user.email}</code>\n"
        message+= f"<b>Nome:</b> <code>{identification_document_name}</code>\n"
        message+= f"<b>Data de Nascimento</b> <code>{user.date_of_birth}</code>\n"
        message+= f"<b>CPF:</b> <code>{format_cpf(identification_document_id)}</code>\n"
        message+= f"<b>Status da conta:</b> <code>{identification_document_status}</code>\n"
        message+= f"<b>Total de ordens:</b> <code>{total_order}</code>\n"
        message+= f"<b>Código Afiliado:</b> <code>{affiliate_code}</code>\n"
        message+= f"<b>Criação de conta:</b> {user.created_at.strftime('%d/%m/%Y %H:%M:%S')}\n\n"   
        message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
        bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def active_or_disable_operator(data: Message, bot: TeleBot):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        user_id = data.data.split("_")[-1]
        user = database.User.select().where(
            (database.User.id == user_id)).get()
        if user.is_operation:
            user.is_operation = False
            user.save()

            message = f"Usuário @{user.username} foi removido como operador com sucesso.\n\n"
            message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            return bot.send_message(data.from_user.id, message)
        else:
            user.is_operation = True
            user.save()

            message = f"Usuário @{user.username} foi adicionado como operador com sucesso.\n\n"
            message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            return bot.send_message(data.from_user.id, message)

    def active_or_disable_partner(data: Message, bot: TeleBot):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        user_id = data.data.split("_")[-1]
        user = database.User.select().where(
            (database.User.id == user_id)).get()
        if user.is_partner:
            user.is_partner = False
            user.is_affiliate = False
            user.save()

            message = f"Usuário @{user.username} foi removido como parceiro com sucesso.\n\n"
            message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            return bot.send_message(data.from_user.id, message)
        else:
            user.is_partner = True
            user.is_affiliate = True
            user.save()

            message = f"Usuário @{user.username} foi adicionado como parceiro com sucesso.\n\n"
            message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            return bot.send_message(data.from_user.id, message)

    def approve_or_reject_document_user(data: Message, bot: TeleBot):
        """
        Approve or reject a user's identification document and send a confirmation message.

        Args:
            data (telebot.types.Message): The received message object.
            bot (telebot.TeleBot): The Telegram bot object.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        user_id = data.data.split("_")[-1]
        identification_document = database.IdentificationDocument.select().where(
            (database.IdentificationDocument.user == str(user_id)) &
            (database.IdentificationDocument.document_type == "CPF")) 
        if not identification_document.exists():
            return bot.send_message(data.from_user.id, "Este usuário não tem documentos a serem aprovados.")
        else:
            identification_document = identification_document.get()
        
        if data.data.split("_")[0].upper() == "APPROVE":
            identification_document.status = "approved"
            identification_document.save()

            message = f"Usuário @{identification_document.user.username} foi aprovado com sucesso.\n\n"
            message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            bot.send_message(data.from_user.id, message)
            Notify.notify_user_status_verification(bot, "approved", identification_document.user.id)
        else:
            identification_document.status = "rejected"
            identification_document.save()
    
            message = f"Usuário @{identification_document.user.username} foi rejeitado com sucesso.\n\n"
            message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            bot.send_message(data.from_user.id, message)
            Notify.notify_user_status_verification(bot, "rejected", identification_document.user.id)
        
    def block_or_unlock_user(data: Message, bot: TeleBot):
        """
        Block or unlock a user based on the callback data and send a confirmation message.

        Args:
            data (telebot.types.Message): The received message object.
            bot (telebot.TeleBot): The Telegram bot object.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        user_id = data.data.split("_")[-1]
        user = database.User.select().where(
            (database.User.id == user_id)).get()
        if user.is_admin:
            return bot.send_message(data.from_user.id, "Não é possível obter informações sobre administradores.")
        
        if user.is_blocked:
            user.is_blocked = False
            user.save()

            message = f"Usuário @{user.username} foi desbloqueado com sucesso.\n\n"
            message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            return bot.send_message(data.from_user.id, message)
        else:
            user.is_blocked = True
            user.save()

            message = f"Usuário @{user.username} foi bloqueado com sucesso.\n\n"
            message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            return bot.send_message(data.from_user.id, message)
