from src.configs import INTER_CLIENT_ID, INTER_CLIENT_SECRET, INTER_GRANT_TYPE, INTER_CERT, INTER_KEY
from datetime import datetime
from inter import Inter

import logging

try:
    inter = Inter(
        client_id=INTER_CLIENT_ID,
        client_secret=INTER_CLIENT_SECRET,
        grant_type=INTER_GRANT_TYPE
    )

    inter.load_cert(INTER_CERT, INTER_KEY)
except Exception as error:
    logging.error(str(error), exc_info=True)
    inter = None

def search_tx(
        txid: str, 
        date_start: str = None, 
        date_end: str = None
    ) -> dict:
    """
    Search for a transaction by its transaction ID within a specified date range.

    Args:
        txid (str): The transaction ID to search for.
        date_start (str): The start date of the search range in "YYYY-MM-DD" format.
        date_end (str): The end date of the search range in "YYYY-MM-DD" format.
    """
    if not date_start:
        date_start = datetime.now().strftime("%Y-%m-%d")

    if not date_end:
        date_end = datetime.now().strftime("%Y-%m-%d")
    
    try:
        history = inter.get_history(
            date_start,
            date_end,
            page=0,
            size=50
        )
    except Exception as error:
        logging.error(str(error), exc_info=True)
        return {}

    try:
        return list(filter(lambda data: data["detalhes"]["txId"] \
                        == txid, history["transacoes"]))[0]
    except:
        return {}


            