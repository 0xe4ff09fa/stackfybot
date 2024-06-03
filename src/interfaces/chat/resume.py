from src.interfaces.chat.notify import Notify
from src.services.helpers import calculate_percentage_difference, calculate_simple_average, calculate_percentage, decode_base64
from telebot.types import Message, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from src.configs import KYC_INCREASE_LEVEL_BASIC_MAX_VALUE, KYC_INCREASE_LEVEL_BASIC_URL, PURCHASE_FEERATE_PRICE, VALUE_COMMUNITY_AFFILIATE, VALUE_PARTNER_AFFILIATE
from datetime import datetime, timedelta
from bitpreco import BitPreco
from telebot import TeleBot
from peewee import fn
from src import database

import logging
import base64
import json

bitpreco = BitPreco()

class Resume:

    def resume(data: Message, bot: TeleBot):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass
        
        purchase_prices = []
        for r in database.\
                  RampBUYAndSELL.\
                    select(database.RampBUYAndSELL.price_services)\
                        .where(
                            (database.RampBUYAndSELL.user == str(data.from_user.id)) &
                            (database.RampBUYAndSELL.order_type == "BUY") &
                            (database.RampBUYAndSELL.status == "settled")):
            purchase_prices.append(r.price_services)        
        average_price = calculate_simple_average(purchase_prices)
        current_price = bitpreco.get_price()
        current_price["SELL"] += calculate_percentage(
            x=current_price["SELL"], 
            y=PURCHASE_FEERATE_PRICE
        )

        user = database.User\
            .select(
                database.User.level, 
                database.User.is_affiliate, 
                database.User.is_partner, 
                database.User.affiliate_code
            )\
                .where((database.User.id == str(data.from_user.id))).get()
        ref_fee = 0
        if user.is_partner:
            ref_fee = VALUE_PARTNER_AFFILIATE
        elif user.is_affiliate:
            ref_fee = VALUE_COMMUNITY_AFFILIATE

        payment_addresses = database.PaymentAddresses.get_or_create(
            user=str(data.from_user.id))[0]
    
        message = "📃 <b>Resumo de Conta:</b>\n\n"
        message+= f"<b>Preço Atual:</b> R$ <code>{current_price['SELL']:,.2f}</code>\n"
        message+= f"<b>Preço Médio:</b> R$ <code>{average_price:,.2f}</code>\n"
        message+= f"<b>Valorização:</b> <code>{calculate_percentage_difference(average_price, current_price['SELL']):,.2f}%</code>\n"
        message+= f"<b>Nível:</b> {'LV0' if not user.level else user.level}\n"

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
        
        if user.level == "LV1":
            message+= "\n<b>Meu Limite (R$)</b>\n"
            message+= f"<b>Diário:</b> R$ {sum_orders_purchase:,.2f} / R$ {KYC_INCREASE_LEVEL_BASIC_MAX_VALUE:,.2f}\n"
        else:
            message+= "\n<b>Meu Limite (R$)</b>\n"
            message+= f"<b>Diário:</b> R$ 0,00 / R$ {KYC_INCREASE_LEVEL_BASIC_MAX_VALUE:,.2f}\n"
        
        message+= "\n<b>Endereços de Recebimento:</b>\n"
        message+= f"<b>Lightning Address:</b> {payment_addresses.lightning_address}\n\n"

        keyboard = InlineKeyboardMarkup(row_width=2)
        if user.is_affiliate:
            current_date = datetime.now()
            #start_date = datetime(current_date.year, current_date.month, 1)
            #end_date = datetime(current_date.year, current_date.month + 1, 1) - timedelta(days=1)
            total_value_ref = database\
                    .RampBUYAndSELL\
                        .select(fn.SUM(database.RampBUYAndSELL.value_from_btc))\
                            .where(
                                (database.RampBUYAndSELL.affiliate_code == user.affiliate_code) & 
                                (database.RampBUYAndSELL.status == "settled") &
                                (database.RampBUYAndSELL.order_type == "BUY") 
                                #&
                                #(database.RampBUYAndSELL.updated_at >= start_date) &
                                #(database.RampBUYAndSELL.updated_at <= end_date)
            ).scalar()
            if not total_value_ref:
                total_rewards = 0
            else:
                total_rewards = round(calculate_percentage(float(total_value_ref), ref_fee))
                if total_rewards < 0:
                    total_rewards = 0
            
            message+= f"🎁 <b>Indique e Ganhe</b>\n"
            message+= f"Indique um amigo e receba <code>{ref_fee}</code>% das taxas pagas, quanto mais pessoas você indicar, mais você ganha.\n\n"
            message+= "Link de indicação: "
            message+= f"<code>https://t.me/{data.json['message']['from']['username']}?start={user.affiliate_code}</code>\n\n"
            message+= f"<b>Total de Recompensa:</b> <code>{total_rewards}</code> sats\n\n"

            if not total_rewards:
                keyboard.add(InlineKeyboardButton("Alterar Código de Afiliado", callback_data="CHANGE_AFFILIATE_CODE"))

        if not payment_addresses.lightning_address:
            keyboard.add(InlineKeyboardButton("Cadastrar Lightning Address", callback_data="ADD_LN_ADDRESS"))

        if not user.level:
            keyboard.add(InlineKeyboardButton("Aumentar Meu Nível", callback_data="INCREASE_LEVEL_1"))
    
        message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
        return bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def increase_level(data: Message, bot: TeleBot):
        if isinstance(data, CallbackQuery):
            try:
                bot.delete_message(data.from_user.id, data.message.message_id)
            except:
                pass
            
            level = data.data.split("_")[-1]
            if level == "1":
                message = "ℹ️ Para elevar seu nível para o básico e obter um limite maior, clique no botão abaixo e siga as instruções.\n\n"
                message+= f"<b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>"
                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton("Aumentar meu Nível", url=KYC_INCREASE_LEVEL_BASIC_URL))
                return bot.send_message(data.from_user.id, message, reply_markup=keyboard)
            else:
                return bot.send_message(data.from_user.id, "Não foi possível aumentar seu nível.")

        level = data.text[:3].upper()
        if level == "LV1":
            code = decode_base64(data.text[3:])
            code = json.loads(code)
            try:
                status = database.IdentificationDocument.select(
                    database.IdentificationDocument.status
                ).where(
                    (database.IdentificationDocument.user == str(data.from_user.id)) &
                    (database.IdentificationDocument.document_type == "CPF")
                ).get().status
            except:
                status = ""
            
            if status and not (status in ["rejected"]):
                return bot.send_message(data.from_user.id, "Não foi possível aumentar seu nível.")

            if len(code["cpf"]) != 11:
                return bot.send_message(data.from_user.id, "Não foi possível aumentar o seu nível, pois o seu documento é inválido.")

            date_of_birth = code.get("date_of_birth", "").replace("-", "/")
            if date_of_birth:
                try:
                    birth_date = datetime.strptime(date_of_birth, "%Y/%m/%d")
                    eighteen_years_ago = datetime.now() - timedelta(days=365 * 16)
                    if birth_date > eighteen_years_ago:
                        return bot.send_message(data.from_user.id, "Não foi possível aumentar o seu nível. A data de aniversário é inválida; você deve ter mais de 16 anos.")
                except Exception as error:
                    logging.error(str(error), exc_info=True)
            else:
                date_of_birth = datetime.now().strftime("%Y/%m/%d")
            
            user = database.User.get(id=str(data.from_user.id))
            user.level = "LV1"
            user.first_name = code["first_name"].title()
            user.last_name = code["last_name"].title()
            user.date_of_birth = date_of_birth
            user.save()

            full_name = f"{code['first_name']} {code['last_name']}".title()
            doc = database.IdentificationDocument.get_or_create(
                user=str(data.from_user.id))[0]
            doc.status = "pending"
            doc.document_type = "CPF"
            doc.document_number = code["cpf"]
            doc.document_name = full_name
            doc.save()

            Notify.notify_new_user_verification(
                bot=bot,
                username=data.from_user.username,
                email="nobody@nobody.com",
                full_name=full_name,
                cpf=code["cpf"],
                date_of_birth=date_of_birth   
            )
            return bot.send_message(data.from_user.id, "Sua solicitação de aumento de nível foi enviada para análise.")
        else:
            return bot.send_message(data.from_user.id, "Não foi possível aumentar seu nível.")

    def change_code_affiliate(data: Message, bot: TeleBot):
        if not isinstance(data, Message):
            try:
                bot.delete_message(data.from_user.id, data.message.message_id)
            except:
                pass

            message = "Por favor, forneça seu novo codigo de indicação, respondendo a esta mensagem: "
            bot.send_message(data.from_user.id, message, reply_markup=ForceReply(selective=False))
        else:
            code = data.text
            if len(code) < 3 or len(code) > 8:
                return bot.send_message(data.from_user.id, "O código de indicação é inválido.")
            
            if database.User.select().where(
                    (database.User.affiliate_code == str(code))).exists():
                return bot.send_message(data.from_user.id, "Este código de afiliado já existe.")
            
            user = database.User.select().where(
                (database.User.id == str(data.from_user.id))).get()
            user.affiliate_code = code
            user.save()
            return bot.send_message(data.from_user.id, f"O código de afiliado foi atualizado para {code} com sucesso.")
    
    def add_address_lightning_address(data: Message, bot: TeleBot):
        if not isinstance(data, Message):
            try:
                bot.delete_message(data.from_user.id, data.message.message_id)
            except:
                pass

            message = "Por favor, forneça seu endereço abaixo, respondendo a esta mensagem. "
            message+= "Certifique-se de que o Lightning Address esteja digitado corretamente: "
            bot.send_message(data.from_user.id, message, reply_markup=ForceReply(selective=False))
        else:
            if not "@" in data.text:
                return bot.send_message(data.from_user.id, "Lightning Address invalido.")
            
            payment_addresses = database.PaymentAddresses\
                .get(user=str(data.from_user.id))
            if not payment_addresses.lightning_address:
                payment_addresses.lightning_address = data.text
                payment_addresses.save()
                return bot.send_message(data.from_user.id, "Lightning Address cadastrado com sucesso.")
            else:
                return bot.send_message(data.from_user.id, "Lightning Address não foi cadastrado.")
