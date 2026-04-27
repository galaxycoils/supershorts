import time
import random
import functools
import logging
from typing import Any, Callable, TypeVar, Tuple, Union

T = TypeVar("T")

logger = logging.getLogger(__name__)

def with_backoff(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator that implements exponential backoff with jitter.
    
    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay between retries in seconds.
        exceptions: A tuple of exception classes that trigger a retry.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            retries = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}")
                        raise
                    
                    # Exponential backoff: base_delay * 2^retries
                    # Jitter: random value between 0 and the calculated delay
                    delay = min(base_delay * (2 ** (retries - 1)), max_delay)
                    jitter = random.uniform(0, delay)
                    sleep_time = delay + jitter
                    
                    logger.warning(
                        f"Retry {retries}/{max_retries} for {func.__name__} after {sleep_time:.2f}s due to {type(e).__name__}: {e}"
                    )
                    time.sleep(sleep_time)
        return wrapper
    return decorator
