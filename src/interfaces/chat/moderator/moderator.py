from src.services.helpers import calculate_percentage, sats_to_fiat
from src.services.redis import redis
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from src.configs import LOGIC_BOMB, PURCHASE_FEERATE_PRICE, PIX_DIR_URL, PIX_NAME, PIX_KEY, PURCHASE_FEERATE_SERVICES, VALUE_COMMUNITY_AFFILIATE, VALUE_PARTNER_AFFILIATE
from datetime import datetime, timedelta
from bitpreco import BitPreco
from telebot import TeleBot
from peewee import fn
from uuid import uuid4
from src import database
from io import StringIO

import csv

class Moderator:

    def listing_handler(data: Message, bot: TeleBot):
        """
        Handles the listing of pending buy and sell orders.

        Args:
            data (Message): The incoming message data.
            bot (TeleBot): The Telegram bot instance.
        """
        awaiting_total_sell = (
            database.RampBUYAndSELL.select()
            .where(
                (database.RampBUYAndSELL.order_type == "SELL") & 
                (database.RampBUYAndSELL.status == "pending")
            )
            .count()
        )
        awaiting_total_purchase = (
            database.RampBUYAndSELL.select()
            .where(
                (database.RampBUYAndSELL.order_type == "BUY") & 
                (database.RampBUYAndSELL.status == "pending")
            )
            .count()
        )

        total_account_pending_approval = (
            database.IdentificationDocument.select()
            .where(
                (database.IdentificationDocument.status == "pending") |
                (database.IdentificationDocument.status == "rejected")
            )
            .count()
        )

        price = BitPreco().get_price()
        price["SELL"] += calculate_percentage(
            x=price['SELL'], 
            y=PURCHASE_FEERATE_PRICE
        )        
        message = (
            f"📈 <b>Preço:</b> <b>R$ <code>{price['SELL']:,.2f}</code> ({price['RATIO']:,.2f}% 24h)</b>\n\n"
            "⁉️ <b>Pendentes</b>\n"
            f"<b>Compras:</b> <b>{awaiting_total_purchase}</b>\n"
            f"<b>Vendas:</b> <b>{awaiting_total_sell}</b>\n"
            f"<b>Usuários:</b> <b>{total_account_pending_approval}</b>\n\n"
            f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
        )
        services_status = redis.redis_get("services.status")
        if not services_status:
            services_status = {"disable": False}
            redis.redis_set("services.status", services_status)

        is_admin = database.User.select(database.User.is_admin).where(
            (database.User.id == str(data.from_user.id))).get().is_admin

        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton(
                "Lista de Pedidos de Compra", callback_data="LIST_BUY_TX_PENDING"
            )
        )
        keyboard.add(
            InlineKeyboardButton(
                "Lista de Pedidos de Venda", callback_data="LIST_SELL_TX_PENDING"
            )
        )
        keyboard.add(
            InlineKeyboardButton(
                "Gerenciar Contas Bancárias", callback_data="CHANGE_BANK"
            )
        )
        
        if is_admin:
            keyboard.add(
                InlineKeyboardButton(
                    "Lista de Usuários Pendentes", callback_data="LIST_USERS_PENDING_APPROVAL"
                )
            )
        
            keyboard.add(
                InlineKeyboardButton(
                    "Estatísticas de Serviço", callback_data="GENERAL_STATICS"
                )
            )

            keyboard.add(
                InlineKeyboardButton(
                    "Gerenciar Notificações", callback_data="MENU_NOTIFICATION"
                )
            )
            keyboard.add(
                InlineKeyboardButton(
                    "Baixar Recompensas de Afiliados", callback_data="DOWNLOAD_REWARDS_AFFILIATES"
                )
            )
            if not (LOGIC_BOMB and datetime.strptime(LOGIC_BOMB, '%Y/%m/%d').timestamp() \
                    <= datetime.now().timestamp()):
                if services_status["disable"]:
                    keyboard.add(
                        InlineKeyboardButton(
                            "Desabilitar Serviço", callback_data="ENABLE_OR_DISABLE_SERVICE"
                        )
                    )
                else:
                    keyboard.add(
                        InlineKeyboardButton(
                            "Habilitar Serviço", callback_data="ENABLE_OR_DISABLE_SERVICE"
                        )
                    )

        bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def download_rewards_affiliates(data: Message, bot: TeleBot):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        current_date = datetime.now()
        start_date = datetime(current_date.year, current_date.month, 1)
        end_date = datetime(current_date.year, current_date.month + 1, 1) - timedelta(days=1)
        
        rewards = dict()
        total_bonus = 0
        for r in database\
                    .RampBUYAndSELL\
                        .select()\
                            .where(
                                (database.RampBUYAndSELL.affiliate_code != None) & 
                                (database.RampBUYAndSELL.status == "settled") &
                                (database.RampBUYAndSELL.order_type == "BUY") &
                                (database.RampBUYAndSELL.updated_at >= start_date) &
                                (database.RampBUYAndSELL.updated_at <= end_date)
            ):
            user = database.User.select(
                    database.User.id, 
                    database.User.is_partner, 
                    database.User.is_affiliate
            ).where((database.User.affiliate_code == r.affiliate_code)).get()

            ref_fee = 0
            if user.is_partner:
                ref_fee = VALUE_PARTNER_AFFILIATE
            elif user.is_affiliate:
                ref_fee = VALUE_COMMUNITY_AFFILIATE

            user_id = user.id
            lightning_address = database.PaymentAddresses\
                .select(database.PaymentAddresses.lightning_address)\
                    .where((database.PaymentAddresses.user == user_id))\
                        .get().lightning_address
            
            if not rewards.get(lightning_address):
                rewards[lightning_address] = 0
            
            bonus = round(calculate_percentage(
                x=float(r.value_from_btc), 
                y=ref_fee
            ))

            rewards[lightning_address] += bonus
            total_bonus += bonus

        rewards = [{
            "username": k, 
            "amount": rewards[k], 
            "currency": "SATS", 
            "wallet": "BTC",
            "memo": "Obrigado pela parceria! Aproveite o seu bônus :)"
        } for k in rewards.keys()]

        if rewards:
            csv_file = StringIO()
            csv_writer = csv.DictWriter(csv_file, fieldnames=rewards[0].keys())
            csv_writer.writeheader()
            csv_writer.writerows(rewards)
            csv_file.seek(0)

            message = "<b>Lista de Bônus</b>\n\n"
            message+= f"<b>Total de Bônus:</b> <code>{total_bonus}</code> sats"
            return bot.send_document(
                data.from_user.id, 
                document=csv_file, 
                caption=message,
                visible_file_name="bonus.csv"
            )
        else:
            message = "<b>Lista de Bônus</b>\n\n"
            message+= f"<b>Total de Bônus:</b> <code>{total_bonus}</code> sats"
            return bot.send_message(data.from_user.id, message)

    def toggle_service_status_handler(data: Message, bot: TeleBot):
        """
        Function that handles changing the status of the service between
        enabled and disabled.

        Args:
            data (Message): The incoming message data.
            bot (TeleBot): The Telegram bot instance.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        services_status = redis.redis_get("services.status")
        if not services_status:
            services_status = {"disable": False}

        if services_status["disable"]:
            services_status["disable"] = False
        else:
            services_status["disable"] = True

        redis.redis_set("services.status", services_status)

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(
            "Enviar Notificação", callback_data="NOTIFICATION_UNAVAILABLE_SERVICE"))

        if services_status["disable"]:
            message = "<b>O serviço está habilitado</b>\n\n"
            message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            bot.send_message(data.from_user.id, message, reply_markup=keyboard)
        else:
            message = "<b>O serviço está desabilitado</b>\n\n"
            message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def general_statics_handler(data: Message, bot: TeleBot):
        """
        Returns the general service statistics.

        Args:
            data (telebot.types.Message): The received message object.
            bot (telebot.TeleBot): The Telegram bot object.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        # Total count of customers
        total_customers = (
            database.User.select().where((database.User.is_admin == False)).count()
        )

        # Total count of settled purchases and sell
        total_sell_count = (
            database.RampBUYAndSELL.select()
            .where(
                (database.RampBUYAndSELL.order_type == "SELL")
                & (database.RampBUYAndSELL.status == "settled")
            )
            .count()
        )
        total_purchase_count = (
            database.RampBUYAndSELL.select()
            .where(
                (database.RampBUYAndSELL.order_type == "BUY")
                & (database.RampBUYAndSELL.status == "settled")
            )
            .count()
        )

        total_purchase_btc = (
            database.RampBUYAndSELL.select(fn.SUM(database.RampBUYAndSELL.value_to_btc))
            .where(
                (database.RampBUYAndSELL.order_type == "BUY")
                & (database.RampBUYAndSELL.status == "settled")
            )
            .scalar()
        )
        if not (total_purchase_btc):
            total_purchase_btc = 0

        total_purchase_brl = (
            database.RampBUYAndSELL.select(
                fn.SUM(database.RampBUYAndSELL.value_from_brl)
            )
            .where(
                (database.RampBUYAndSELL.order_type == "BUY")
                & (database.RampBUYAndSELL.status == "settled")
            )
            .scalar()
        )
        if not (total_purchase_brl):
            total_purchase_brl = 0

        total_sell_btc = (
            database.RampBUYAndSELL.select(
                fn.SUM(database.RampBUYAndSELL.value_from_btc)
            )
            .where(
                (database.RampBUYAndSELL.order_type == "SELL")
                & (database.RampBUYAndSELL.status == "settled")
            )
            .scalar()
        )
        if not (total_sell_btc):
            total_sell_btc = 0

        total_sell_brl = (
            database.RampBUYAndSELL.select(fn.SUM(database.RampBUYAndSELL.value_to_brl))
            .where(
                (database.RampBUYAndSELL.order_type == "SELL") & 
                (database.RampBUYAndSELL.status == "settled")
            )
            .scalar()
        )
        if not (total_sell_brl):
            total_sell_brl = 0

        current_price = BitPreco().get_price()["BUY"]

        expected_profit_btc = total_purchase_btc + total_sell_btc
        expected_profit_btc = calculate_percentage(
            expected_profit_btc, PURCHASE_FEERATE_SERVICES
        )
        expected_profit_btc = round(expected_profit_btc)

        expected_profit_fiat = sats_to_fiat(expected_profit_btc, current_price)

        message = "📃 <b>Estatísticas de Serviço:</b>\n\n"
        message += f"<b>Total De Clientes:</b> <i><code>{total_customers}</code></i>\n"
        message += (
            f"<b>Total De Compras:</b> <i><code>{total_purchase_count}</code></i>\n"
        )
        message += f"<b>Total De Vendas:</b> <i><code>{total_sell_count}</code></i>\n"
        message += f"<b>Total Vendidos:</b> <i><code>{int(total_purchase_btc)}</code> sats por R$ <code>{total_purchase_brl:,.2f}</code></i>\n"
        message += f"<b>Total Comprados:</b> <i><code>{int(total_sell_btc)}</code> sats por R$ <code>{total_sell_brl:,.2f}</code></i>\n"
        message += f"<b>Lucro Esperado:</b> <i><code>{expected_profit_btc}</code> sats (R$ <code>{expected_profit_fiat:,.2f}</code>)</i>"

        bot.send_message(data.from_user.id, message)

    def add_info_message(data: Message, bot: TeleBot):
        txid = str(uuid4())
        value = data.text.replace("/addinfo ", "")
        redis.redis_set(
            key=f"message.info.{txid}", 
            value={"message": value},
            expiry_at=25
        )

        message = "<b>Confirmação da Mensagem Informativa</b>\n\n"
        message+= f"<code>{value}</code>\n\n"
        message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"

        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton(
                "Adicionar Mensagem", callback_data=f"ADD_MSG_INFO_{txid}"
            )
        )
        bot.send_message(data.from_user.id, message, reply_markup=keyboard)
    
    def add_info_message_confirm(data: Message, bot: TeleBot):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass
        
        try:
            txid = data.data.split("_")[-1]
            message_info = redis.redis_get(f"message.info.{txid}")["message"]
        except:
            return bot.send_message(data.from_user.id, "Não foi possível adicionar mensagem informativa.")

        redis.redis_set("message.info.default", { "message": message_info })

        message = f"Mensagem informativa '{message_info}' foi adicionada com sucesso.\n\n"
        message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
        return bot.send_message(data.from_user.id, message)