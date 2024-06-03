from src.interfaces.chat.notify import Notify
from src.middlewares.features import featuresEnabled
from src.services.bitfinex import bitfinex
from src.services.helpers import sats_to_btc
from src.services.redis import redis
from src.services.quote import Quote
from telebot.types import (
    ForceReply,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
)
from src.services import lightning
from src.configs import (
    FEERATE_PROVIDER,
    HISTORY_CHANNEL_ID,
    SELL_FEERATE_PRICE,
    SELL_FEERATE_SERVICES,
    PRODUCTION,
    SELL_LISTING,
    SELL_MAX_VALUE,
    SELL_MIN_VALUE,
    SUPPORT_CHANNEL,
)
from datetime import datetime, timedelta
from telebot import TeleBot
from qrcode import QRCode
from pix import Pix
from src import database
from io import BytesIO

import logging

# Initialize Quote
quote = Quote(redis=redis)

class SELL:

    @featuresEnabled("FEATURE_SELL")
    def sell_listing_handler(data: Message, bot: TeleBot):
        """
        Handles the sell listing message.
        Displays the steps for making a sell and the available sell values.

        Args:
            data (Message): The message data.
            bot (TeleBot): The Telegram bot object.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        message = (
            "⚡️💸 <b><i>Escolha uma das opções para realizar uma venda:</i></b>\n\n"
        )
        keyboard = InlineKeyboardMarkup()
        for value in sorted([float(x) for x in SELL_LISTING], reverse=True):
            keyboard.add(
                InlineKeyboardButton(
                    f"R$ {float(value):,.2f}", callback_data=f"SELL_VALUE_{value}"
                )
            )
        
        keyboard.add(InlineKeyboardButton("Personalizar valor", callback_data="SELL_VALUE_CUSTOM"))
        with open("src/assets/select-value-sell.jpg", "rb") as f:
            bot.send_photo(data.from_user.id, f, caption=message, reply_markup=keyboard)

    @featuresEnabled("FEATURE_SELL")
    def sell_select_value_handler(data: Message, bot: TeleBot):
        """Handles the selection of a value for a sell.

        Args:
            data (Message): The message data.
            bot (TeleBot): The Telegram bot object.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        value = float(data.data.split("_")[-1])

        sell_details = quote.make_sell(
            value=value,
            fees={
                "services": SELL_FEERATE_SERVICES,
                "provider": FEERATE_PROVIDER,
                "price": SELL_FEERATE_PRICE,
            }
        )
        sell_details = quote.create_sell(sell_details)
        database.RampBUYAndSELL.create(
            id=sell_details["txid"],
            user=str(data.from_user.id),
            status="created",
            order_type="SELL",
            value_from_btc=sell_details["values"]["from"]["btc"],
            value_from_brl=sell_details["values"]["from"]["brl"],
            value_to_btc=sell_details["values"]["to"]["btc"],
            value_to_brl=sell_details["values"]["to"]["brl"],
            price_services=sell_details["prices"]["services"],
            price_provider=sell_details["prices"]["provider"],
            fee_value=sell_details["fees"]["value"],
            fee_rate_price=sell_details["fees"]["rate"]["price"],
            fee_rate_services=sell_details["fees"]["rate"]["services"],
            fee_rate_provider=sell_details["fees"]["rate"]["provider"],
            identifier=sell_details["identifier"],
            expiry_at=datetime.now() + timedelta(minutes=60),
        )
        message = (
            "📄 <b>Confirme sua venda com as seguintes condições:</b>\n\n"
            f"<b>Valor de venda:</b> R$ <i><code>{sell_details['values']['to']['brl']:,.2f}</code></i>\n"
            f"<b>Preço:</b> <i>R$ <code>{sell_details['prices']['services']:,.2f}</code></i>\n"
            f"<b>Taxa:</b> R$ <i><code>{sell_details['values']['from']['brl'] - sell_details['values']['to']['brl']:,.2f}</code></i>\n"
            f"<b>Total vendido:</b> <i><code>{int(sell_details['values']['from']['btc'])}</code></i> sats\n\n"
            "⚠️ <b>Atenção!</b>\n\n"
            f"Crie um código de cobrança PIX com o valor de R$ <code>{sell_details['values']['to']['brl']:,.2f}</code> no seu Internet Banking e responda a esta mensagem.\n\n"
            f"<b>Txid:</b> <code>{sell_details['txid']}</code>\n"
        )

        user_id = str(data.from_user.id)
        tx = redis.redis_get(f"user.{data.from_user.id}")
        if not tx:
            redis.redis_set(
                f"user.{user_id}",
                {
                    "id": user_id,
                    "tx": {
                        "purchase": {
                            "txid": None,
                        },
                        "sell": {"txid": sell_details["txid"]},
                    },
                },
            )
        else:
            tx["tx"]["sell"]["txid"] = sell_details["txid"]
            redis.redis_set(f"user.{user_id}", tx)

        with open("src/assets/send-invoice-pix.jpg", "rb") as f:
            bot.send_photo(data.from_user.id, f, caption=message)

    @featuresEnabled("FEATURE_SELL")
    def sell_select_currency_handler(data: Message, bot: TeleBot):
        """
        Handles the addition of a sell pix code.

        Args:
            data (Message): The received message data.
            bot (TeleBot): The TeleBot instance.
        """
        pix_code = data.text.strip()
        try:
            txid = data.reply_to_message.text.split("\n\n")[-1].split(" ")[-1]
        except:
            txid = redis.redis_get(f"user.{data.from_user.id}")["tx"]["sell"]["txid"]

        tx = redis.redis_get(f"tx.{txid}")
        if not (tx):
            message = f"Sua transação de venda expirou. Por favor, realize uma nova compra ou entre em contato com o suporte @{SUPPORT_CHANNEL} para mais informações."
            return bot.send_message(data.from_user.id, message)

        redis.redis_update(f"tx.{txid}", { "pix_code": pix_code })

        message = "<b>Por favor, selecione a moeda que você usará para efetuar o pagamento via chave PIX.</b>"
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                "BTC (LN)", callback_data=f"SELL_SELECT_BTC_{txid}"
            )
        )
        keyboard.add(
            InlineKeyboardButton(
                "L-USDT (Liquid)", callback_data=f"SELL_SELECT_LUSDT_{txid}"
            )
        )
        return bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    @featuresEnabled("FEATURE_SELL")
    def sell_add_address_handler(data: Message, bot: TeleBot):
        """
        Handles the addition of a sell pix code.

        Args:
            data (Message): The received message data.
            bot (TeleBot): The TeleBot instance.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass
        
        try:
            txid = data.reply_to_message.text.split("\n\n")[-1].split(" ")[-1]
        except:
            txid = redis.redis_get(f"user.{data.from_user.id}")["tx"]["sell"]["txid"]

        tx = redis.redis_get(f"tx.{txid}")
        if not (tx):
            message = f"Sua transação de venda expirou. Por favor, realize uma nova compra ou entre em contato com o suporte @{SUPPORT_CHANNEL} para mais informações."
            return bot.send_message(data.from_user.id, message)

        pix_code = tx["pix_code"]
        if Pix().decode(pix_code)["amount"] != tx["values"]["to"]["brl"]:
            message = "O valor do código de pagamento PIX não corresponde ao valor de venda. "
            message += f"Crie um novo código com o valor {tx['values']['to']['brl']:.2f} e envie abaixo para continuar.\n\n"
            message += f"<b>Txid:</b> <code>{txid}</code>\n\n"
            message += f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            return bot.send_message(data.from_user.id, message)

        currency_payment = data.data.split("SELL_SELECT_")[-1].split("_")[0]
        if currency_payment == "BTC":
            invoice = lightning.addinvoice(tx["values"]["from"]["btc"], f'SELL-{txid}')
            payment_request = invoice["payment_request"]
            if invoice.get("hash"):
                payment_hash = invoice['hash']
            else:
                payment_hash = invoice['r_hash']

            redis.redis_set(
                key=f"tx.address.{txid}",
                value={
                    "payment_request": payment_request,
                    "payment_hash": payment_hash,
                    "network": currency_payment,
                    "pix_code": pix_code,
                },
                expiry_at=60 * 60,
            )

            qrcode = QRCode()
            qrcode.add_data(payment_request)
            qrcode.make(fit=True)

            stream = BytesIO()
            image = qrcode.make_image(fill_color="black", back_color="white")
            image.save(stream, "PNG")
            image = stream.getvalue()

            expiration_time = datetime.now() + timedelta(minutes=15)
            expiration_formatted = expiration_time.strftime("%H:%M")

            message = (
                "<b>⏳⚡️ Efetue o pagamento do invoice lightning utilizando o QRCODE ou a Fatura (copie e cole). Em seguida, clique no botão abaixo.</b>\n\n"
                f"<code>{payment_request}</code>\n\n"
                "<b>Prazo:</b> <i>15 Minutos</i>\n"
                f"<b>Expira às:</b> <i>{expiration_formatted}</i>\n\n"
                f"<b>Txid:</b> <code>{txid}</code>\n\n"
                f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            )

            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton(
                    "Confirmar Pagamento", callback_data=f"CONFIRM_PAYMENT_INVOICE_{txid}"
                )
            )
            bot.send_photo(data.from_user.id, stream.getvalue(), caption=message, reply_markup=keyboard)

        elif currency_payment == "LUSDT":
            address_usdt = bitfinex.deposit_address("tetherusl")[-4][-2]
            usdt_value = round(sats_to_btc(tx["values"]["from"]["btc"]) * float(bitfinex.get_price()["SELL"]), 2)
            redis.redis_set(
                key=f"tx.address.{txid}",
                value={
                    "address": address_usdt,
                    "network": currency_payment, 
                    "value": usdt_value,
                    "pix_code": pix_code
                },
                expiry_at=(60 * 60) * 1.5,
            )

            expiration_time = datetime.now() + timedelta(minutes=15)
            expiration_formatted = expiration_time.strftime("%H:%M")
            message = (
                "<b>⏳⚡️ Efetue o pagamento de L-USDT na rede Liquid utilizando o QRCODE ou o Endereço Liquid. Em seguida, clique no botão abaixo.</b>\n\n"
                f"<code>{address_usdt}</code>\n\n"
                f"<b>Valor:</b> $ <code>{usdt_value}</code> USDT\n"
                "<b>Prazo:</b> <i>15 Minutos</i>\n"
                f"<b>Expira às:</b> <i>{expiration_formatted}</i>\n\n"
                f"<b>Txid:</b> <code>{txid}</code>\n\n"
                f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            )
            qrcode = QRCode()
            qrcode.add_data(address_usdt)
            qrcode.make(fit=True)

            stream = BytesIO()
            image = qrcode.make_image(fill_color="black", back_color="white")
            image.save(stream, "PNG")
            image = stream.getvalue()

            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton(
                    "Confirmar Pagamento", callback_data=f"CONFIRM_PAYMENT_ADDRESS_LUSDT_{txid}"
                )
            )
            return bot.send_photo(data.from_user.id, stream.getvalue(), caption=message, reply_markup=keyboard)

    def sell_confirm_payment_invoice(data: Message, bot: TeleBot):
        """
        Confirms the payment for a sell transaction and sends appropriate messages to the user and admins.

        Args:
            data (Message): The message data containing transaction information.
            bot (TeleBot): The Telegram bot instance.
        """
        txid = data.data.split("_")[-1]
        address = redis.redis_get(f"tx.address.{txid}")
        if not (address):
            try:
                bot.delete_message(data.from_user.id, data.message.message_id)
            except:
                pass

            message = f"Sua transação de venda expirou. Por favor, realize uma nova compra ou entre em contato com o suporte @{SUPPORT_CHANNEL} para mais informações.\n\n"
            message += f"<b>Txid:</b> <code>{txid}</code>\n\n"
            message += f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            return bot.send_message(data.from_user.id, message)

        ramp = database.RampBUYAndSELL.select().where(
            (database.RampBUYAndSELL.id == txid) & 
            (database.RampBUYAndSELL.status == "created")
        )
        if ramp.exists() == False:
            try:
                bot.delete_message(data.from_user.id, data.message.message_id)
            except:
                pass

            message = f"Desculpe, não foi possível processar o seu comprovante no momento. Por favor, entre em contato com o suporte através de @{SUPPORT_CHANNEL} para obter assistência.\n\n"
            message += f"<b>Txid:</txid> <code>{txid}</code>\n\n"
            message += f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            return bot.send_message(data.from_user.id, message)
        else:
            ramp = ramp.get()

        if ramp.expiry_at.timestamp() < datetime.now().timestamp():
            try:
                bot.delete_message(data.from_user.id, data.message.message_id)
            except:
                pass

            message = f"Sua transação de compra venda. Por favor, realize uma nova compra ou entre em contato com o suporte @{SUPPORT_CHANNEL} para mais informações.\n\n"
            message += f"<b>Txid:</txid> <code>{txid}</code>\n\n"
            message += f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            return bot.send_message(data.from_user.id, message)

        network = address.get("network")
        if network == "BTC":
            payment_hash = address["payment_hash"]
            payment_status = lightning.check_payment(payment_hash)
            if (PRODUCTION == True) and (payment_status["paid"] == False):
                return None
        else:
            movements = bitfinex.movements(currency="UST")
            if not movements:
                return None

            order_value = address.get("value")
            usdt_address = address.get("address")
            get_movements_with_address = list(filter(lambda data: data[-6] == usdt_address, movements))
            if not get_movements_with_address:
                return None
            else:
                get_movements_with_address = get_movements_with_address[-1]
                movement_status = get_movements_with_address[-13]
                movement_value = float(get_movements_with_address[-10])

            if movement_value < order_value:
                return None

            if movement_status != "COMPLETED":
                return None
        
        ramp.status = "pending"
        ramp.save()
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        with open("src/assets/pay-receive.jpg", "rb") as f:
            try:
                message = "Recebemos seu pagamento.\n\n"
                message += "Não se preocupe, em breve o código PIX será pago.\n\n"
                message += f"Qualquer dúvida entre em contato com nossa equipe @{SUPPORT_CHANNEL}.\n\n"
                message += f"<b>Txid:</b> <code>{txid}</code>\n\n"
                message += f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
                bot.send_photo(data.from_user.id, f, caption=message)
            except:
                pass

        identification_document = database.IdentificationDocument.select().where(
            (database.IdentificationDocument.user == str(data.from_user.id)) &
            (database.IdentificationDocument.document_type == "CPF")) 
        if not identification_document.exists():
            identification_document_id = None
            identification_document_name = None
        else:
            identification_document = identification_document.get()
            identification_document_id = identification_document.document_number
            identification_document_name = identification_document.document_name
        
        if not identification_document_name:
            identification_document_name = data.from_user.first_name
        
        pix_code = address.get("pix_code")
        Notify.notify_sell_order(
            bot,
            txid,
            data.from_user.username,
            int(ramp.value_from_btc),
            float(ramp.value_to_brl),
            ramp.identifier,
            pix_code,
            network,
            identification_document_id,
            identification_document_name,
            HISTORY_CHANNEL_ID
        )

        try:
            database.RampAddressInfo.create(ramp=txid, network="pix", address=pix_code)
        except Exception as error:
            logging.error(str(error), exc_info=True)
        
    @featuresEnabled("FEATURE_SELL")
    def sell_custom_value_handler(data: Message, bot: TeleBot):
        """
        Handles the sell custom value message.
        Asks the user for the desired sell value.

        Args:
            data (Message): The message data.
            bot (TeleBot): The Telegram bot object.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        message = (
            "Forma correta/errada de enviar os valores:\n\n"
            "✅ 25 | 25.01 | 1000 | 1000.99\n"
            "❌ 25,00 | 25,01 | 1.000 | 1.000,99\n\n"
            "Qual valor você deseja vender?\n\n"
            "Por favor, responda esta mensagem com o valor desejado."
        )
        return bot.send_message(
            data.from_user.id, message, reply_markup=ForceReply(selective=False)
        )

    @featuresEnabled("FEATURE_SELL")
    def sell_custom_add_value_handler(data: Message, bot: TeleBot):
        """Handles the custom addition of a value for a sale.

        Args:
            data (Message): The message data.
            bot (TeleBot): The Telegram bot object.
        """
        value = round(float(data.text.replace(",", ".")), 2)
        if value < SELL_MIN_VALUE:
            message = f"Pedimos desculpas pelo inconveniente, mas o valor informado é abaixo do nosso limite de R$ {SELL_MIN_VALUE:,.2f}."
            return bot.send_message(data.from_user.id, message)

        if value > SELL_MAX_VALUE:
            message = f"Pedimos desculpas pelo inconveniente, mas o valor informado ultrapassa nosso limite de R$ {SELL_MAX_VALUE:,.2f}.\nPor favor, tente inserir um valor menor."
            return bot.send_message(data.from_user.id, message)

        message = f"Para prosseguir com a venda no valor de R$ {value:,.2f}, clique no botão abaixo."

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("Continuar", callback_data=f"SELL_VALUE_{value}")
        )
        return bot.send_message(data.from_user.id, message, reply_markup=keyboard)
