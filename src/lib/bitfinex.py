import hashlib
import hmac
import json
import requests
import time

class Bitfinex:

    def __init__(
            self, 
            api_key=None, 
            api_secret_key=None, 
            url="https://api.bitfinex.com/", 
            url_pub="https://api-pub.bitfinex.com/"
        ):
        self.__url = url
        self.__url_pub = url_pub
        self.__api_key = api_key
        self.__api_secret_key = api_secret_key

    def sign(self, path: str, nonce: str, data: str):
        if self.__api_key and self.__api_secret_key:
            payload = f"/api/{path}{nonce}{data.decode('utf-8')}"
            signature = hmac.new(bytes(self.__api_secret_key, 'utf-8'), bytes(payload, 'utf-8'), hashlib.sha384)
            return signature.hexdigest()
        else:
            return ""
    
    def call(self, method: str, path: str, data=None, params=None):
        body = json.dumps(data).encode('utf-8')
        nonce = str(int(time.time() * 1000))

        headers = {
            'Content-Type': 'application/json',
            'bfx-nonce': nonce,
            'bfx-apikey': self.__api_key,
            'bfx-signature': self.sign(path, nonce, body),
        }
        response = requests.request(method.upper(), self.__url + path, headers=headers, params=params, data=body)
        response.raise_for_status()
        return response.json()
    
    def call_pub(self, method: str, path: str) -> dict:
        response = requests.request(method=method, url=self.__url_pub + path)
        response.raise_for_status()
        return response.json()

    def candles(self, candle="trade:1W:tBTCUSD", section="hist"):
        return self.call_pub("GET", f"v2/candles/{candle}/{section}")

    def get_price(self, ticket="btcusd"):
        r = self.call("GET", f"v1/pubticker/{ticket}")
        return {"SELL": r["ask"], "BUY": r["bid"]}
    
    def deposit_address(self, method='', wallet="exchange"):
        if not method:
            method = 'bitcoin'

        data = {
            "wallet": wallet,
            "method": method,
            "op_renew": 1
        }
        return self.call("POST", "v2/auth/w/deposit/address", data)

    def create_invoice(self, amount):
        data = {"currency": "LNX", "wallet": "exchange", "amount": amount}
        return self.call("POST", "v2/auth/w/deposit/invoice", data)

    def get_wallets(self):
        data = {}
        return self.call("POST", "v2/auth/r/wallets", data)

    def movements(self, currency: str = "BTC", start=0, end=0, limit=0):
        data = dict()
        if start:
            data["start"] = start
        if end:
            data["end"] = end
        if limit:
            data["limit"] = limit
        return self.call("POST", f"v2/auth/r/movements/{currency}/hist", data=data)

    def order_submit(self, symbol, amount):
        data = {"symbol": symbol, "amount": amount, "type": "EXCHANGE"}
        return self.call("POST", "v2/auth/w/order/submit", data)