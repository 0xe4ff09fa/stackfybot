from src.interfaces.chat.notify import Notify
from src.middlewares.features import featuresEnabled
from src.services.lightning import lnbits
from src.services.helpers import sats_to_fiat
from src.services.coinos import coinos
from src.services.redis import redis
from src.services.quote import Quote
from src.services.bank import BankAccount
from src.services.swap import swap
from telebot.types import (
    ForceReply,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message
)
from src.configs import (
    COINOS_LIQUID_RATE_FEE,
    HISTORY_CHANNEL_ID,
    KYC_INCREASE_LEVEL_BASIC_MAX_VALUE,
    KYC_INCREASE_LEVEL_BASIC_MIN_VALUE,
    KYC_VERIFICATION,
    PIX_NON_TXID,
    PURCHASE_ENABLE_ONCHAIN_VALUE_IN_FIAT,
    PURCHASE_FEERATE_PRICE,
    FEERATE_PROVIDER,
    PURCHASE_FEERATE_SERVICES,
    PIX_KEY,
    PIX_NAME,
    PURCHASE_LISTING,
    PURCHASE_MAX_VALUE,
    PURCHASE_MAX_VALUE_FOR_NEW_USERS,
    PURCHASE_MIN_ORDERS_UNLOCK_LIMIT,
    PURCHASE_MIN_VALUE,
    PURCHASE_WHITELIST_CHANNELS,
    SUPPORT_CHANNEL,
    Features
)

from datetime import datetime, timedelta
from mempool import Mempool
from telebot import TeleBot
from peewee import fn
from qrcode import QRCode
from time import time
from pix import Pix
from src import database
from io import BytesIO

import logging
import random

# Initialize Quote
quote = Quote(redis=redis)

# Initialize Mempool
mempool = Mempool()

