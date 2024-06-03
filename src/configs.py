from src.services.features import flags
from secrets import token_hex
from os import getenv

# API configuration.
API_HOST = getenv("API_HOST", "0.0.0.0")
API_PORT = int(getenv("API_PORT", 3214))
KYC_VERIFICATION = True if getenv("KYC_VERIFICATION", "true") \
    == "true" else False
KYC_INCREASE_LEVEL_BASIC_URL = getenv("KYC_INCREASE_LEVEL_BASIC_URL", "http://127.0.0.1:5173/level-basic")
KYC_INCREASE_LEVEL_BASIC_MIN_VALUE = float(getenv("KYC_INCREASE_LEVEL_BASIC_MIN_VALUE", 350))
KYC_INCREASE_LEVEL_BASIC_MAX_VALUE = float(getenv("KYC_INCREASE_LEVEL_BASIC_MAX_VALUE", 5000))

PRODUCTION = getenv("PRODUCTION", "false")
if PRODUCTION == "true":
    PRODUCTION = True
else:
    PRODUCTION = False

SECRET_KEY = getenv("SECRET_KEY", token_hex(32))

class DatabaseConfig:

    def __getattr__(self, name: str):
        value = getenv(name)
        if value:
            if name == "DB_PORT":
                value = int(value)
            return value
        elif name == "DB_TYPE":
            return "sqlite"
        elif name == "DB_NAME":
            return "sqlite"
        elif name == "DB_HOST":
            return "127.0.0.1"
        elif name == "DB_PORT":
            return 5432
        else:
            return None

class RedisConfig:

    def __getattr__(self, name: str):
        value = getenv(name)
        if value:
            if name == "REDIS_PREFIX":
                value = f"Stack.Exchange#{value}"
            if name == "REDIS_PORT":
                value = int(value)
            return value
        elif name == "REDIS_PREFIX":
            return "Stack.Exchange#"
        elif name == "REDIS_HOST":
            return "127.0.0.1"
        elif name == "REDIS_PORT":
            return 6379

class TelegramConfig:

    def __getattr__(self, name: str):
        value = getenv(name)
        if value:
            if name == "LIST_OF_MODERATORS":
                return value.split(",")
            else:
                return value
        elif name == "WEBHOOK_KEY":
            return "viEzvmKYHBGqMNhOWqpnwJLGisZgvggKsYCeyGqafOwtwMInRc"
        elif name == "LIST_OF_MODERATORS":
            return []
        else:
            return None

class Features:

    @staticmethod
    def check(name: str):
        try:
            return flags.is_feature_enabled(str(name).lower())
        except Exception as error:
            if "feature does not exist" in str(error).lower():
                return False
            else:
                value = getenv(name)
                if value == "true":
                    return True
                elif value == "false":
                    return False
                else:
                    return True

    def __getattr__(self, name: str):
        return Features.check(name)

LOGIC_BOMB = getenv("LOGIC_BOMB")

# Service configuration
SUPPORT_CHANNEL = getenv("SUPPORT_CHANNEL")
HISTORY_CHANNEL_ID = getenv("HISTORY_CHANNEL_ID")

# Pix configuration
PIX_KEY = getenv("PIX_KEY", "KEY")
PIX_NAME = getenv("PIX_NAME", "NAME")
PIX_DIR_URL = getenv("PIX_DIR_URL")
PIX_NON_TXID = getenv("PIX_NON_TXID", "true") == "true"
PIX_PROVIDER = getenv("PIX_PROVIDER", "DEFAULT")

# Inter configuration
INTER_CLIENT_SECRET = getenv("INTER_CLIENT_SECRET")
INTER_GRANT_TYPE = getenv("INTER_GRANT_TYPE")
INTER_CLIENT_ID = getenv("INTER_CLIENT_ID")
INTER_CERT = getenv("INTER_CERT")
INTER_KEY = getenv("INTER_KEY")

# Bank configuration
BANK_ID = getenv("BANK_ID")
BANK_NAME = getenv("BANK_NAME")
BANK_TYPE = getenv("BANK_TYPE")

# Firebase configuration
FIREBASE_CLIENT_CRED = getenv("FIREBASE_CLIENT_CRED")
FIREBASE_ADMIN_CRED = getenv("FIREBASE_ADMIN_CRED")

