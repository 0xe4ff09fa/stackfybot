from src.interfaces.api.middlewares import get_current_user
from src.interfaces.chat.telegram import bot
from src.interfaces.chat.notify import Notify
from src.interfaces.api.schemas import AddressSchema
from src.services.lightning import lnbits
from src.services.firebase import storage
from src.services.helpers import msats_to_sats
from src.services.coinos import coinos
from src.services.quote import Quote
from src.services.redis import redis
from src.services.bank import BankAccount
from src.services import lightning
from src.services import inter
from src.configs import BANK_ID, BANK_NAME, HISTORY_CHANNEL_ID, PIX_KEY, PIX_NAME, PIX_PROVIDER, PRODUCTION, TRANSFER_MIN_VALUE_AUTO
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from mempool import Mempool
from time import time
from pix import Pix
from src import database

import logging
import random

# Initialize APIRouter
router = APIRouter()

# Initialize Quote
quote = Quote(redis=redis)

# Initialize Mempool
mempool = Mempool()

@router.patch("/api/v1/add-address/{txid}")
def add_address(
        txid: str, 
        address: AddressSchema, 
        current_user: str = Depends(get_current_user)
    ):
    tx = database.RampBUYAndSELL.select().where(
        (database.RampBUYAndSELL.user == current_user) & 
        (database.RampBUYAndSELL.id == txid) & 
        (database.RampBUYAndSELL.status == "created"))
    if not tx.exists():
        raise HTTPException(400, "Tx not found.")
    else:
        tx = tx.get()
    
    if (tx.order_type == "BUY"):
        address = address.address
        try:
            network = quote.get_quote(txid).get("network", "LN").upper()
        except:
            network = "LN"
        
        if "lnbc" in address and network == "LN":
            try:
                decode_invoice = lnbits.decode_invoice(address)
            except Exception as error:
                logging.error(str(error), exc_info=True)
                raise HTTPException(400, "Your Lightning invoice is invalid.")

            invoice_amount_sat = msats_to_sats(decode_invoice["amount_msat"])
            if decode_invoice["date"] + decode_invoice["expiry"] <= time() + 3600 or \
                    round(invoice_amount_sat) != round(tx.value_to_btc):
                raise HTTPException(400, "Your lightning invoice is invalid. Please generate a new invoice.")

            channel = decode_invoice["payee"]
            try:
                node_stats = dict(mempool.get_node_stats(id=channel))
            except:
                raise HTTPException(400, "Your lightning invoice is invalid. Please generate a new invoice.")

            database.RampAddressInfo.create(
                ramp=txid,
                alias=node_stats.get("alias"),
                address=address,
                network="LN",
                channel=channel,
                country=node_stats.get("iso_code")
            )
        elif ("lq1" in str(address).lower() or \
                "vj" in str(address).lower()) and network == "LIQUID":
            try:
                chain_stats = mempool.get_address(address, network="liquid")
            except:
                raise HTTPException(400, "Your Liquid is invalid.")

            if chain_stats and chain_stats["chain_stats"]["funded_txo_count"] >= 1:
                raise HTTPException(400, "This address has already been used.")

            tx = quote.get_quote(txid)
            try:
                payment_request = coinos.invoice(
                    round(tx["swap"]["value"]))["text"]
            except Exception as error:
                logging.error(str(error), exc_info=True)
                raise HTTPException(500, "We were unable to validate your address, please try again.")
            
            tx["swap"]["address"] = address
            quote.create_purchase(tx, expiry_at=(60 * 60))
            redis.redis_set(
                key=f"tx.address.{txid}",
                value={
                    "address": address,
                    "network": network
                },
                expiry_at=60 * 60
            )
            database.RampAddressInfo.create(
                ramp=txid,
                address=payment_request,
                network="LIQUID"
            )
        else:
            raise HTTPException(501)

        return { "message": "Address added successfully." }
    else:
        address = address.address
        try:
            decode_pix = Pix().decode(address)
        except:
            raise HTTPException(400, "Your PIX code is invalid.")
        
        if decode_pix["amount"] != tx.value_to_brl:
            raise HTTPException(400, "Your PIX code is invalid. Create a new PIX code.")

        database.RampAddressInfo.create(
            ramp=txid,
            address=address,
            network="pix"
        )
        return { "message": "Address added successfully." }

