from src.lib.bitfinex import Bitfinex
from src.configs import BITFINEX_API_KEY, BITFINEX_API_SECRET_KEY

bitfinex = Bitfinex(
    api_key=BITFINEX_API_KEY, 
    api_secret_key=BITFINEX_API_SECRET_KEY
)
