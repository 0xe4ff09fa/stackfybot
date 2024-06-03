from src.services.firebase import storage
from src.services.helpers import format_cpf
from src.services.coinos import coinos
from src.services.redis import redis
from src.services.swap import swap
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from src.configs import PRODUCTION
from datetime import datetime
from telebot import TeleBot
from src import database

import logging

class Purchase:

    def purchase_listing_handler(data: Message, bot: TeleBot):
        """Handles the listing of pending purchase orders.

        Args:
            data (Message): The incoming message data.
            bot (TeleBot): The Telegram bot instance.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass
        
        message = (
            "<b>Lista de compras pendentes aguardando aprovação.</b>\n\n"
            "Para acessar qualquer uma das transações, clique no botão correspondente abaixo:"
        )

        try:
            is_admin = (database.User
                        .select(database.User.is_admin)
                        .where((database.User.id == str(data.from_user.id)))).get().is_admin
        except:
            is_admin = False

        keyboard = InlineKeyboardMarkup()
        for ramp in (
            database.RampBUYAndSELL.select(database.RampBUYAndSELL.id, database.RampBUYAndSELL.bank)
            .where(
                (database.RampBUYAndSELL.status == "pending") & 
                (database.RampBUYAndSELL.order_type == "BUY")
            )
            .order_by(database.RampBUYAndSELL.value_from_brl.asc())
        ):
            try:
                operator = database.BankAccount.select().where(
                    (database.BankAccount.alias == ramp.bank)).get().operator
            except:
                operator = None

            txid = str(ramp.id)
            label = txid.split(":")[-1][:16]            
            if operator and operator == str(data.from_user.id):
                keyboard.add(InlineKeyboardButton(label, callback_data=f"BUY_TX_{txid}"))
            elif is_admin == True:
                keyboard.add(InlineKeyboardButton(label, callback_data=f"BUY_TX_{txid}"))

        bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def purchase_get_tx_pending(data: Message, bot: TeleBot):
        """
        Retrieves details of a pending purchase transaction.

        Args:
            data (telebot.types.Message): The received message object.
            bot (telebot.TeleBot): The Telegram bot object.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        txid = data.data.split("_")[-1]
        ramp = database.RampBUYAndSELL.select().where(
            (database.RampBUYAndSELL.id == txid) & 
            (database.RampBUYAndSELL.status == "pending")
        )
        if ramp.exists() == False:
            message = "Tx não encontrado.\n\n"
            message += f"<code>{txid}</code>"
            return bot.send_message(data.from_user.id, message)
        else:
            ramp = ramp.get()
        
        receipt_path = ramp.receipt_path
        if "tg:" in receipt_path:
            receipt_path = receipt_path.replace("tg:", "")
            receipt_type = receipt_path[-3:]
            try:
                receipt = bot.download_file(file_path=receipt_path[:-4])
            except:
                receipt = None
        elif "firebase:" in receipt_path:
            receipt_path = receipt_path.replace("firebase:", "")
            receipt_type = receipt_path[-3:]

            bucket = storage.bucket()
            blob = bucket.blob(receipt_path)
            receipt = blob.download_as_bytes()        
        else:
            receipt = None

        try:
            rampaddress_info = database.RampAddressInfo.select().where(
                (database.RampAddressInfo.ramp == str(ramp.id))).get()
            address = rampaddress_info.address
            network = rampaddress_info.network.title()
        except:
            address = None
            network = None

        if not address:
            address = redis.redis_get(f"tx.address.{txid}") 
            network = address.get("network", "LN").upper()
            address = address.get("payment_request")

        identification_document = database.IdentificationDocument.select().where(
            (database.IdentificationDocument.user == str(ramp.user.id)) &
            (database.IdentificationDocument.document_type == "CPF")) 
        if not identification_document.exists():
            identification_document_id = None
            identification_document_name = None
        else:
            identification_document = identification_document.get()
            identification_document_id = identification_document.document_number
            identification_document_name = identification_document.document_name

        if not identification_document_name:
            identification_document_name = ramp.user.first_name

        total_purchase = (
            database.RampBUYAndSELL.select().where(
                (database.RampBUYAndSELL.user == ramp.user.id) &
                (database.RampBUYAndSELL.order_type == "BUY") &
                (database.RampBUYAndSELL.status == "settled")
            ).count()
        )

        message = (
            f"<b>[Compra] Detalhes de Pedido:</b>\n\n"
            f"<b>Usuário:</b> <i>@{ramp.user.username}</i>\n"
            f"<b>Nome:</b> <i><code>{identification_document_name}</code></i>\n"
            f"<b>CPF:</b> <i><code>{format_cpf(identification_document_id)}</code></i>\n"
            f"<b>Total de Compras:</b> <code>{total_purchase}</code>\n"
            f"<b>Criação de conta:</b> {ramp.user.created_at.strftime('%d/%m/%Y %H:%M:%S')}\n"   
            f"<b>Quantidade:</b> <i><code>{int(ramp.value_to_btc)}</code> sats (R$ {ramp.value_from_brl:,.2f})</i>\n"
            f"<b>Preço:</b> <i>R$ <code>{ramp.price_services:,.2f}</code></i>\n"
            f"<b>Banco:</b> <code>{ramp.bank}</code>\n"
            f"<b>ID:</b> <code>{ramp.identifier}</code>\n"
            f"<b>Rede:</b> <code>{str(network).upper()}</code>\n"
            f"<b>Endereço de Pagamento:</b> <i><code>{address}</code></i>\n\n"
            f"<b>Txid:</b> <code>{txid}</code>\n\n"
            f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
        )

        keyboard = InlineKeyboardMarkup()
        try:
            operator = database.BankAccount.select().where(
                (database.BankAccount.alias == ramp.bank)).get().operator
        except:
            operator = None

        if operator == None or \
                operator == str(data.from_user.id):        
            keyboard.add(
                InlineKeyboardButton(
                    "Finalizar Compra", callback_data=f"BUY_TX_FINALIZE_{txid}"
                )
            )
            keyboard.add(
                InlineKeyboardButton(
                    "Cancelar Compra", callback_data=f"BUY_TX_CANCEL_{txid}"
                )
            )
        
        if receipt:
            if receipt_type == "pdf":
                return bot.send_document(
                    chat_id=data.from_user.id,
                    document=receipt,
                    caption=message,
                    reply_markup=keyboard,
                    visible_file_name="receipt.pdf",
                )
            else:
                return bot.send_photo(
                    chat_id=data.from_user.id,
                    photo=receipt,
                    caption=message,
                    reply_markup=keyboard,
                )
        else:
            return bot.send_message(
                data.from_user.id,
                message,
                reply_markup=keyboard,
            )

    def purchase_tx_pending_settled_options(data: Message, bot: TeleBot):
        """
        Provides options to finalize a pending purchase transaction.

        Args:
            data (telebot.types.Message): The received message object.
            bot (telebot.TeleBot): The Telegram bot object.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        txid = data.data.split("_")[-1]

        message = "<b>Você tem certeza de que deseja finalizar esta compra?</b>"

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                "Sim, Finalizar Compra", callback_data=f"BUY_TX_FINALIZE_CONFIRM_{txid}"
            )
        )
        keyboard.add(
            InlineKeyboardButton(
                "Não, Voltar", callback_data=f"BUY_TX_FINALIZE_CANCEL_{txid}"
            )
        )

        bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def purchase_tx_pending_cancel_options(data: Message, bot: TeleBot):
        """
        Provides options to cancel a pending purchase transaction.

        Args:
            data (telebot.types.Message): The received message object.
            bot (telebot.TeleBot): The Telegram bot object.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        txid = data.data.split("_")[-1]

        message = "<b>Você tem certeza de que deseja cancelar esta compra?</b>"

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                "Sim, Cancelar Compra", callback_data=f"BUY_TX_CANCEL_CONFIRM_{txid}"
            )
        )
        keyboard.add(
            InlineKeyboardButton(
                "Não, Voltar", callback_data=f"BUY_TX_CANCEL_CANCEL_{txid}"
            )
        )

        bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def purchase_tx_pending_finalize_confirm(data: Message, bot: TeleBot):
        """
        Confirms the finalization of a pending purchase transaction.

        Args:
            data (telebot.types.Message): The received message object.
            bot (telebot.TeleBot): The Telegram bot object.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        txid = data.data.split("_")[-1]
        ramp = database.RampBUYAndSELL.select().where(
            (database.RampBUYAndSELL.id == txid) & 
            (database.RampBUYAndSELL.status == "pending")
        )
        if ramp.exists() == False:
            message = "Tx não encontrado.\n\n"
            message += f"<code>{txid}</code>"
            return bot.send_message(data.from_user.id, message)
        else:
            ramp = ramp.get()
            ramp.status = "settled"
            ramp.operator = str(data.from_user.id)
            ramp.save()

        address = redis.redis_get(f"tx.address.{txid}")    
        network = address.get("network", "LN").upper()
        try:
            message = (
                "<b>Transação de compra aprovada com sucesso </b>✅\n\n"
                "<b>Dados da transação:</b>\n\n"
                f"<b>Usuário:</b> <i>@{ramp.user.username}</i>\n"
                f"<b>Valor:</b> R$ <i><code>{ramp.value_from_brl:,.2f}</code></i>\n"
                f"<b>Total comprado:</b> R$ <i><code>{ramp.value_to_brl:,.2f}</code></i>\n"
                f"<b>Preço:</b> R$ <i><code>{ramp.price_services:,.2f}</code></i>\n"
                f"<b>Total enviado:</b> <i><code>{round(ramp.value_to_btc)}</code> sats</i>\n"
                f"<b>Rede:</b> {network}\n"
                f"<b>Endereço:</b> <code>{address.get('address')}</code>\n\n"
                f"<b>Txid:</b> <i><code>{txid}</code></i>\n\n"
                f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            )
            bot.send_message(data.from_user.id, message)
        except Exception as error:
            logging.error(str(error), exc_info=True)

        with open("src/assets/confirmed-tx.jpg", "rb") as f:
            message = (
                "<b>Compra concluída com sucesso </b>✅\n\n"
                "<b>Dados da transação:</b>\n\n"
                f"<b>Total comprado:</b> R$ <i><code>{ramp.value_to_brl:,.2f}</code></i>\n"
                f"<b>Preço:</b> R$ <i><code>{ramp.price_services:,.2f}</code></i>\n\n"
                f"Você recebeu <i><code>{round(ramp.value_to_btc)}</code></i> sats em sua carteira.\n\n"
                f"<b>Txid:</b> <i><code>{txid}</code></i>\n\n"
                f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            )
            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton(
                    f"Realizar Nova Compra", callback_data=f"MENU_CUSTOMER"
                )
            )
            try:
                bot.send_photo(
                    ramp.user.id,
                    f, 
                    caption=message, 
                    reply_markup=keyboard
                )
            except Exception as error:
                logging.error(str(error), exc_info=True)

        if network == "LIQUID":
            try:
                coinos.pay_bitcoin_and_liquid(
                    amount=int(ramp.value_to_btc),
                    address=address["address"]
                )
            except Exception as error:
                logging.error(str(error), exc_info=True)
        elif network == "BTC":
            try:
                swap_id = address.get("swap_id")
                if swap_id:
                    swap.get_swap(swap_id)
            except Exception as error:
                logging.error(str(error), exc_info=True)

    def purchase_tx_pending_cancel_confirm(data: Message, bot: TeleBot):
        """
        Confirms the cancellation of a pending purchase transaction.

        Args:
            data (telebot.types.Message): The received message object.
            bot (telebot.TeleBot): The Telegram bot object.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        txid = data.data.split("_")[-1]
        ramp = database.RampBUYAndSELL.select().where(
            (database.RampBUYAndSELL.id == txid)
            & (database.RampBUYAndSELL.status == "pending")
        )
        if ramp.exists() == False:
            message = "Tx não encontrado.\n\n"
            message += f"<code>{txid}</code>"
            return bot.send_message(data.from_user.id, message)
        else:
            ramp = ramp.get()
            ramp.operator = str(data.from_user.id)
            ramp.status = "cancelled"
            ramp.save()

            message = (
                "ℹ️ <b>Transação de compra cancelada com sucesso.</b>\n\n"
                f"<b>Txid:</b> <code>{txid}</code>\n\n"
                f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            )
            bot.send_message(data.from_user.id, message)

    def purchase_tx_pending_settled_or_cancel_cancel(data: Message, bot: TeleBot):
        """
        Cancels the action to settle or cancel a pending purchase transaction.

        Args:
            data (telebot.types.Message): The received message object.
            bot (telebot.TeleBot): The Telegram bot object.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        Purchase.purchase_get_tx_pending(data, bot)
