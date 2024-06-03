from requests import request

class Swap:

    def __init__(self, url: str = "https://swap.stklabs.xyz"):
        self.url = url

    def call(self, method: str, path: str, data=None, params=None) -> dict:
        return request(method=method, url=self.url + path, json=data, params=params).json()
    
    def get_info(self) -> dict:
        return self.call("GET", "/api/v1/info")

    def calculate(self, value: int, feerate: int) -> dict:
        return self.call("GET", "/api/v1/calculate", params={"value": int(value), "feerate": feerate})

    def create_swap(self, address: str, value: int, feerate: int) -> dict:
        return self.call("POST", "/api/v1/swap", data={"address": address, "amount": value, "feerate": feerate})

    def get_swap(self, txid: str) -> dict:
        return self.call("GET", f"/api/v1/swap/{txid}")
