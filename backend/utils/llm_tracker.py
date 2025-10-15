"""Track LLM API calls for monitoring and debugging."""

import logging
import os
import time
from typing import Optional
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# Context variable to track calls per request
_llm_call_count = ContextVar('llm_call_count', default=0)
_llm_call_details = ContextVar('llm_call_details', default=[])
_request_start_time = ContextVar('request_start_time', default=None)

# Global variable for rate limiting (shared across all requests)
_last_llm_call_time = None
_rate_limit_lock = None  # Will be initialized when needed


def reset_llm_tracker():
    """Reset the LLM call tracker for a new request."""
    _llm_call_count.set(0)
    _llm_call_details.set([])
    _request_start_time.set(time.time())


def enforce_rate_limit():
    """
    Enforce rate limiting between LLM API calls.

    Reads MIN_DELAY_BETWEEN_CALLS from environment (default: 0.2 seconds).
    This prevents hitting rate limits by spacing out API calls.
    """
    global _last_llm_call_time

    # Get minimum delay from environment (default 0.2 seconds = 200ms)
    min_delay = float(os.getenv("MIN_DELAY_BETWEEN_CALLS", "0.2"))

    if min_delay <= 0:
        return  # Rate limiting disabled

    if _last_llm_call_time is not None:
        elapsed = time.time() - _last_llm_call_time
        if elapsed < min_delay:
            sleep_time = min_delay - elapsed
            logger.debug(f"⏱️ Rate limiting: sleeping {sleep_time:.2f}s before next API call")
            time.sleep(sleep_time)

    _last_llm_call_time = time.time()


def track_llm_call(
    call_type: str,
    location: str,
    model: Optional[str] = None,
    purpose: Optional[str] = None
):
    """
    Track an LLM API call and enforce rate limiting.

    Args:
        call_type: Type of call (e.g., "chat", "embedding")
        location: Where the call is made (file:function)
        model: Model name
        purpose: What the call is for
    """
    # Enforce rate limiting before the call
    enforce_rate_limit()

    count = _llm_call_count.get()
    count += 1
    _llm_call_count.set(count)

    details = _llm_call_details.get()
    call_info = {
        "call_number": count,
        "type": call_type,
        "location": location,
        "model": model,
        "purpose": purpose,
        "timestamp": time.time()
    }
    details.append(call_info)
    _llm_call_details.set(details)

    logger.info(f"🤖 LLM CALL #{count}: {purpose or call_type} [{location}] (model: {model or 'unknown'})")


def get_llm_call_count() -> int:
    """Get the current LLM call count for this request."""
    return _llm_call_count.get()


def get_llm_call_summary() -> dict:
    """
    Get a summary of all LLM calls made in this request.

    Returns:
        Dict with total count, details, and timing
    """
    count = _llm_call_count.get()
    details = _llm_call_details.get()
    start_time = _request_start_time.get()

    elapsed = None
    if start_time:
        elapsed = time.time() - start_time

    summary = {
        "total_calls": count,
        "elapsed_seconds": elapsed,
        "calls": details
    }

    # Log summary
    if count > 0:
        logger.warning(f"📊 LLM CALL SUMMARY: {count} total calls in {elapsed:.2f}s" if elapsed else f"📊 LLM CALL SUMMARY: {count} total calls")
        for call in details:
            logger.info(f"   {call['call_number']}. {call['purpose']} [{call['location']}]")

    return summary


def log_rate_limit_info():
    """Log information when hitting rate limits."""
    count = _llm_call_count.get()
    details = _llm_call_details.get()

    logger.error(f"⚠️ RATE LIMIT HIT after {count} LLM calls")
    logger.error("Recent LLM calls:")
    for call in details[-5:]:  # Last 5 calls
        logger.error(f"   - {call['purpose']} at {call['location']}")

    # Suggest solutions
    logger.error("\n💡 To reduce LLM calls:")
    logger.error("   1. Use caching for repeated queries")
    logger.error("   2. Batch similar operations")
    logger.error("   3. Use simpler models for basic tasks")
    logger.error("   4. Increase rate limit quota")
