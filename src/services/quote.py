from src.services.helpers import calculate_percentage, fiat_to_sats, sats_to_fiat
from bitpreco import BitPreco
from datetime import datetime
from secrets import token_hex
from uuid import uuid4

bitpreco = BitPreco()

class Quote:

    def __init__(self, redis: object):
        self.redis = redis

    def get_price_provider(self) -> dict:
        price = bitpreco.get_price()
        return {"BUY": price["SELL"], "SELL": price["SELL"], "RATIO": price["RATIO"]}

    def get_price_service(self, feerate_buy=0, feerate_sell=0):
        price_provider = self.get_price_provider()
        price_services_buy = price_provider["SELL"] + \
            calculate_percentage(x=price_provider["SELL"] , y=feerate_buy)
        price_services_sell = price_provider["BUY"] - \
            calculate_percentage(x=price_provider["BUY"], y=feerate_sell)
        return { "BUY": price_services_buy, "SELL": price_services_sell, "RATIO": price_provider["RATIO"] }
    
    def get_quote(self, txid: str) -> dict:
        return self.redis.redis_get(key=f"tx.{txid}")

    def update_exp(self, txid: str, expiry_at=60 * 10) -> dict:
        quote = self.get_quote(txid)
        quote["updated_at"] = datetime.now().timestamp()
        return self.redis.redis_set(key=f"tx.{txid}", value=quote, expiry_at=expiry_at)

    def make_sell(self, value: float, fees: dict) -> dict:
        """
        Create a SELL with the specified value.

        Args:
            value (float): The value of the SELL in fiat currency.
            fees (dict): A dictionary containing the fees for price and value calculations.
        """
        price_provider = self.get_price_provider()["BUY"]

        # Calculate the price including fees
        price_services = price_provider
        price_services-= calculate_percentage(price_provider, fees["price"])
        
        value_with_fee = value
        value_with_fee+= calculate_percentage(
            x=value, 
            y=fees["services"] + \
                fees["provider"]
        )
        value_sell_in_btc = fiat_to_sats(
            x=value_with_fee, 
            y=price_services
        )

        txid = token_hex(15)

        fees["total"] = (fees["services"] + fees["provider"] + fees["price"])
        fees["value"] = (value_sell_in_btc - \
                         fiat_to_sats(value, price_provider))
        return {
            "txid": txid,
            "type": "SELL",
            "values": {
                "from": {
                    "btc": value_sell_in_btc,
                    "brl": sats_to_fiat(
                        x=value_sell_in_btc, 
                        y=price_services
                    ),
                },
                "to": {
                    "brl": value, 
                    "btc": fiat_to_sats(
                        x=value, 
                        y=price_provider
                    )
                },
            },
            "prices": {
                "provider": price_provider, 
                "services": price_services
            },
            "fees": {
                "rate": {
                    "services": fees["services"],
                    "provider": fees["provider"],
                    "price":    fees["price"],
                    "total":    fees["total"]
                },
                "value": fees["value"],
            },
            "identifier": token_hex(2).upper(),
            "created_at": datetime.now().timestamp(),
            "updated_at": datetime.now().timestamp()
        }

    def create_sell(self, tx: dict, expiry_at=60 * 10) -> dict:
        """
        Create a sell in the Redis cache.

        Args:
            tx (dict): The details of the sell.
        """
        tx["updated_at"] = datetime.now().timestamp()
        return self.redis.redis_set(key=f"tx.{tx['txid']}", value=tx, expiry_at=expiry_at)

    def make_purchase(self, value: float, fees: dict, network: str = "LN") -> dict:
        """
        Create a purchase with the specified value.

        Args:
            value (float): The value of the purchase in fiat currency.
            fees (dict): A dictionary containing the fees for price and value calculations.
        """
        price_provider = self.get_price_provider()["SELL"]

        # Calculate the price including fees
        price_services = price_provider
        price_services += calculate_percentage(x=price_provider, y=fees["price"])

        value_discounted_fees = value
        value_discounted_fees-= calculate_percentage(x=value, y=fees["services"] + fees["provider"])

        txid = token_hex(15)

        fees["total"] = (fees["services"] + fees["provider"] + fees["price"])
        fees["value"] = value - value_discounted_fees
        return {
            "txid": txid,
            "type": "BUY",
            "values": {
                "from": {
                    "brl": value, 
                    "btc": fiat_to_sats(
                        x=value, 
                        y=price_services
                    )
                },
                "to": {
                    "brl": value_discounted_fees,
                    "btc": fiat_to_sats(
                        x=value_discounted_fees, 
                        y=price_services
                    ),
                },
            },
            "prices": {
                "provider": price_provider, 
                "services": price_services
            },
            "fees": {
                "rate": {
                    "services": fees["services"],
                    "provider": fees["provider"],
                    "price": fees["price"],
                    "total": fees["total"],
                },
                "value": fees["value"],
            },
            "network":    network.upper(),
            "identifier": token_hex(5).upper(),
            "created_at": datetime.now().timestamp(),
            "updated_at": datetime.now().timestamp(),
        }

    def create_purchase(self, tx: dict, expiry_at=60 * 10) -> dict:
        """
        Create a purchase in the database and Redis cache.

        Args:
            tx (dict): The details of the purchase.
        """
        tx["updated_at"] = datetime.now().timestamp()
        return self.redis.redis_set(key=f"tx.{tx['txid']}", value=tx, expiry_at=expiry_at)
