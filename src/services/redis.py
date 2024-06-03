from src.configs import RedisConfig
from typing import Union
from redis import StrictRedis
from json import loads, dumps

import logging

class Redis:
    INSTANCE = None

    def __init__(self, prefix: str, configs: object):
        self.prefix = prefix
        self.configs = configs
        self.INSTANCE = StrictRedis(
            host=self.configs.REDIS_HOST,
            port=self.configs.REDIS_PORT,
            password=self.configs.REDIS_PASS,
        )

    def redis_get(self, key: str) -> dict:
        if not self.prefix in key:
            key = self.prefix + key
        
        try:
            data = self.INSTANCE.get(key)
            if not data:
                return {}
            else:
                return loads(data)
        except Exception as error:
            logging.error(str(error), exc_info=True)
            if "password" in str(error):
                self.INSTANCE = StrictRedis(
                    host=self.configs.REDIS_HOST,
                    port=self.configs.REDIS_PORT,
                    password=self.configs.REDIS_PASS,
                )
                return loads(redis.get(key))
            else:
                return {}

    def redis_del(self, key: str) -> bool:
        if not self.prefix in key:
            key = self.prefix + key
        
        try:
            self.INSTANCE.delete(key)
            return True
        except Exception as error:
            logging.error(str(error), exc_info=True)
            if "password" in str(error):
                self.INSTANCE = StrictRedis(
                    host=self.configs.REDIS_HOST,
                    port=self.configs.REDIS_PORT,
                    password=self.configs.REDIS_PASS,
                )
                self.INSTANCE.delete(key)
            return False

    def redis_set(
        self, key: str, value: Union[dict, list], expiry_at: int = None
    ) -> bool:
        if not self.prefix in key:
            key = self.prefix + key
        
        try:
            self.INSTANCE.set(key, dumps(value))
            if expiry_at:
                self.INSTANCE.expire(key, int(expiry_at))
            return value
        except Exception as error:
            logging.error(str(error), exc_info=True)
            if "password" in str(error):
                self.INSTANCE = StrictRedis(
                    host=self.configs.REDIS_HOST,
                    port=self.configs.REDIS_PORT,
                    password=self.configs.REDIS_PASS,
                )
                self.INSTANCE.set(key, dumps(value))
                if expiry_at:
                    self.INSTANCE.expire(key, int(expiry_at))  
                return value   
            return value

    def redis_update(self, key: str, data: dict, expiry_at: int = None) -> bool:
        if not self.prefix in key:
            key = self.prefix + key
        
        value = self.redis_get(key)
        value.update(data)
        return self.redis_set(key, value, expiry_at=expiry_at)

    def redis_expire(self, key: str, expiry_at: int = None):
        if not self.prefix in key:
            key = self.prefix + key
        
        return self.INSTANCE.expire(key, int(expiry_at))

redis = Redis(prefix=RedisConfig().REDIS_PREFIX, configs=RedisConfig())