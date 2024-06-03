from src.services.helpers import format_cpf, fiat_to_sats, sats_to_fiat, calculate_percentage
from src.services.redis import redis
from telebot.types import Message, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton
from src.configs import COMMERCIAL_ACTIVITY_REGISTRATION
from telebot import TeleBot
from uuid import uuid4
from src import database
from io import StringIO

import csv

class NFSe:
    
    def nfse_menu(data: Message, bot: TeleBot):
        total_pending_nfse = (
            database.RampBUYAndSELL.select()
            .where(
                (database.RampBUYAndSELL.nfse == False) &
                (database.RampBUYAndSELL.status == "settled")
            )
            .count()
        )
    
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                "Baixa NFS-e não processadas", callback_data="UNPROCESSED_NFSE"
            )
        )
        keyboard.add(
            InlineKeyboardButton(
                "Importar NFS-e processadas", callback_data="PROCESSED_NFSE"
            )
        )
        message = f"<b>Total de NFS-e supostamente pendentes: [{total_pending_nfse}] para emissão.</b>"
        return bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def nfse_reply_import(data: Message, bot: TeleBot):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        message = "Importe o arquivo de NFS-e .csv"
        return bot.send_message(data.from_user.id, message, reply_markup=ForceReply(selective=False))
    
    def load_processed_nfse(data: Message, bot: TeleBot):        
        nfses = []
        message = "<b>NFS-es</b>\n\n"
        for nfse in csv.DictReader(bot.download_file(
                file_path=bot.get_file(data.document.file_id).file_path).decode('utf-8').splitlines()):
            message += f"<code>{nfse['txid']}</code> R$ <code>{nfse['value']}</code> "
            message += f"<code>{nfse['created_at']}</code>\n"
            nfses.append(nfse)

        txid = str(uuid4())
        redis.redis_set(f"NFSES.CONFIRM.PROCESSED.{txid}", nfses, expiry_at=60)

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                "Confirmar / Rollback NFS-e Processadas", callback_data=f"C_OR_R_NFSE_PROCESSED_{txid}"
            )
        )
        return bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def confirm_or_roolback_nfse_processed(data: Message, bot: TeleBot):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass
        
        txid = data.data.split("_")[-1]
        nfses_processed = redis.redis_get(f"NFSES.CONFIRM.PROCESSED.{txid}")
        if not nfses_processed:
            nfses_processed = []

        message = "<b>NFS-es Confirmado / Rollback:</b>\n\n"
        for nfse in nfses_processed:
            tx = database.RampBUYAndSELL.select().where(
                (database.RampBUYAndSELL.id == str(nfse["txid"])))
            if not tx.exists():
                continue
            else:
                tx = tx.get()
                nfse_processed = False if tx.nfse else True
                tx.nfse = nfse_processed                
                tx.save()
        
            message += f"<code>{nfse['txid']}</code> R$ <code>{nfse['value']}</code> "
            if nfse_processed:
                message += "(Processado) "
            else:
                message += "(Rollback) "

            message += f"<code>{nfse['created_at']}</code>\n"

        return bot.send_message(data.from_user.id, message)

    def get_unprocessed_nfse(data: Message, bot: TeleBot):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass
        
        txs = []
        total_billing = 0
        for ramp in database.RampBUYAndSELL.select().where(
                (database.RampBUYAndSELL.nfse == False) &
                (database.RampBUYAndSELL.status == "settled")
            ):
            identification_document = database.IdentificationDocument.select().where(
                (database.IdentificationDocument.user == str(ramp.user.id)) &
                (database.IdentificationDocument.document_type == "CPF")
            ).first()
            if identification_document:
                identification_document_id = identification_document.document_number
                identification_document_name = identification_document.document_name
            else:
                identification_document_id = None
                identification_document_name = ramp.user.first_name

            if ramp.order_type == "BUY":
                gross_revenue_value_fiat_total = sats_to_fiat((fiat_to_sats(ramp.value_from_brl, ramp.price_provider) - \
                        fiat_to_sats((ramp.value_from_brl - ramp.fee_value), ramp.price_services)), ramp.price_provider)
                gross_revenue_value_fiat_total -= calculate_percentage(
                    x=ramp.value_from_brl,
                    y=ramp.fee_rate_provider        
                )
            else:
                gross_revenue_fiat = sats_to_fiat(ramp.value_from_btc, ramp.price_provider)
                gross_revenue_value_fiat_total = (gross_revenue_fiat - ramp.value_to_brl)
                gross_revenue_value_fiat_total-= calculate_percentage(
                    x=ramp.value_from_brl,
                    y=ramp.fee_rate_provider        
                )
            
            order_type = ("Compra" if (ramp.order_type == "BUY") \
                    else "Venda").title()
            txs.append({
                "txid":        ramp.id,
                "name":        identification_document_name,
                "cpf":         format_cpf(identification_document_id),
                "cnae":        COMMERCIAL_ACTIVITY_REGISTRATION,
                "value":       f"{gross_revenue_value_fiat_total:,.2f}",
                "description": f"Intermediação de ({order_type}) de criptomoeda Bitcoin (BTC).",
                "created_at":  ramp.created_at.strftime('%d/%m/%Y %H:%M:%S')
            })
            total_billing += gross_revenue_value_fiat_total

        if not txs:
            return bot.send_message(data.from_user.id, "Não possuímos nenhuma NFS-e para emitir.")
        
        csv_file = StringIO()
        csv_writer = csv.DictWriter(csv_file, fieldnames=txs[0].keys())
        csv_writer.writeheader()
        csv_writer.writerows(txs)
        csv_file.seek(0)

        message = "<b>NFS-e não processadas</b>\n\n"
        message+= f"<b>Total de Faturamento:</b> R$ {total_billing:,.2f}"
        return bot.send_document(
            data.from_user.id, 
            document=csv_file, 
            caption=message,
            visible_file_name="nfse.csv"
        )