@router.get("/api/v1/payment-info/{txid}")
def get_payment_info(
        txid: str,
        current_user: str = Depends(get_current_user)
    ):
    tx = database.RampBUYAndSELL.select().where(
        (database.RampBUYAndSELL.user == current_user) & 
        (database.RampBUYAndSELL.id == txid))
    if not tx.exists():
        raise HTTPException(400, "Tx not found.")
    else:
        tx = tx.get()
    
    if (tx.expiry_at.timestamp() <= time()):
        raise HTTPException(400, "Tx has expired.")
    
    if (tx.order_type == "BUY"): 
        bank_alias = redis.redis_get(f"tx.address.{txid}").get("bank_alias")
        if PIX_PROVIDER == "INTER":
            bank_current = { "alias": None, "name": PIX_NAME, "address": PIX_KEY }
            try:
                pix_code = inter.inter.get_cob(txid)
            except:
                pix_code = inter.inter.create_cob(
                    key=PIX_KEY,
                    value=tx.value_from_brl,
                    txid=txid,
                    expiry=600
                )

            pix_code = pix_code["pixCopiaECola"]
        else:
            if bank_alias:
                try:
                    bank_current = BankAccount.get_account_bank(
                        alias=address["bank_alias"])    
                except Exception as error:
                    logging.error(str(error), exc_info=True)
                    bank_current = { "alias": None,  "name": PIX_NAME, "address": PIX_KEY }
            else: 
                try:
                    bank_current = random.choice(BankAccount.listing_bank_accounts(activated=True))
                except Exception as error:
                    logging.error(str(error), exc_info=True)
                    bank_current = { "alias": None,  "name": PIX_NAME, "address": PIX_KEY }

            pix_code = Pix().encode(
                address=bank_current["address"],
                amount=tx.value_from_brl,
                name=bank_current["name"],
                city="SP",
                txid=tx.identifier
            )
        
        if not bank_alias:
            redis.redis_update(f"tx.address.{txid}", { 
                "bank_alias": bank_current["alias"],
            }, expiry_at=(60 * 30))
        return { "id": txid, "pix": pix_code }
    else:
        address = redis.redis_get(f"tx.address.{txid}")
        if not address:
            address = lightning.addinvoice(
                value=tx.value_from_btc, 
                memo=f'SELL-{txid}',
                expiry=(60 * 20)
            )
            payment_request = address["payment_request"]
            if address.get("hash"):
                payment_hash = address['hash']
            else:
                payment_hash = address['r_hash']

            redis.redis_set(f"tx.address.{txid}", {
                "payment_request": payment_request,
                "payment_hash": payment_hash
            }, expiry_at=(60 * 25))
        else:
            payment_request = address["payment_request"]
            payment_hash = address["payment_hash"]
        
        return { "id": txid, "invoice": payment_request, "payment_hash": payment_hash }

@router.post("/api/v1/check-payment/{txid}")
def check_payment(
        txid: str, 
        background_tasks: BackgroundTasks,
        current_user: str = Depends(get_current_user)
    ):
    tx = database.RampBUYAndSELL.select().where(
        (database.RampBUYAndSELL.user == current_user) & 
        (database.RampBUYAndSELL.id == txid) &
        (database.RampBUYAndSELL.order_type == "SELL"))
    if not tx.exists():
        raise HTTPException(400, "Tx not found.")
    else:
        tx = tx.get()

    if (tx.status != "created"):
        return { "paid": True }

    payment_hash = redis.redis_get(f"tx.address.{txid}")
    if not payment_hash:
        raise HTTPException(400, "Tx not found.")
    else:
        payment_hash = payment_hash["payment_hash"]
    
    payment_status = lightning.check_payment(payment_hash)
    if (PRODUCTION == True) and (payment_status["paid"] == False):
        raise HTTPException(400, "Invoice hasn't been paid yet.")
    else:
        address = database.RampAddressInfo.select(database.RampAddressInfo.address).where(
            (database.RampAddressInfo.ramp == txid)).get().address

    if (tx.status == "created"):
        tx.status = "pending"
        tx.save()

        identification_document = database.IdentificationDocument.select().where(
            (database.IdentificationDocument.user == current_user) &
            (database.IdentificationDocument.document_type == "CPF")) 
        if not identification_document.exists():
            identification_document_id = None
            identification_document_name = None
        else:
            identification_document = identification_document.get()
            identification_document_id = identification_document.document_number
            identification_document_name = identification_document.document_name

        background_tasks.add_task(
            func=Notify.notify_sell_order,
            bot=bot,
            txid=txid,
            username=tx.user.username,
            value_from_btc=int(tx.value_from_btc),
            value_to_brl=float(tx.value_to_brl),
            identifier=tx.identifier,
            address=address,
            identification_document_id=identification_document_id,
            identification_document_name=identification_document_name,
            channel_id=HISTORY_CHANNEL_ID
        )
    
    return { "message": f"We received your payment successfully: {txid}." }

