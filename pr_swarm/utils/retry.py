"""Simple asynchronous retry helper used by the PR Agent Swarm.

This module provides a small helper function for running an async call
with retries and exponential backoff. It avoids external dependencies like
``tenacity`` to keep the core library lightweight.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Iterable, Tuple, Type


async def retry_async(
    func: Callable[..., Awaitable[Any]],
    *args: Any,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    attempts: int = 3,
    initial_wait: float = 1.0,
    max_wait: float = 8.0,
    **kwargs: Any,
) -> Any:
    """Execute ``func`` with retries and exponential backoff.

    Parameters
    ----------
    func: Callable[..., Awaitable[Any]]
        The asynchronous function to invoke.
    *args: Any
        Positional arguments passed to ``func``.
    exceptions: Tuple[Type[BaseException], ...]
        A tuple of exception classes that should trigger a retry.
    attempts: int
        The maximum number of attempts. The function will be called up to this
        many times. The first call counts as the first attempt.
    initial_wait: float
        The initial backoff delay in seconds. Each retry waits for this amount
        before doubling, capped by ``max_wait``.
    max_wait: float
        The maximum backoff delay in seconds.
    **kwargs: Any
        Keyword arguments passed to ``func``.

    Returns
    -------
    Any
        Whatever ``func`` returns.

    Raises
    ------
    Exception
        Re-raises the last exception if all attempts fail.
    """
    delay = initial_wait
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await func(*args, **kwargs)
        except exceptions as exc:  # type: ignore[misc]
            last_exc = exc
            if attempt == attempts:
                break
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_wait)
    # If we exit the loop without returning, raise the last exception
    if last_exc is not None:
        raise last_exc
    # Should not reach here
    raise RuntimeError("retry_async failed without raising an exception")