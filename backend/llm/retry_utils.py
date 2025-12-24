"""Retry utilities for LLM API calls with exponential backoff"""

import time
from typing import Callable, TypeVar, Optional
from functools import wraps
from core import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """Decorator for retrying function calls with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch and retry

    Example:
        @retry_with_backoff(max_retries=3, initial_delay=1.0)
        def call_openai_api():
            return client.chat.completions.create(...)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        # Last attempt failed, raise the exception
                        logger.error(
                            "retry_max_attempts_exceeded",
                            function=func.__name__,
                            attempts=max_retries + 1,
                            error=str(e),
                        )
                        raise

                    # Log retry attempt
                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay=delay,
                        error=str(e),
                    )

                    # Wait before retrying
                    time.sleep(delay)
                    delay *= backoff_factor

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def call_llm_with_retry(
    llm_func: Callable[..., T],
    *args,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    **kwargs,
) -> Optional[T]:
    """Call LLM function with automatic retry on failure

    Args:
        llm_func: Function to call (e.g., OpenAI API call)
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay before first retry
        *args, **kwargs: Arguments to pass to llm_func

    Returns:
        Result from llm_func or None if all retries failed

    Example:
        result = call_llm_with_retry(
            client.chat.completions.create,
            model="gpt-4o-mini",
            messages=[...]
        )
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return llm_func(*args, **kwargs)
        except Exception as e:
            last_exception = e

            if attempt == max_retries:
                logger.error(
                    "llm_call_failed_after_retries",
                    attempts=max_retries + 1,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                return None

            logger.warning(
                "llm_call_retry",
                attempt=attempt + 1,
                max_retries=max_retries,
                delay=delay,
                error=str(e),
                error_type=type(e).__name__,
            )

            time.sleep(delay)
            delay *= 2.0  # Exponential backoff

    return None
