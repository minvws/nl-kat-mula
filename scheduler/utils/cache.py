import logging
from datetime import datetime, timedelta
from functools import lru_cache, wraps

log = logging.getLogger(__name__)


def ttl_lru_cache(ttl: int, maxsize: int = 128):
    def inner(func):
        func = lru_cache(maxsize=maxsize)(func)
        func.lifetime = timedelta(seconds=ttl)
        func.expiration = datetime.utcnow() + func.lifetime

        @wraps(func)
        def wrapper(*args, **kwargs):
            if datetime.utcnow() >= func.expiration:
                log.debug(f"Cache expired for {func.__name__}")
                func.cache_clear()
                func.expiration = datetime.utcnow() + func.lifetime

            return func(*args, **kwargs)

        return wrapper

    return inner
