from src.configs import Features
from functools import wraps

def featuresEnabled(flag: str) -> object:
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            if Features().check(flag):
                return function(*args, **kwargs)
            else:
                return None
        return wrapper
    return decorator