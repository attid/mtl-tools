import asyncio
from functools import wraps
from time import time
from typing import Optional, Any, Tuple
from collections import OrderedDict


class AsyncTTLCache:
    def __init__(self, ttl_seconds: int, maxsize: int = 128):
        self.ttl_seconds = ttl_seconds
        self.maxsize = maxsize
        self.cache: OrderedDict[str, Tuple[float, Any]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Returns the value from the cache if it is valid (not expired), otherwise removes the key and returns None."""
        async with self._lock:
            if key in self.cache:
                timestamp, value = self.cache[key]
                if time() - timestamp < self.ttl_seconds:
                    self.cache.move_to_end(key)
                    return value
                else:
                    del self.cache[key]
            return None

    async def set(self, key: str, value: Any) -> None:
        """Forcibly sets a key in the cache. Does nothing if the value is None."""
        if value is None:
            return

        async with self._lock:
            if len(self.cache) >= self.maxsize and key not in self.cache:
                self.cache.popitem(last=False)  # удаляем самый старый элемент
            self.cache[key] = (time(), value)
            # Явно перемещаем в конец для обеспечения LRU-порядка
            self.cache.move_to_end(key)

    async def invalidate(self, key: str) -> bool:
        """Forcibly removes a key from the cache. Returns True if the key was removed, False if the key was not present."""
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False


def async_cache_with_ttl(ttl_seconds: int, maxsize: int = 32):
    cache = AsyncTTLCache(ttl_seconds, maxsize)

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key_parts = [repr(args)]
            if kwargs:
                key_parts.append(repr(tuple(sorted(kwargs.items()))))
            cache_key = "".join(key_parts)

            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            result = await func(*args, **kwargs)

            await cache.set(cache_key, result)

            return result

        return wrapper

    return decorator


# Примеры использования:

# С дефолтным maxsize=32
@async_cache_with_ttl(ttl_seconds=3600)
async def get_fund_signers():
    print('real call')
    return 'data'


# Тестирование
async def test():
    result1 = await get_fund_signers()
    print(result1)

    # Повторный вызов должен взять из кэша
    result2 = await get_fund_signers()
    print(result2)


if __name__ == "__main__":
    asyncio.run(test())
