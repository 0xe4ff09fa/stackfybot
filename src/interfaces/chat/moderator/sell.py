from src.services.helpers import format_cpf
from src.services.redis import redis
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from datetime import datetime
from telebot import TeleBot
from src import database

import logging

class Sell:

    def sell_listing_handler(data: Message, bot: TeleBot):
        """
        Handles the display of a list of pending sells awaiting approval.

        Args:
            data (Message): The message data received from the user.
            bot (TeleBot): The TeleBot instance used to interact with the Telegram Bot API.

        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        message = (
            "<b>Lista de vendas pendentes aguardando aprovação.</b>\n\n"
            "Para acessar qualquer uma das transações, clique no botão correspondente abaixo:"
        )

        keyboard = InlineKeyboardMarkup()
        for ramp in (
            database.RampBUYAndSELL.select(database.RampBUYAndSELL.id)
            .where(
                (database.RampBUYAndSELL.order_type == "SELL")
                & (database.RampBUYAndSELL.status == "pending")
            )
            .order_by(database.RampBUYAndSELL.value_from_brl.asc())
        ):
            txid = str(ramp.id)
            label = txid.split(":")[-1][:16]
            keyboard.add(InlineKeyboardButton(label, callback_data=f"SELL_TX_{txid}"))

        bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def sell_get_tx_pending(data: Message, bot: TeleBot):
        """
        Retrieves and displays the details of a pending transaction for a sell.

        Args:
            data (Message): The message data received from the user.
            bot (TeleBot): The TeleBot instance used to interact with the Telegram Bot API.
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

        try:
            address = redis.redis_get(f"tx.address.{txid}")["pix_code"]
        except:
            address = None

        if not address:
            try:
                address = database.RampAddressInfo.select(database.RampAddressInfo.address).where(
                    (database.RampAddressInfo.ramp == txid)).get().address
            except Exception as error:
                logging.error(str(error), exc_info=True)
        
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
    
        total_sell = (
            database.RampBUYAndSELL.select().where(
                (database.RampBUYAndSELL.user == ramp.user.id) &
                (database.RampBUYAndSELL.order_type == "SELL") &
                (database.RampBUYAndSELL.status == "settled")
            ).count()
        )

        message = (
            "<b>[Venda] Detalhes de Pedido:</b>\n\n"
            f"<b>Usuário:</b> <i>@{ramp.user.username}</i>\n"
            f"<b>Nome:</b> <i><code>{ramp.user.first_name}</code></i>\n"
            f"<b>CPF:</b> <i><code>{format_cpf(identification_document_id)}</code></i>\n"
            f"<b>Total de Vendas:</b> <code>{total_sell}</code>\n"
            f"<b>Criação de conta:</b> {ramp.user.created_at.strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"<b>Quantidade:</b> R$ <code>{ramp.value_to_brl:,.2f}</code> <i>({int(ramp.value_from_btc)} sats)</i>\n"
            f"<b>Preço:</b> <i>R$ <code>{ramp.price_services:,.2f}</code></i>\n"
            f"<b>ID:</b> <code>{ramp.identifier}</code>\n"
            f"<b>Endereço de Pagamento:</b> <i><code>{address}</code></i>\n\n"
            f"<b>Txid:</b> <code>{txid}</code>\n\n"
            f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
        )

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                "Finalizar Venda", callback_data=f"SELL_TX_FINALIZE_{txid}"
            )
        )
        keyboard.add(
            InlineKeyboardButton(
                "Cancelar Venda", callback_data=f"SELL_TX_CANCEL_{txid}"
            )
        )
        return bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def sell_tx_pending_settled_options(data: Message, bot: TeleBot):
        """
        Displays options to confirm or cancel the finalization of a pending sale transaction.

        Args:
            data (Message): The message data received from the user.
            bot (TeleBot): The TeleBot instance used to interact with the Telegram Bot API.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        txid = data.data.split("_")[-1]

        message = "<b>Você tem certeza de que deseja finalizar esta venda?</b>"

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                "Sim, Finalizar Venda", callback_data=f"SELL_TX_FINALIZE_CONFIRM_{txid}"
            )
        )
        keyboard.add(
            InlineKeyboardButton(
                "Não, Voltar", callback_data=f"SELL_TX_FINALIZE_CANCEL_{txid}"
            )
        )

        bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def sell_tx_pending_cancel_options(data: Message, bot: TeleBot):
        """
        Displays options to confirm or cancel the cancellation of a pending sale transaction.

        Args:
            data (Message): The message data received from the user.
            bot (TeleBot): The TeleBot instance used to interact with the Telegram Bot API.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        txid = data.data.split("_")[-1]

        message = "<b>Você tem certeza de que deseja cancelar esta venda?</b>"

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                "Sim, Cancelar Compra", callback_data=f"SELL_TX_CANCEL_CONFIRM_{txid}"
            )
        )
        keyboard.add(
            InlineKeyboardButton(
                "Não, Voltar", callback_data=f"SELL_TX_CANCEL_CANCEL_{txid}"
            )
        )

        bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def sell_tx_pending_finalize_confirm(data: Message, bot: TeleBot):
        """
        Confirms the finalization of a pending sale transaction.

        Args:
            data (Message): The message data received from the user.
            bot (TeleBot): The TeleBot instance used to interact with the Telegram Bot API.
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
            ramp.status = "settled"
            ramp.save()

            bot.send_message(
                data.from_user.id,
                "<b>🔺 Transação de venda aprovada com sucesso </b>✅\n\n"
                "<b>Dados da transação:</b>\n\n"
                f"<b>Usuário:</b> <i>@{ramp.user.username}</i>\n"
                f"<b>Total vendido:</b> <i><code>{int(ramp.value_from_btc)}</code> sats</i>\n"
                f"<b>Preço:</b> R$ <i><code>{ramp.price_services:,.2f}</code></i>\n"
                f"<b>Total enviado:</b> <i>R$ <code>{ramp.value_to_brl:,.2f}</code></i>\n\n"
                f"<b>Txid:</b> <i><code>{txid}</code></i>\n\n"
                f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            )

            message = (
                "<b>Venda concluída com sucesso </b>✅\n\n"
                f"<b>Total vendido:</b> <i><code>{int(ramp.value_from_btc)}</code> sats</i>\n"
                f"<b>Total recebido:</b> <i>R$ <code>{ramp.value_to_brl:,.2f}</code></i>\n"
                f"<b>Preço:</b> R$ <i><code>{ramp.price_services:,.2f}</code></i>\n\n"
                f"💸 Seu codigo de pagamento no valor de R$ <i><code>{ramp.value_to_brl:,.2f}</code></i> foi pago com sucesso!\n\n"
                f"<b>Txid:</b> <i><code>{txid}</code></i>\n\n"
                f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            )
            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton(
                    f"Realizar Nova Venda", callback_data=f"MENU_CUSTOMER"
                )
            )
            with open("src/assets/sell-confirmed-tx.jpg", "rb") as f:
                bot.send_photo(ramp.user.id, f, caption=message, reply_markup=keyboard)

    def sell_tx_pending_cancel_confirm(data: Message, bot: TeleBot):
        """
        Confirms the cancellation of a pending sale transaction.

        Args:
            data (Message): The message data received from the user.
            bot (TeleBot): The TeleBot instance used to interact with the Telegram Bot API.
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

            bot.send_message(
                data.from_user.id,
                (
                    "<b>Transação de venda cancelada com sucesso.</b>\n\n"
                    f"<b>Txid:</b> <code>{txid}</code>"
                ),
            )

    def sell_tx_pending_settled_or_cancel_cancel(data: Message, bot: TeleBot):
        """
        Handles the cancellation of settled or canceled sale transactions.

        Args:
            data (Message): The message data received from the user.
            bot (TeleBot): The TeleBot instance used to interact with the Telegram Bot API.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        Sell.sell_get_tx_pending(data, bot)

