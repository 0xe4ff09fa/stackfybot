from src.services.firebase import storage
from src.services.helpers import format_cpf, fiat_to_sats, sats_to_fiat, calculate_percentage
from src.services.quote import Quote
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from src.configs import TAX_RATE
from telebot import TeleBot
from src import database

quote = Quote(redis=None)

class Transaction:

    def get_transaction_tx(data: Message, bot: TeleBot):
        txid = data.text.split(" ")[-1]
        ramp = database.RampBUYAndSELL.select().where(
            (database.RampBUYAndSELL.id == txid) |
            (database.RampBUYAndSELL.identifier == txid)
        )
        if ramp.exists() == False:
            message = "Tx não encontrado.\n\n"
            message += f"<code>{txid}</code>"
            return bot.send_message(data.from_user.id, message)
        else:
            ramp = ramp.get()    
        
        try:
            rampaddress_info = database.RampAddressInfo.select().where(
                (database.RampAddressInfo.ramp == str(ramp.id))).get()

            address = rampaddress_info.address
            network = rampaddress_info.network.title()
        except:
            address = None
            network = None

        identification_document = database.IdentificationDocument.select().where(
            (database.IdentificationDocument.user == str(ramp.user.id)) &
            (database.IdentificationDocument.document_type == "CPF")
        )
        if not identification_document.exists():
            identification_document_id = None
            identification_document_name = None
        else:
            identification_document = identification_document.get()
            identification_document_id = identification_document.document_number
            identification_document_name = identification_document.document_name

        if not identification_document_name:
            identification_document_name = ramp.user.first_name

        try:
            operator = database.User.select(database.User.username).where(
                (database.User.id == str(ramp.operator))).get().username
        except:
            operator = None

        if ramp.order_type == "BUY":
            gross_revenue_value_fiat_total = sats_to_fiat((fiat_to_sats(ramp.value_from_brl, ramp.price_provider) - \
                    fiat_to_sats((ramp.value_from_brl - ramp.fee_value), ramp.price_services)), ramp.price_provider)
            gross_revenue_value_fiat_total -= calculate_percentage(
                x=ramp.value_from_brl,
                y=ramp.fee_rate_provider        
            )
            tax_turnover_value = calculate_percentage(gross_revenue_value_fiat_total, TAX_RATE)
        else:
            gross_revenue_fiat = sats_to_fiat(ramp.value_from_btc, ramp.price_provider)
            gross_revenue_value_fiat_total = (gross_revenue_fiat - ramp.value_to_brl)
            gross_revenue_value_fiat_total -= calculate_percentage(
                x=ramp.value_from_brl,
                y=ramp.fee_rate_provider        
            )
            tax_turnover_value = calculate_percentage(gross_revenue_value_fiat_total, TAX_RATE)

        order_type = ("Compra" if (ramp.order_type == "BUY") \
                    else "Venda").title()

        total_order = (
            database.RampBUYAndSELL.select().where(
                (database.RampBUYAndSELL.user == ramp.user.id) &
                (database.RampBUYAndSELL.order_type == ramp.order_type) &
                (database.RampBUYAndSELL.status == "settled")
            ).count()
        )

        message = (
            f"<b>[{order_type}] Detalhes de Pedido:</b>\n\n"
            "<b>Informações do Usuário:</b>\n"
            f"<b>Usuário:</b> <i>@{ramp.user.username}</i>\n"
            f"<b>Nome:</b> <i><code>{ramp.user.first_name}</code></i>\n"
            f"<b>CPF:</b> <i><code>{format_cpf(identification_document_id)}</code></i>\n"
            f"<b>Total de {order_type}:</b> <code>{total_order}</code>\n"
            f"<b>Criação de conta:</b> <i><code>{ramp.user.created_at.strftime('%d/%m/%Y %H:%M:%S')}</code></i>\n\n"
            "<b>Informações da Transação:</b>\n"
            f"<b>ID:</b> <code>{ramp.identifier}</code>\n"
            f"<b>Tipo:</b> <i>{order_type}</i>\n"
            f"<b>Status:</b> <i>{ramp.status.title()}</i>\n"
            f"<b>Banco:</b> <i>{ramp.bank}</i>\n"
            f"<b>Operador:</b> <i>@{operator}</i>\n"
            f"<b>Preço (Serviço):</b> <i>R$ <code>{ramp.price_services:,.2f}</code></i>\n"
            f"<b>Preço (Fornecedor):</b> <i>R$ <code>{ramp.price_provider:,.2f}</code></i>\n"
            f"<b>Valor (De):</b> <i>R$ <code>{ramp.value_from_brl:,.2f}</code></i> <i>(<code>{int(ramp.value_from_btc)}</code> sats)</i>\n"
            f"<b>Valor (Para):</b> <i>R$ <code>{ramp.value_to_brl:,.2f}</code></i> <i>(<code>{int(ramp.value_to_btc)}</code> sats)</i>\n"
            f"<b>Taxa (Valor):</b> <i>R$ <code>{ramp.fee_value:,.2f}</code></i>\n"
            f"<b>Taxa Rate (Preço):</b> <i><code>{ramp.fee_rate_price:,.2f}%</code></i>\n"
            f"<b>Taxa Rate (Serviço):</b> <i><code>{ramp.fee_rate_services:,.2f}%</code></i>\n"
            f"<b>Taxa Rate (Fornecedor):</b> <i><code>{ramp.fee_rate_provider:,.2f}%</code></i>\n\n"
            "<b>Informações do Endereço De Recebimento:</b>\n"
            f"<b>Rede:</b> <code>{network}</code>\n"
            f"<b>Endereço de Pagamento:</b> <i><code>{address}</code></i>\n\n"
            "<b>Informações de Faturamento Da Transação:</b>\n"
            f"<b>NFS-e Emitido:</b> <i>{'Sim' if ramp.nfse == True else 'Não'}</i>\n"
            f"<b>Valor do Serviço:</b> R$ <i><code>{gross_revenue_value_fiat_total:,.2f}</code></i>\n"
            f"<b>Imposto sobre o Valor:</b> R$ <i><code>{tax_turnover_value:,.2f}</code></i>\n"
            f"<b>Lucro Bruto:</b> R$ <i><code>{gross_revenue_value_fiat_total - tax_turnover_value:,.2f}</code></i>\n\n"
            f"<b>Txid:</b> <code>{txid}</code>\n"
            f"<b>Criado Em:</b> {ramp.created_at.strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"<b>Atualizado Em:</b> {ramp.updated_at.strftime('%d/%m/%Y %H:%M:%S')}"
        )

        keyboard = InlineKeyboardMarkup()
        if ramp.order_type == "BUY":
            keyboard.add(
                InlineKeyboardButton(
                    "Recibo de Pagamento", callback_data=f"TX_RECEIPT_OF_PAYMENT_{txid}"
                )
            )
        return bot.send_message(data.from_user.id, message, reply_markup=keyboard)

    def get_transaction_tx_receipt_of_payment(data: Message, bot: TeleBot):
        try:
            bot.delete_message(data.from_user.id, data.message.message_id)
        except:
            pass

        txid = data.data.split("_")[-1]
        ramp = database.RampBUYAndSELL.select().where(
            (database.RampBUYAndSELL.id == txid) & 
            (database.RampBUYAndSELL.order_type == "BUY")
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

        identification_document = database.IdentificationDocument.select().where(
            (database.IdentificationDocument.user == str(ramp.user.id)) &
            (database.IdentificationDocument.document_type == "CPF")
        )
        if not identification_document.exists():
            identification_document_id = None
            identification_document_name = None
        else:
            identification_document = identification_document.get()
            identification_document_id = identification_document.document_number
            identification_document_name = identification_document.document_name

        if not identification_document_name:
            identification_document_name = ramp.user.first_name

        message = (
            "<b>Recibo de Pagamento </b>\n"
            f"<b>Nome:</b> <code>{identification_document_name}</code>\n"
            f"<b>CPF:</b> <i><code>{format_cpf(identification_document_id)}</code></i>\n"
            f"<b>Valor:</b> <i>R$ <code>{ramp.value_from_brl:,.2f}</code></i>\n"
            f"<b>ID:</b> <code>{ramp.identifier}</code>\n\n"
            f"<b>Txid:</b> <code>{txid}</code>\n"
            f"<b>Criado Em:</b> {ramp.created_at.strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"<b>Atualizado Em:</b> {ramp.updated_at.strftime('%d/%m/%Y %H:%M:%S')}"
        )
        if receipt:
            if receipt_type == "pdf":
                return bot.send_document(
                    chat_id=data.from_user.id,
                    document=receipt,
                    caption=message,
                    visible_file_name="receipt.pdf",
                )
            else:
                return bot.send_photo(
                    chat_id=data.from_user.id,
                    photo=receipt,
                    caption=message,
                )
        else:
            return bot.send_message(data.from_user.id, message)