@router.put("/api/v1/upload-receipt/{txid}")
def upload_receipt(
        txid: str,
        background_tasks: BackgroundTasks,
        receipt: UploadFile = File(...),
        current_user: str = Depends(get_current_user)
    ):
    tx = database.RampBUYAndSELL.select().where(
        (database.RampBUYAndSELL.user == current_user) & 
        (database.RampBUYAndSELL.id == txid) &
        (database.RampBUYAndSELL.order_type == "BUY"))
    if not tx.exists():
        raise HTTPException(400, "Tx not found.")
    else:
        tx = tx.get()

    if tx.expiry_at.timestamp() <= time():
        raise HTTPException(400, "Tx has expired.")

    if tx.receipt_path:
        raise HTTPException(409, "Proof of payment has already been sent.")
    
    address_info = database.RampAddressInfo.select().where(
        (database.RampAddressInfo.ramp == txid))
    if not address_info.exists():
        raise HTTPException(400, "It is necessary to add an address.")
    else:
        address_info = address_info.get()

    # Initialize Bucket
    bucket = storage.bucket()
    
    # Initialize Blob Bucket
    file_path = f"{txid}.jpg"
    blob = bucket.blob(file_path)
    blob.upload_from_string(receipt.file.read(), content_type="image/jpeg")
    tx.receipt_path = f"firebase:{file_path}"

    identification_document = database.IdentificationDocument.select().where(
        (database.IdentificationDocument.user == current_user) &
        (database.IdentificationDocument.document_type == "CPF")) 
    if not identification_document.exists():
        identification_document_id = None
        identification_document_name = None
    else:
        identification_document = identification_document.get()
        identification_document_id = identification_document.document_number
        identification_document_name = identification_document.document_name

    tx.status = "pending"
    tx.save()
    if PIX_PROVIDER == "INTER":
        try:
            address = database.RampAddressInfo\
                .select(database.RampAddressInfo.address)\
                    .where((database.RampAddressInfo.ramp == txid))\
                        .get().address
        except Exception as error:
            logging.error(str(error), exc_info=True)
            address = None
        
        try:
            status = inter.inter.get_cob(txid)["status"]
        except Exception as error:
            logging.error(str(error), exc_info=True)
            status = None

        if address and status == "CONCLUIDA":
            tx_details = inter.search_tx(txid)
            if tx_details:
                tx_value = float(tx_details["valor"])
                tx_cpf_cnpj = tx_details["detalhes"]["cpfCnpjPagador"]
                tx_end_to_end_id = tx_details["detalhes"]["endToEndId"]

                if (str(tx_cpf_cnpj) != str(identification_document_id)):
                    inter.inter.pix_refund(tx_end_to_end_id, txid, tx_value)
                    tx.status = "cancelled"
                    tx.save()
                    raise HTTPException(400, "The source of payment comes from an unknown source.")

                def update_order_status_after_payment(paid: bool, **kwargs: dict):
                    txid = kwargs.get("txid")
                    tx = database.RampBUYAndSELL.select().where(
                        (database.RampBUYAndSELL.id == txid) &
                        (database.RampBUYAndSELL.order_type == "BUY"))
                    tx = tx.get()
                    if paid:
                        swap = quote.get_quote(txid).get("swap")
                        if swap:
                            try:
                                coinos.pay_bitcoin_and_liquid(
                                    amount=round(tx.value_to_btc), 
                                    address=swap["address"]
                                )
                                tx.status = "settled"
                                tx.save()
                            except Exception as error:
                                logging.error(str(error), exc_info=True)
                        else:
                            tx.status = "settled"
                            tx.save()

                if TRANSFER_MIN_VALUE_AUTO >= tx.value_from_brl and \
                        TRANSFER_MIN_VALUE_AUTO <= tx.value_from_brl: 
                    background_tasks.add_task(
                        func=lightning.payinvoice,
                        invoice=address,
                        callback=update_order_status_after_payment,
                        tx=tx,
                        txid=txid
                    )

    # Notify the processing operator about the 
    # completion of a specific task.
    background_tasks.add_task(
        func=Notify.notify_purchase_order,
        bot=bot,
        txid=txid,
        username=tx.user.username,
        value_from_brl=tx.value_from_brl,
        value_to_btc=tx.value_to_btc,
        identifier=tx.identifier,
        address=address_info.address,
        bank_id=BANK_ID,
        bank_name=BANK_NAME,
        bank_full_name=PIX_NAME,
        bank_key=PIX_KEY,
        identification_document_id=identification_document_id,
        identification_document_name=identification_document_name,
        channel_id=HISTORY_CHANNEL_ID
    )
    return { "message": f"Receipt uploaded successfully for transaction: {txid}." }
