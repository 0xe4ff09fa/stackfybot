from src.configs import LNBITS_ADMIN_KEY, LNBITS_INVOICE_KEY, LNBITS_URL
from lnbits import Lnbits

import logging

# Initialize Lnbits
lnbits = Lnbits(
    admin_key=LNBITS_ADMIN_KEY,
    invoice_key=LNBITS_INVOICE_KEY,
    url=LNBITS_URL
)

def payinvoice(invoice: str, callback: object = None, **kwargs: dict) -> dict:
    """
    Pays an LNBits invoice and checks its status.

    Args:
        invoice (str): The LNBits invoice to be paid.
        callback (object): An optional callback function.
        **kwargs (dict): Additional keyword arguments for the callback.
    """
    try:
        pay_invoice = lnbits.pay_invoice(invoice)
    except Exception as error:
        logging.error(str(error), exc_info=True)
        pay_invoice = dict()

    try:
        check_invoice_status = lnbits.check_invoice_status(
            payment_hash=pay_invoice.get("payment_hash", "")).get("paid", False)
    except Exception as error:
        logging.error(str(error), exc_info=True)
        check_invoice_status = False
    
    if callback:
        callback(check_invoice_status, **kwargs)
    
    return { "paid": check_invoice_status }

def addinvoice(value: int, memo: str, expiry=((60 * 60) * 2)) -> dict:
    """
    Adds an invoice for a payment.

    Args:
        value (int): The payment value in satoshis.
        memo (str): An optional description for the invoice.
    """
    invoice = lnbits.create_invoice(value, memo, expiry=expiry)
    return { 
        "r_hash": invoice["payment_hash"],
        "hash": invoice["payment_hash"],
        "payment_request": invoice["payment_request"]
    }

def check_payment(payment_hash: str) -> dict:
    """
    Checks the status of a payment based on the payment hash.

    Args:
        payment_hash (str): The payment hash to be checked.
    """
    return lnbits.check_invoice_status(payment_hash)
