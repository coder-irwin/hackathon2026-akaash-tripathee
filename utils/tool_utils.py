import random
import asyncio
import functools
import json
import logging
from typing import Any, Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ShopWaveAgent")

import os

def simulate_realism(func: Callable):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if os.environ.get("SKIP_SIMULATION") == "true":
            return await func(*args, **kwargs)
            
        # 10-20% chance of timeout
        if random.random() < 0.15:
            timeout = random.uniform(1.0, 3.0)
            logger.warning(f"Simulating timeout in {func.__name__} for {timeout:.2f}s")
            await asyncio.sleep(timeout)
            raise asyncio.TimeoutError(f"Tool {func.__name__} timed out")

        # occassional malformed JSON simulation (by returning a bad dict structure that might fail validation)
        if random.random() < 0.05:
            logger.warning(f"Simulating malformed data in {func.__name__}")
            return {"error": "Internal Server Error", "code": 500, "data": "CORRUPT_DATA_BLOCK"}

        # Random delay for realism
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        return await func(*args, **kwargs)
    return wrapper

async def retry_with_backoff(func: Callable, max_retries: int = 3, base_delay: float = 0.5):
    """Retries a tool call with exponential backoff and detailed logging."""
    for attempt in range(1, max_retries + 1):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"FAILURE [FINAL]: {func.__name__ if hasattr(func, '__name__') else 'Tool'} failed after {max_retries} attempts. Error: {str(e)}")
                raise
            
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.2)
            logger.warning(f"RETRY [Attempt {attempt}]: {func.__name__ if hasattr(func, '__name__') else 'Tool'} failed. Retrying in {delay:.2f}s... Error: {str(e)}")
            await asyncio.sleep(delay)
