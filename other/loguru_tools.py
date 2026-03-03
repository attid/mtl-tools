import asyncio
from typing import TypeVar, Callable
from functools import wraps
from loguru import logger
from sentry_sdk import capture_exception

T = TypeVar("T")


def safe_catch(func: Callable[..., T]) -> Callable[..., T]:
    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.exception(f"Error in {func.__name__}")
            capture_exception()
            raise

    return wrapper


def safe_catch_async(func: Callable[..., T]) -> Callable[..., T]:
    @wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        try:
            return await func(*args, **kwargs)
        except asyncio.CancelledError:
            # Normal during shutdown, don't log as error
            raise
        except Exception:
            logger.exception(f"Error in {func.__name__}")
            capture_exception()
            raise

    return wrapper
