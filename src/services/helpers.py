import base64
import re

def fiat_to_btc(x: float, y: float) -> float:
    """
    Convert a value from fiat currency to Bitcoin.

    Args:
        x (float): Value in fiat currency.
        y (float): Bitcoin price in fiat currency.
    """
    return x / y


def msats_to_sats(x: float) -> float:
    """
    Convert a value from mSats to Satoshi.

    Args:
        x (float): Value in msats.
    """
    return x / 1000


def fiat_to_sats(x: float, y: float) -> int:
    """
    Convert a value from fiat currency to Bitcoin.

    Args:
        x (float): Value in fiat currency.
        y (float): Bitcoin price in fiat currency.
    """
    return btc_to_sats(fiat_to_btc(x, y))


def btc_to_fiat(x: float, y: float) -> float:
    """
    Convert a value from Bitcoin to fiat currency.

    Args:
        x (float): Value in Bitcoin.
        y (float): Bitcoin price in fiat currency.
    """
    return x * y


def sats_to_fiat(x: float, y: float) -> float:
    """
    Convert a value from Satoshi to fiat currency.

    Args:
        x (float): Value in Bitcoin.
        y (float): Bitcoin price in fiat currency.
    """
    return btc_to_fiat(x=sats_to_btc(x), y=y)


def decode_base64(data, altchars=b'+/'):
    """Decode base64, padding being optional.

    Args 
        data (str): Base64 data as an ASCII byte string
    """
    if isinstance(data, str):
        data = str(data).encode()

    data = re.sub(rb'[^a-zA-Z0-9%s]+' % altchars, b'', data)
    missing_padding = len(data) % 4
    if missing_padding:
        data += b'='* (4 - missing_padding)

    return base64.b64decode(data, altchars)


def sats_to_btc(x: float) -> float:
    """
    Convert a value from Satoshis to Bitcoin.

    Args:
        x (float): Value in Satoshis.
    """
    return x / pow(10, 8)


def btc_to_sats(x: float) -> float:
    """
    Convert a value from Bitcoin to Satoshis.

    Args:
        x (float): Value in Bitcoin.
    """
    return x * pow(10, 8)


def calculate_percentage(x: float, y: float) -> float:
    """
    Calculate the percentage of a value.

    Args:
        x (float): Value to calculate the percentage of.
        y (float): Percentage value.
    """
    return x * y / 100

def calculate_percentage_difference(x: float, y: float) -> float:
    """
    Calculates the percentage difference between two values.

    Args:
        x (float): The first value.
        y (float): The second value.
    """
    if x == 0:
        return 0
    r = (abs(x - y) / abs(x)) * 100
    if y < x:
        return -r
    else:
        return r

def format_cpf(cpf: str) -> str:
    """
    Formats a CPF in Brazilian style.

    Args:
        cpf (str): CPF number as an 11-digit string.
    """
    try:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    except:
        return cpf

def calculate_simple_average(prices: list) -> float:
    """
    Calculates the simple average of a price list.

    Args:
        prices (list): List of prices.
    """
    try:
        return sum(prices) / len(prices)
    except:
        return 0

