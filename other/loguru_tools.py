from typing import TypeVar, Callable
from functools import wraps
from loguru import logger

T = TypeVar('T')


def safe_catch(func: Callable[..., T]) -> Callable[..., T]:
    @wraps(func)
    @logger.catch()
    def wrapper(*args, **kwargs) -> T:
        return func(*args, **kwargs)

    return wrapper


def safe_catch_async(func: Callable[..., T]) -> Callable[..., T]:
    @wraps(func)
    @logger.catch()
    async def wrapper(*args, **kwargs) -> T:
        return await func(*args, **kwargs)

    return wrapper