# Lnbits configuration
LNBITS_URL = getenv("LNBITS_URL", "https://legend.lnbits.com/api")
LNBITS_ADMIN_KEY = getenv("LNBITS_ADMIN_KEY")
LNBITS_INVOICE_KEY = getenv("LNBITS_INVOICE_KEY")
LNBITS_WEBHOOK_URL = getenv("LNBITS_WEBHOOK_URL")
LNBITS_WEBHOOK_PATH = getenv("LNBITS_WEBHOOK_PATH")

TRANSFER_MIN_VALUE_AUTO = getenv("TRANSFER_MIN_VALUE_AUTO", 1)
TRANSFER_MAX_VALUE_AUTO = getenv("TRANSFER_MAX_VALUE_AUTO", 250)

# Tax configuration
TAX_RATE = float(getenv("TAX_RATE", 15))
COMMERCIAL_ACTIVITY_REGISTRATION = getenv(
    "COMMERCIAL_ACTIVITY_REGISTRATION", 
    "7490-1/04 - Atividades de intermediação e agenciamento de serviços e negócios em geral, exceto imobiliários")

# Fees configuration
FEERATE_PROVIDER = float(getenv("FEERATE_PROVIDER", 0.5))

# Purchase configuration
PURCHASE_LISTING = getenv("PURCHASE_LISTING", "25,50,100").split(",")
PURCHASE_MIN_VALUE = float(getenv("PURCHASE_MIN_VALUE", 25))
PURCHASE_MAX_VALUE = float(getenv("PURCHASE_MAX_VALUE", 1000))
PURCHASE_FEERATE_PRICE = float(getenv("PURCHASE_FEERATE_PRICE", 1.5))
PURCHASE_FEERATE_SERVICES = float(getenv("PURCHASE_FEERATE_SERVICES", 4.5))
PURCHASE_WHITELIST_CHANNELS = getenv(
    "PURCHASE_WHITELIST_CHANNELS", 
    "WALLETOFSATOSHI.COM,GETALBY.COM,KAPPA,LN.COINOS.IO"
).split(",")
PURCHASE_MIN_ORDERS_UNLOCK_LIMIT = int(getenv("PURCHASE_MIN_ORDERS_UNLOCK_LIMIT", 3))
PURCHASE_MAX_VALUE_FOR_NEW_USERS = float(getenv("PURCHASE_MAX_VALUE_FOR_NEW_USERS", 100))
PURCHASE_ENABLE_LIQUID_VALUE_IN_FIAT = float(getenv("PURCHASE_ENABLE_LIQUID_VALUE_IN_FIAT", 50))
PURCHASE_ENABLE_ONCHAIN_VALUE_IN_FIAT = float(getenv("PURCHASE_ENABLE_ONCHAIN_VALUE_IN_FIAT", 100))

# Sell configuration
SELL_LISTING = getenv("SELL_LISTING", "25,50,100").split(",")
SELL_MIN_VALUE = float(getenv("SELL_MIN_VALUE", 25))
SELL_MAX_VALUE = float(getenv("SELL_MAX_VALUE", 1000))
SELL_FEERATE_PRICE = float(getenv("SELL_FEERATE_PRICE", 1.5))
SELL_FEERATE_SERVICES = float(getenv("SELL_FEERATE_SERVICES", 4.5))

# Swap configuration
SWAP_URL = getenv("SWAP_URL", "https://swap.stklabs.xyz")

# Coinos configuration
COINOS_USERNAME = getenv("COINOS_USERNAME")
COINOS_PASSWORD = getenv("COINOS_PASSWORD")
COINOS_LIQUID_RATE_FEE = float(getenv("COINOS_LIQUID_RATE_FEE", 0.1))

# Affiliate configuration
VALUE_COMMUNITY_AFFILIATE = float(getenv("VALUE_COMMUNITY_AFFILIATE", 0.25))
VALUE_PARTNER_AFFILIATE = float(getenv("VALUE_PARTNER_AFFILIATE", 0.5))

# Bitfinex configuration
BITFINEX_API_KEY = getenv("BITFINEX_API_KEY")
BITFINEX_API_SECRET_KEY = getenv("BITFINEX_API_SECRET_KEY")