class Purchase:

    @featuresEnabled("FEATURE_BUY")
    def purchase_listing_handler(data: Message, bot: TeleBot):
        """
        Handles the purchase listing message.
        Displays the steps for making a purchase and the available purchase values.

        Args:
            data (Message): The message data.
            bot (TeleBot): The Telegram bot object.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        with open("src/assets/select-value-buy.jpg", "rb") as f:
            message = (
                "💸⚡️ <b><i>Escolha uma das opções para realizar uma compra:</i></b>\n\n"
                f"⚠️ Para recebimento on-chain, o valor deve ser superior ou igual ao mínimo de R$ {PURCHASE_ENABLE_ONCHAIN_VALUE_IN_FIAT:,.2f}"
            )
            keyboard = InlineKeyboardMarkup()
            for value in sorted([float(v) for v in PURCHASE_LISTING], reverse=True):
                keyboard.add(
                    InlineKeyboardButton(
                        f"R$ {value:,.2f}", callback_data=f"BUY_VALUE_{value}"
                    )
                )

            keyboard.add(InlineKeyboardButton("Personalizar valor", callback_data="BUY_VALUE_CUSTOM"))
            return bot.send_photo(
                data.from_user.id,
                f, 
                caption=message, 
                reply_markup=keyboard
            )

    @featuresEnabled("FEATURE_BUY")
    def purchase_select_network_handler(data: Message, bot: TeleBot):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        if database.RampBUYAndSELL.select().where(
                (database.RampBUYAndSELL.user == str(data.from_user.id)) &
                (database.RampBUYAndSELL.order_type == "BUY") &
                (database.RampBUYAndSELL.status == "pending")
            ).exists():
            message = f"<b>⚠️ Desculpe, você não pode realizar uma nova compra, pois ainda possui um pedido em aberto.</b>\n\n"
            message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"        
            return bot.send_message(data.from_user.id, message)

        value = float(data.data.split("_")[-1])
        total_orders_purchase = database.RampBUYAndSELL.select().where(
            (database.RampBUYAndSELL.user == str(data.from_user.id)) &
            (database.RampBUYAndSELL.status == "settled")).count()
        if total_orders_purchase < PURCHASE_MIN_ORDERS_UNLOCK_LIMIT \
                and value > PURCHASE_MAX_VALUE_FOR_NEW_USERS:
            message = f"<b>⚠️ Desculpe, você ainda não tem limite para efetuar compras acima de R$ {PURCHASE_MAX_VALUE_FOR_NEW_USERS:,.2f}.</b>\n\n"
            message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"        
            return bot.send_message(data.from_user.id, message)

        keyboard = InlineKeyboardMarkup()
        if KYC_VERIFICATION:
            current_date_time = datetime.now()
            sum_orders_purchase = (
                database.RampBUYAndSELL.select(
                    fn.SUM(database.RampBUYAndSELL.value_from_brl)
                )
                .where(
                    (database.RampBUYAndSELL.user == str(data.from_user.id)) &
                    (database.RampBUYAndSELL.order_type == "BUY") & 
                    (database.RampBUYAndSELL.status == "settled") &
                    (database.RampBUYAndSELL.created_at.year == current_date_time.year) &
                    (database.RampBUYAndSELL.created_at.month == current_date_time.month) &
                    (database.RampBUYAndSELL.created_at.day == current_date_time.day)
                )
                .scalar()
            )
            if not sum_orders_purchase:
                sum_orders_purchase = 0

            sum_orders_purchase += value
            try:
                level = database.User.select(database.User.level).where(
                    (database.User.id == str(data.from_user.id))).get().level
            except Exception as error:
                logging.error(str(error), exc_info=True)
                level = None

            if not level and (sum_orders_purchase >= KYC_INCREASE_LEVEL_BASIC_MIN_VALUE) \
                    and (sum_orders_purchase <= KYC_INCREASE_LEVEL_BASIC_MAX_VALUE):
                message = f"<b>⚠️ Para conseguir comprar R$ {value:,.2f}, você deve aumentar seu nível.</b>\n\n"
                message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
                keyboard.add(InlineKeyboardButton("Aumentar Meu Nível", callback_data="INCREASE_LEVEL_1"))
                with open("src/assets/increase-level.jpg", "rb") as f:
                    return bot.send_photo(
                        data.from_user.id,
                        f, 
                        caption=message, 
                        reply_markup=keyboard
                    )

            if level == "LV1":
                if database.IdentificationDocument.select(
                    database.IdentificationDocument.status
                ).where(
                    (database.IdentificationDocument.user == str(data.from_user.id)) &
                    (database.IdentificationDocument.document_type == "CPF") & 
                    (database.IdentificationDocument.status != "approved")
                ).exists():
                    return bot.send_message(data.from_user.id, "⚠️ Seu pedido de aumento de nível está em análise.")

                if (sum_orders_purchase >= KYC_INCREASE_LEVEL_BASIC_MAX_VALUE):
                    message = f"<b>⚠️ Você atingiu o limite diário de {KYC_INCREASE_LEVEL_BASIC_MAX_VALUE:,.2f}.</b>"
                    message+= "<b>Para continuar comprando, aguarde até amanhã ou use nossa plataforma (Web) https://app.stackfy.xyz</b>\n\n"
                    message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
                    keyboard.add(InlineKeyboardButton("Minha conta", callback_data="MENU_RESUME"))
                    with open("src/assets/limit-exceeded.jpg", "rb") as f:
                        return bot.send_photo(
                            data.from_user.id,
                            f, 
                            caption=message, 
                            reply_markup=keyboard
                        )

        message = "<b>Escolha a rede em que você deseja receber:</b>\n\n"
        if Features().check("FEATURE_BUY_ONCHAIN") and value >= PURCHASE_ENABLE_ONCHAIN_VALUE_IN_FIAT:        
            message+= "<b>⛓️ ON-Chain:</b> Escolhendo essa opção, você pagará um adicional de taxas de rede(Prioridade Média)\n\n"
            keyboard.add(InlineKeyboardButton("⛓️ ON-Chain", callback_data=f"BUY_VALUE_BTC_{value}"))

        if Features().check("FEATURE_BUY_LIQUID"):
            message += "<b>💧 Liquid Network:</b> Escolhendo essa opção, você apenas pagará taxa de rede.\n\n"
            keyboard.add(InlineKeyboardButton("💧 Liquid Network", callback_data=f"BUY_VALUE_LIQUID_{value}"))

        if Features().check("FEATURE_BUY_LIGHTNING"):
            message+= "<b>⚡ Lightning Network:</b>  Escolhendo essa opção, você não pagará taxa de rede.\n\n"
            keyboard.add(InlineKeyboardButton("⚡ Lightning Network", callback_data=f"BUY_VALUE_LN_{value}"))

        with open("src/assets/select-network.jpg", "rb") as f:
            bot.send_photo(
                data.from_user.id,
                f, 
                caption=message, 
                reply_markup=keyboard
            )

    @featuresEnabled("FEATURE_BUY")
    def purchase_select_value_handler(data: Message, bot: TeleBot):
        """Handles the selection of a value for a purchase.

        Args:
            data (Message): The message data.
            bot (TeleBot): The Telegram bot object.
        """
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        value = float(data.data.split("_")[-1])
        if value < PURCHASE_MIN_VALUE:
            message = f"⚠️ Pedimos desculpas pelo inconveniente, mas o valor informado é abaixo do nosso limite de R$ {PURCHASE_MIN_VALUE:,.2f}."
            return bot.send_message(data.from_user.id, message)

        if value > PURCHASE_MAX_VALUE:
            message = f"⚠️ Pedimos desculpas pelo inconveniente, mas o valor informado ultrapassa nosso limite de R$ {PURCHASE_MAX_VALUE:,.2f}."
            return bot.send_message(data.from_user.id, message)

        network = data.data.split("_")[-2].upper()
        purchase_feerate_price = PURCHASE_FEERATE_PRICE
        if network == "LIQUID":
            purchase_feerate_price += COINOS_LIQUID_RATE_FEE
        
        purchase_details = quote.make_purchase(
            value=value,
            fees={
                "services": PURCHASE_FEERATE_SERVICES,
                "provider": FEERATE_PROVIDER,
                "price": purchase_feerate_price
            },
        )
        network_fee = 0
        feerate = 0
        swap_value = 0
        if network == "LIQUID":
            swap_value = purchase_details["values"]["to"]["btc"]
            feerate = mempool.fees_recommended(network="liquid")["fastestFee"]
            fees = feerate * 3000
            purchase_details["values"]["to"]["btc"] -= round(fees)
            purchase_details["values"]["to"]["brl"] = sats_to_fiat(purchase_details["values"]["to"]["btc"], purchase_details['prices']['services'])

        if network == "BTC":
            try:
                getinfo = swap.get_info()
                if getinfo["swap"]["min"] > purchase_details["values"]["to"]["btc"]:
                    return bot.send_message(data.from_user.id, f"⚠️ O valor R$ {value:,.2f} informado não é permitido para transação on-chain.")

                if getinfo["swap"]["max"] < purchase_details["values"]["to"]["btc"]:
                    return bot.send_message(data.from_user.id, f"⚠️ O valor R$ {value:,.2f} informado não é permitido para transação on-chain. ")

                feerate = getinfo["fees"]["minimum_fee"]
                swap_value = purchase_details["values"]["to"]["btc"]
                fees_calculate = swap.calculate(swap_value, feerate)
                if fees_calculate.get("message"):
                    return bot.send_message(data.from_user.id, "⚠️ As taxas de rede encontram-se elevadas no momento.\n\nRecomendamos tentar novamente mais tarde ou utilizar a rede Lightning.")

                purchase_details["values"]["to"]["btc"] -= round(fees_calculate["fees"])
                purchase_details["values"]["to"]["brl"] = fees_calculate["to"]  * purchase_details['prices']['services']
                network_fee = round(fees_calculate["fees"])
            except Exception as error:
                logging.error(str(error), exc_info=True)
                return bot.send_message(data.from_user.id, "⚠️ Tente novamente mais tarde ou utilize a rede Lightning.")

        purchase_details["swap"] = {
            "feerate": feerate, 
            "value": swap_value
        }
        purchase_details["network"] = network

        purchase_details = quote.create_purchase(
            tx=purchase_details, 
            expiry_at=(60 * 35)
        )
        try:
            affiliated_to = database.User.select(database.User.affiliated_to).where(
                (database.User.id == str(data.from_user.id))).get().affiliated_to
        except Exception as error:
            logging.error(str(error), exc_info=True)
            affiliated_to = None
        
        database.RampBUYAndSELL.create(
            id=purchase_details["txid"],
            user=str(data.from_user.id),
            status="created",
            order_type="BUY",
            value_from_btc=purchase_details["values"]["from"]["btc"],
            value_from_brl=purchase_details["values"]["from"]["brl"],
            value_to_btc=purchase_details["values"]["to"]["btc"],
            value_to_brl=purchase_details["values"]["to"]["brl"],
            price_services=purchase_details["prices"]["services"],
            price_provider=purchase_details["prices"]["provider"],
            fee_value=purchase_details["fees"]["value"],
            fee_rate_price=purchase_details["fees"]["rate"]["price"],
            fee_rate_services=purchase_details["fees"]["rate"]["services"],
            fee_rate_provider=purchase_details["fees"]["rate"]["provider"],
            identifier=purchase_details["identifier"],
            affiliate_code=affiliated_to,
            expiry_at=datetime.now() + timedelta(minutes=60),
        )
        message = (
            "📃 <b>Informações de compra:</b>\n\n"
            f"<b>Preço:</b> R$ <code><i>{purchase_details['prices']['services']:,.2f}</i></code>\n"
            f"<b>Valor:</b> R$ <code><i>{purchase_details['values']['from']['brl']:,.2f}</i></code>\n"
            f"<b>Taxa:</b> R$ <i><code>{purchase_details['fees']['value']:,.2f}</code></i>\n"
        )
        if network == "BTC":
            message += f"<b>Taxa De Rede:</b> <i><code>{network_fee}</code> sats ({feerate} sats / vb)</i>\n"

        message += f"<b>Comprado:</b> R$ <code><i>{purchase_details['values']['to']['brl']:,.2f}</i></code>\n"
        message += f"<b>Receber:</b> <code><i>{round(purchase_details['values']['to']['btc'])}</i></code> sats\n\n" 
        if network == "BTC":
            message += (
                "⚠️ <b>Atenção!</b>\n\n"
                "<b>1 - Envie seu endereço Bitcoin ele deve ser (SegWit) e começar com bc1 ...</b>\n"   
                "<b>2 - Por favor, verifique seu endereço antes de enviar. Não nos responsabilizamos por envios de endereços errados.</b>\n\n"
            ) 
        elif network == "LIQUID":
            message += (
                "⚠️ <b>Atenção!</b>\n\n"
                "<b>1 - Envie seu endereço Liquid ele deve começar com lq ou vj ...</b>\n"   
                "<b>2 - Por favor, verifique seu endereço antes de enviar. Não nos responsabilizamos por envios de endereços errados.</b>\n\n"
            ) 
        else:
            message+= "⚠️ LEIA COM ATENÇÃO\n\n"
            message+= "01 - Use a CARTEIRA INDICADA: Wallet of Satoshi\n"
            message+= f"02 - GERE uma fatura lightning válida de <code>{round(purchase_details['values']['to']['btc'])}</code> sats\n"
            message+= "03 - Envie SOMENTE 'TXT' da fatura (NÃO ENVIE O QR-CODE).\n"
            message+= "04 - Não use: Muun wallet, Breez, Phoenix e Blixt.\n\n"
            message+= "Aguardando o envio da fatura...\n\n"
        
        message += f"<b>Txid:</b> <code><i>{purchase_details['txid']}</i></code>\n\n"
        message += f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"

        user_id = str(data.from_user.id)
        tx = redis.redis_get(f"user.{user_id}")
        if not tx:
            redis.redis_set(
                f"user.{user_id}",
                {
                    "id": user_id,
                    "tx": {
                        "purchase": {
                            "txid": purchase_details["txid"],
                        },
                        "sell": {
                            "txid": None
                        },
                    },
                },
            )
        else:
            tx["tx"]["purchase"]["txid"] = purchase_details["txid"]
            redis.redis_set(f"user.{user_id}", tx)

        if network == "BTC":
            with open("src/assets/address-bitcoin.jpg", "rb") as f:
                bot.send_photo(
                    user_id,
                    f, 
                    caption=message
                )
        elif network == "LIQUID":
            with open("src/assets/address-liquid.jpg", "rb") as f:
                bot.send_photo(
                    user_id,
                    f, 
                    caption=message
                )
        else:
            with open("src/assets/create-invoice-lightning.jpg", "rb") as f:
                bot.send_photo(
                    user_id,
                    f, 
                    caption=message
                )

    @featuresEnabled("FEATURE_BUY")
    def purchase_add_address_handler(data: Message, bot: TeleBot):
        """
        Handles the addition of a purchase address.

        Args:
            data (Message): The received message data.
            bot (TeleBot): The TeleBot instance.
        """
        try:
            txid = redis.redis_get(
                f"user.{data.from_user.id}")["tx"]["purchase"]["txid"]        
        except:
            txid = None
        
        tx = redis.redis_get(f"tx.{txid}")
        if not (tx):
            message = "Sua transação de compra expirou. Por favor, refaça o processo de compra."
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("Refazer Compra", callback_data="BUY_OPTION"))
            return bot.send_message(data.from_user.id, message, reply_markup=keyboard)

        try:
            address = data.text.strip()
        except:
            address = data.caption.strip()
        
        network = tx.get("network")
        try:
            if network == "BTC":
                chain_stats = mempool.get_address(address=address)
            elif network == "LIQUID":
                chain_stats = mempool.get_address(
                    address=address, network="liquid")
            else:
                chain_stats = None
            
            if chain_stats and chain_stats["chain_stats"]["funded_txo_count"] >= 1:
                raise ValueError("This address has already been used.")
        except Exception as error:
            logging.error(str(error), exc_info=True)
            return bot.send_message(data.from_user.id,  "Seu endereço Bitcoin / Liquid é invalido. Por favor, envie um novo endereço.")
        
        swap_id = None
        if network == "LIQUID":
            try:
                payment_request = coinos.invoice(round(tx["swap"]["value"]))["text"]
            except Exception as error:
                logging.error(str(error), exc_info=True)
                return bot.send_message(data.from_user.id, "O serviço da Liquid encontra-se temporariamente indisponível. Por favor, utilize outra rede para realizar suas compra.")
        elif network == "BTC":
            try:
                swap_request = swap.create_swap(
                    address=address, 
                    value=round(tx["swap"]["value"]), 
                    feerate=tx["swap"]["feerate"]
                )
                payment_request = swap_request["from"]["payment_request"]
                swap_id = swap_request["id"]
            except Exception as error:
                logging.error(str(error), exc_info=True)
                return bot.send_message(data.from_user.id,  "Seu endereço Bitcoin é invalido. Por favor, envie um novo endereço.")
        else:
            payment_request = address
        
        try:
            decode_invoice = lnbits.decode_invoice(payment_request)
        except Exception as error:
            logging.error(str(error), exc_info=True)
            message = f"Por favor, tente enviar novamente á fatura."
            return bot.send_message(data.from_user.id, message)
        
        if decode_invoice["date"] + decode_invoice["expiry"] <= time() + 3000:
            return bot.send_message(data.from_user.id,  "Sua fatura lightning é invalida. Por favor, gere uma nova fatura.")

        invoice_amount_sat = decode_invoice["amount_msat"] / 1000
        if (network in ["BTC", "LIQUID"]) and (round(invoice_amount_sat) != round(tx["swap"]["value"])):
            return bot.send_message(data.from_user.id,  "Sua fatura lightning é invalida. Por favor, gere uma nova fatura.")

        if (network == "LN") and (round(invoice_amount_sat) != round(tx["values"]["to"]["btc"])):
            return bot.send_message(data.from_user.id,  "Sua fatura lightning é invalida. Por favor, gere uma nova fatura.")
    
        node_alias = None
        try:
            node_alias = mempool.get_node_stats(id=decode_invoice["payee"])["alias"].upper()
        except Exception as err:
            logging.error(str(err), exc_info=True)

        if not node_alias or not node_alias in PURCHASE_WHITELIST_CHANNELS:
            message = "Fatura inválida. Por favor, utilize uma das carteiras indicadas. "
            message+= "Recomendamos o uso de carteiras como Wallet of Satoshi, Alby, Coinos."
            return bot.send_message(data.from_user.id, message)

        try:
            bank_current = random.choice(BankAccount.listing_bank_accounts(activated=True))
        except Exception as error:
            logging.error(str(error), exc_info=True)
            bank_current = None
        
        if not bank_current:
            bank_current = { "alias": None,  "name": PIX_NAME, "address": PIX_KEY }

        redis.redis_set(
            key=f"tx.address.{txid}",
            value={
                "payment_request": payment_request,
                "payment_hash": decode_invoice["payment_hash"],
                "payee": decode_invoice["payee"],
                "address": address,
                "swap_id": swap_id,
                "network": network,
                "bank_alias": bank_current["alias"]
            },
            expiry_at=60 * 60,
        )

        pix_code = Pix().encode(
            address=bank_current["address"],
            amount=tx["values"]["from"]["brl"],
            name=bank_current["name"],
            city="SP",
            txid=(tx["identifier"] if PIX_NON_TXID == True else None)
        )
        qrcode = QRCode()
        qrcode.add_data(pix_code)
        qrcode.make(fit=True)

        stream = BytesIO()
        image = qrcode.make_image(fill_color="black", back_color="white")
        image.save(stream, "PNG")
        image = stream.getvalue()

        expiration_time = datetime.now() + timedelta(minutes=15)
        expiration_formatted = expiration_time.strftime("%H:%M")

        message = (
            "<b>⏳⚡️ DADOS DO PAGAMENTO:</b>\n"
            f"<b>Valor:</b> R$ <code>{tx['values']['from']['brl']:,.2f}</code>\n"
            f"<b>ID:</b> <code>{tx['identifier']}</code>\n"
            f"<b>Rede:</b> {network.upper()}\n"
            f"<b>Expiração:</b> ~{expiration_formatted}\n\n"
        )
        message+= (
            "<b>⚠️ Atenção!</b>\n"
            "01 - Pague a FATURA PIX Copie e Cole.\n"
            "02 - Envie o comprovante de pagamento (Formato: PNG/JPG).\n"
            "03 - O comprovante deve estar em seu nome e CPF cadastrado.\n\n"
            "Obs: O comprovante de pagamento deve conter os seguintes dados: NOME COMPRADOR, IDENTIFICADOR, VALOR, DATA, HORA e os dados precisam estar legíveis.\n\n"
            f"Para copiar a FATURA PIX abaixo, clique sobre ela, vá no seu banco e pague a mesma:\n<code>{pix_code}</code>\n\n"
            f"<b>Txid: </b><code>{txid}</code>\n\n"
            f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
        )

        with open("src/assets/send-receipt.jpg", "rb") as f:
            bot.send_photo(data.from_user.id, f, caption=message, reply_markup=ForceReply(selective=False))

    def purchase_add_receipt_handler(data: Message, bot: TeleBot):
        """
        Handles the addition of a purchase receipt.

        Args:
            data (Message): The received message data.
            bot (TeleBot): The TeleBot instance.
        """
        try:
            bot.delete_message(data.from_user.id, data.message_id - 1)
        except Exception as error:
            logging.error(str(error), exc_info=True)

        try:
            txid = redis.redis_get(f"user.{data.from_user.id}")["tx"]["purchase"]["txid"]
        except:
            txid = None

        tx = redis.redis_get(f"tx.{txid}")
        if not tx:
            message = (
                "⚠️ Sua transação de compra expirou.\n\nPor favor, refaça o processo de compra: com o mesmo valor, "
                "gerando uma nova fatura Lightning, e após isso, reenvie este comprovante de pagamento.\n\n"
                f"Em caso de dúvidas, entre em contato com nosso suporte: {SUPPORT_CHANNEL}\n\n"
                f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
            )
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("Resolver problema de compra expirada", url="https://stackfy.substack.com/p/stackfy-ordem-de-compra-expirada#%C2%A7ordem-expirou-o-que-devo-fazer"))
            return bot.send_message(data.from_user.id, message)

        address = redis.redis_get(f"tx.address.{txid}")
        channel = address["payee"]
        network = address.get("network", "LN").upper()
        receipt = database.RampBUYAndSELL.select().where(
            (database.RampBUYAndSELL.id == txid) & 
            (database.RampBUYAndSELL.status == "created")
        )
        if not receipt.exists():
            message = "⚠️ Não foi possível enviar o seu comprovante.\n\n"
            message += f"<b>Txid:</b> <code>{txid}</code>"
            return bot.send_message(data.from_user.id, message)
        else:
            receipt = receipt.get()
            if receipt.expiry_at.timestamp() <= time():
                message = (
                    "⚠️ Sua transação de compra expirou.\n\nPor favor, refaça o processo de compra: com o mesmo valor, "
                    "gerando uma nova fatura Lightning, e após isso, reenvie este comprovante de pagamento.\n\n"
                    f"Em caso de dúvidas, entre em contato com nosso suporte: {SUPPORT_CHANNEL}\n\n"
                    f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
                )
                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton("Resolver problema de compra expirada", url="https://stackfy.substack.com/p/stackfy-ordem-de-compra-expirada#%C2%A7ordem-expirou-o-que-devo-fazer"))
                with open("src/assets/expired-order.jpg", "rb") as f:
                    return bot.send_photo(data.from_user.id, f, caption=message, reply_markup=keyboard)
            else:
                with open("src/assets/processing-tx.jpg", "rb") as f:
                    message = "Seu comprovante de pagamento está em análise. "
                    message+= f"Em breve, os <code>{round(receipt.value_to_btc)}</code> sats serão enviados para sua carteira.\n\n"
                    if (tx["network"] in ["BTC", "LIQUID"]):
                        message += f"<code>{address['address']}</code>\n\n"
                    else:
                        message+= f"<code>{address['payment_request']}</code>\n\n"
                    
                    message+= f"<b>Txid:</b> <code>{txid}</code>\n\n"
                    message+=f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
                    bot.send_photo(data.from_user.id, f, caption=message)

        if "document" in data.json:
            file_path = bot.get_file(data.document.file_id).file_path
            file_path += ".pdf"
        else:
            file_path = bot.get_file(data.photo[-1].file_id).file_path
            file_path += ".png"

        receipt.receipt_path = f"tg:{file_path}"
        receipt.status = "pending"
        receipt.bank = address["bank_alias"]
        receipt.save()

        redis.redis_expire(f"tx.address.{txid}", (60 * 60) * 2.5)

        try:
            bank_current = BankAccount.get_account_bank(
                alias=address["bank_alias"])    
        except Exception as error:
            logging.error(str(error), exc_info=True)
            bank_current = None
        
        if not bank_current:
            if PIX_NAME:
                bank_current = {
                    "operator": None,
                    "name": PIX_NAME,
                    "alias": None,
                    "address": PIX_KEY,
                    "activated": True,
                    "bank_name": None,
                    "account_type": "PF"
                }

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
        
        Notify.notify_purchase_order(
            bot,
            txid,
            data.from_user.username,
            receipt.value_from_brl,
            receipt.value_to_btc,
            receipt.identifier,
            address["payment_request"],
            bank_current['alias'],
            bank_current['bank_name'],
            bank_current['name'],
            bank_current['address'],
            identification_document_id,
            identification_document_name,
            HISTORY_CHANNEL_ID
        )

        try:
            node_stats = mempool.get_node_stats(id=channel)
        except:
            node_stats = dict()
        
        try:
            database.RampAddressInfo.create(
                ramp=txid,
                alias=node_stats.get("alias"),
                network=network,
                address=address.get("payment_request"),
                channel=channel,
                country=node_stats.get("iso_code")
            )
        except Exception as error:
            logging.error(str(error), exc_info=True)

    @featuresEnabled("FEATURE_BUY")
    def purchase_custom_value_handler(data: Message, bot: TeleBot):
        """
        Handles the purchase custom value message.
        Asks the user for the desired purchase value.

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
            "Qual valor você deseja comprar?\n\n"
            "Por favor, responda esta mensagem com o valor desejado."
        )
        bot.send_message(
            data.from_user.id, message, reply_markup=ForceReply(selective=False)
        )

    @featuresEnabled("FEATURE_BUY")
    def purchase_custom_add_value_handler(data: Message, bot: TeleBot):
        """Handles the custom addition of a value for a purchase.

        Args:
            data (Message): The message data.
            bot (TeleBot): The Telegram bot object.
        """
        value = round(float(data.text.replace(",", ".")), 2)
        if value < PURCHASE_MIN_VALUE:
            message = f"⚠️ Valor R$ {value:,.2f} inválido, abaixo de nosso limite mínimo de compra:\n\n"
            message+= "Limites (Min./Máx.)\n"
            message+= f"Compra: R$ {PURCHASE_MIN_VALUE:,.2f} / R$ {PURCHASE_MAX_VALUE:,.2f}\n\n"
            message+= "Certifique-se de que você não está digitando, por exemplo, 1.000 (R$ 1,00) em vez de 1000 (R$ 1000,00)."
            return bot.send_message(data.from_user.id, message)

        if value > PURCHASE_MAX_VALUE:
            message = f"⚠️ Pedimos desculpas pelo inconveniente, mas o valor informado ultrapassa nosso limite de R$ {PURCHASE_MAX_VALUE:,.2f}."
            return bot.send_message(data.from_user.id, message)

        message = f"Para prosseguir com a compra no valor de R$ {value:,.2f}, clique no botão abaixo."
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Continuar", callback_data=f"BUY_VALUE_{value}"))
        return bot.send_message(data.from_user.id, message, reply_markup=keyboard)
