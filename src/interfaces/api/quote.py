from src.interfaces.api.middlewares import get_current_user, get_user_without_kyc_validation
from src.services.bitfinex import bitfinex
from src.services.helpers import sats_to_fiat
from src.services.quote import Quote
from src.services.redis import redis
from src.configs import COINOS_LIQUID_RATE_FEE, FEERATE_PROVIDER, PURCHASE_FEERATE_PRICE, PURCHASE_MAX_VALUE, PURCHASE_MIN_VALUE, SELL_MAX_VALUE, SELL_MIN_VALUE
from src.configs import PURCHASE_FEERATE_SERVICES, SELL_FEERATE_PRICE, SELL_FEERATE_SERVICES
from pydantic import PositiveFloat
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from mempool import Mempool
from src import database

import logging

# Initialize APIRouter
router = APIRouter()

# Initialize Quote
quote = Quote(redis=redis)

# Initialize Mempool
mempool = Mempool()

@router.get("/api/v1/price")
async def get_price():
    price = quote.get_price_service(
        feerate_buy=PURCHASE_FEERATE_PRICE,
        feerate_sell=SELL_FEERATE_PRICE
    )
    return { "BUY": price["BUY"], "SELL": price["SELL"], "RATIO": price["RATIO"] }

@router.get("/api/v1/candles")
async def get_candles():
    candles = bitfinex.candles()
    return { "candles": [{"timestamp": candle[0], "price": candle[2]} for candle in candles] }

@router.get("/api/v1/quote/info")
def get_quote_info(current_user: str = Depends(get_user_without_kyc_validation)):
    return {
        "buy": {
            "min": PURCHASE_MIN_VALUE,
            "max": PURCHASE_MAX_VALUE
        },
        "sell": {
            "min": SELL_MIN_VALUE,
            "max": SELL_MAX_VALUE
        }
    }

@router.get("/api/v1/quotes")
async def quotes(
        value: PositiveFloat, 
        network: str = "LN",
        operation: str = "BUY", 
        current_user: str = Depends(get_current_user)
    ):
    network = str(network).upper()
    if operation == "BUY":
        if value < PURCHASE_MIN_VALUE:
            raise HTTPException(400, f"Minimum value is R$ {PURCHASE_MIN_VALUE}.")

        if value > PURCHASE_MAX_VALUE:
            raise HTTPException(400, f"Maximum value is R$ {PURCHASE_MAX_VALUE}.")
        
        fee_price = PURCHASE_FEERATE_PRICE
        if network == "LIQUID":
            fee_price += COINOS_LIQUID_RATE_FEE
        
        tx = quote.make_purchase(value, {
            "services": PURCHASE_FEERATE_SERVICES,
            "provider": FEERATE_PROVIDER,
            "price": fee_price,
        }, network=network)
        if network == "LIQUID":
            try:
                swap_value = tx["values"]["to"]["btc"]
                feerate = mempool.fees_recommended(network="liquid")["fastestFee"]
                fees = feerate * 3000
                tx["values"]["to"]["btc"]-= round(fees)
                tx["values"]["to"]["brl"] = sats_to_fiat(
                    tx["values"]["to"]["btc"], 
                    tx['prices']['services']
                )
                tx["swap"] = { "feerate": feerate, "value": swap_value }
            except Exception as error:
                logging.error(str(error), exc_info=True)
                raise HTTPException(500)
        
        quote.create_purchase(tx, expiry_at=60 * 3)
    else:
        if value < SELL_MIN_VALUE:
            raise HTTPException(400, f"Minimum value is R$ {SELL_MIN_VALUE}.")

        if value > SELL_MAX_VALUE:
            raise HTTPException(400, f"Maximum value is R$ {SELL_MAX_VALUE}.")
        
        tx = quote.make_sell(value, {
            "services": SELL_FEERATE_SERVICES,
            "provider": FEERATE_PROVIDER,
            "price":    SELL_FEERATE_PRICE,
        })
        quote.create_sell(tx, expiry_at=60 * 3)

    return { 
        "txid":  tx["txid"], 
        "type":  operation, 
        "quote": tx["values"], 
        "price": tx["prices"]["services"],
        "fee":   tx["fees"]["value"]
    }

@router.get("/api/v1/quote/{txid}")
async def get_quote(
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
    
    return {
        "txid":   txid,
        "type":   tx.order_type,
        "status": tx.status,
        "quote": {
            "from": {
                "brl": tx.value_from_brl,
                "btc": tx.value_from_btc
            },
            "to": {
                "brl": tx.value_to_brl,
                "btc": tx.value_to_btc
            }
        },
        "price": tx.price_services,
        "fee":   tx.fee_value
    }

@router.patch("/api/v1/quote/{txid}")
def quote_execute(
        txid: str, 
        current_user: str = Depends(get_current_user)
    ):
    tx = quote.get_quote(txid)
    if not tx:
        raise HTTPException(400, "Tx not found.")

    if database.RampBUYAndSELL.select().where(
        (database.RampBUYAndSELL.user == current_user) & 
        (database.RampBUYAndSELL.id == txid)).exists():
        raise HTTPException(400, "Tx not found.")
    
    database.RampBUYAndSELL.create(
        id=tx["txid"],
        user=current_user,
        status="created",
        order_type=tx["type"],
        value_from_btc=tx["values"]["from"]["btc"],
        value_from_brl=tx["values"]["from"]["brl"],
        value_to_btc=tx["values"]["to"]["btc"],
        value_to_brl=tx["values"]["to"]["brl"],
        price_services=tx["prices"]["services"],
        price_provider=tx["prices"]["provider"],
        fee_value=tx["fees"]["value"],
        fee_rate_price=tx["fees"]["rate"]["price"],
        fee_rate_services=tx["fees"]["rate"]["services"],
        fee_rate_provider=tx["fees"]["rate"]["provider"],
        identifier=tx["identifier"],
        expiry_at=(datetime.now() + timedelta(minutes=20))
    )
    quote.update_exp(txid, expiry_at=60 * 15)
    return { "message": f"Quote {txid} executed successfully." }