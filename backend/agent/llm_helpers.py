"""LLM helper functions for flexible intent understanding."""

import json
import logging
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)


def check_user_confirmation(
    user_message: str,
    context: str,
    llm
) -> Literal["confirmed", "cancelled", "unclear"]:
    """
    Use LLM to understand if user is confirming, canceling, or being unclear.

    This replaces hardcoded yes/no lists with flexible natural language understanding.

    Args:
        user_message: What the user said
        context: What we asked them (for context)
        llm: Language model instance

    Returns:
        "confirmed" - User is confirming/agreeing
        "cancelled" - User is declining/canceling
        "unclear" - Ambiguous or needs clarification

    Examples:
        >>> check_user_confirmation("yes", "Do you want to book?", llm)
        "confirmed"
        >>> check_user_confirmation("absolutely!", "Is this correct?", llm)
        "confirmed"
        >>> check_user_confirmation("nah", "Confirm booking?", llm)
        "cancelled"
        >>> check_user_confirmation("maybe later", "Want to proceed?", llm)
        "cancelled"
    """
    # Check cache first for common confirmation patterns
    from utils.cache import get_cache
    cache = get_cache()
    cache_key = f"confirmation:{user_message.lower().strip()}"
    cached_result = cache.get(cache_key)

    if cached_result:
        logger.info(f"✅ Using cached confirmation result for: {user_message[:50]}")
        return cached_result

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are analyzing user responses to determine their intent.

Context: We asked the user: "{context}"
User responded: "{user_message}"

Analyze the user's response and determine their intent:
- **confirmed**: User is agreeing, confirming, or saying yes (in any form)
  Examples: yes, yeah, yup, sure, ok, absolutely, definitely, sounds good, let's do it, go ahead, confirm, correct, that's right, alright

- **cancelled**: User is declining, canceling, or saying no (in any form)
  Examples: no, nope, nah, cancel, quit, exit, stop, not now, maybe later, i changed my mind, don't want to

- **unclear**: User's intent is ambiguous or they're asking a question
  Examples: what?, I'm not sure, can I change it?, let me think, maybe, possibly

Return ONLY a JSON object:
{{{{
  "intent": "confirmed" or "cancelled" or "unclear",
  "confidence": 0.0 to 1.0,
  "reason": "brief explanation"
}}}}"""),
        ("user", "Context: {context}\nUser said: {user_message}")
    ])

    try:
        # Track LLM call
        from utils.llm_tracker import track_llm_call
        track_llm_call(
            call_type="chat",
            location="llm_helpers.py:check_user_confirmation",
            model=getattr(llm, 'model_name', 'unknown'),
            purpose="User confirmation check (yes/no/unclear)"
        )

        chain = prompt | llm
        response = chain.invoke({
            "context": context,
            "user_message": user_message
        })

        # Parse JSON response
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)
        intent = result.get("intent", "unclear").lower()
        confidence = result.get("confidence", 0.0)

        logger.info(f"Confirmation check: '{user_message}' → {intent} (confidence: {confidence})")

        # Cache the result for 10 minutes (common patterns like "yes", "no")
        final_intent = intent if intent in ["confirmed", "cancelled", "unclear"] else "unclear"
        cache.set(cache_key, final_intent, ttl=600)

        return final_intent

    except Exception as e:
        logger.error(f"Error in confirmation check: {e}")
        logger.error(f"Response content: {response.content if 'response' in locals() else 'N/A'}")
        # Default to unclear if parsing fails
        return "unclear"


def check_new_booking_intent(
    user_message: str,
    llm
) -> Literal["yes", "no", "new_request"]:
    """
    Check if user wants to make a new booking after cancellation.

    Args:
        user_message: User's response
        llm: Language model instance

    Returns:
        "yes" - Wants to book for different date
        "no" - Doesn't want to book
        "new_request" - Has a specific new booking request
    """
    # Check cache first
    from utils.cache import get_cache
    cache = get_cache()
    cache_key = f"new_booking:{user_message.lower().strip()}"
    cached_result = cache.get(cache_key)

    if cached_result:
        logger.info(f"✅ Using cached new booking intent for: {user_message[:50]}")
        return cached_result

    prompt = ChatPromptTemplate.from_messages([
        ("system", """We asked: "Would you like to book a meeting for a different date?"
User responded: "{user_message}"

Analyze their response:
- **yes**: User wants to try booking again
  Examples: yes, sure, yeah, let's try again, I'd like to

- **no**: User doesn't want to book
  Examples: no, nope, not now, cancel, maybe later

- **new_request**: User is making a specific new booking request
  Examples: "book for next Monday", "how about tomorrow at 3pm", "I want to meet on Friday"

Return ONLY JSON:
{{{{
  "intent": "yes" or "no" or "new_request",
  "confidence": 0.0 to 1.0
}}}}"""),
        ("user", "{user_message}")
    ])

    try:
        # Track LLM call
        from utils.llm_tracker import track_llm_call
        track_llm_call(
            call_type="chat",
            location="llm_helpers.py:check_new_booking_intent",
            model=getattr(llm, 'model_name', 'unknown'),
            purpose="New booking intent check"
        )

        chain = prompt | llm
        response = chain.invoke({"user_message": user_message})

        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)
        intent = result.get("intent", "no").lower()

        # Cache the result for 10 minutes
        final_intent = intent if intent in ["yes", "no", "new_request"] else "no"
        cache.set(cache_key, final_intent, ttl=600)

        return final_intent

    except Exception as e:
        logger.error(f"Error in new booking check: {e}")
        return "no"


def check_user_intent_in_context(
    user_message: str,
    context: str,
    llm
) -> Literal["providing_info", "new_booking"]:
    """
    Check if user is providing requested information or trying to start a new booking.

    Args:
        user_message: User's response
        context: What we asked them for
        llm: Language model instance

    Returns:
        "providing_info" - User is answering the question
        "new_booking" - User wants to start a new booking
    """
    # Check cache first
    from utils.cache import get_cache
    cache = get_cache()
    cache_key = f"intent_context:{user_message.lower().strip()}"
    cached_result = cache.get(cache_key)

    if cached_result:
        logger.info(f"✅ Using cached intent result for: {user_message[:50]}")
        return cached_result

    prompt = ChatPromptTemplate.from_messages([
        ("system", """Analyze the user's response in context.

Context: {context}
User responded: "{user_message}"

Determine if the user is:
- **providing_info**: Answering the question we asked (providing contact info, details, etc.)
- **new_booking**: Trying to start a new booking request (mentioning dates, times, wanting to book)

Return ONLY JSON:
{{{{
  "intent": "providing_info" or "new_booking",
  "confidence": 0.0 to 1.0
}}}}"""),
        ("user", "{user_message}")
    ])

    try:
        # Track LLM call
        from utils.llm_tracker import track_llm_call
        track_llm_call(
            call_type="chat",
            location="llm_helpers.py:check_user_intent_in_context",
            model=getattr(llm, 'model_name', 'unknown'),
            purpose="Check if user providing info or starting new booking"
        )

        chain = prompt | llm
        response = chain.invoke({
            "context": context,
            "user_message": user_message
        })

        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)
        intent = result.get("intent", "providing_info").lower()

        # Cache the result for 5 minutes
        final_intent = intent if intent in ["providing_info", "new_booking"] else "providing_info"
        cache.set(cache_key, final_intent, ttl=300)

        return final_intent

    except Exception as e:
        logger.error(f"Error in intent context check: {e}")
        return "providing_info"  # Default to assuming they're providing info


def check_cancellation_intent(
    user_message: str,
    current_action: str,
    llm
) -> bool:
    """
    Use LLM to detect if user wants to cancel the booking process.

    This replaces hardcoded keyword matching with intelligent understanding.

    Args:
        user_message: What the user said
        current_action: Current booking workflow state
        llm: Language model instance

    Returns:
        True if user wants to cancel/exit booking
        False if user wants to continue with booking

    Examples:
        >>> check_cancellation_intent("no, let's talk about your services", "wait_for_user_input", llm)
        True
        >>> check_cancellation_intent("cancel", "wait_for_slot_selection", llm)
        True
        >>> check_cancellation_intent("next Tuesday", "wait_for_user_input", llm)
        False
        >>> check_cancellation_intent("tell me about your company", "wait_for_new_date", llm)
        True
    """
    # Check cache first
    from utils.cache import get_cache
    cache = get_cache()
    cache_key = f"cancellation:{user_message.lower().strip()}"
    cached_result = cache.get(cache_key)

    if cached_result is not None:
        logger.info(f"✅ Using cached cancellation result for: {user_message[:50]}")
        return cached_result

    # Map action to context for better LLM understanding
    action_context = {
        "wait_for_user_input": "asking for a date/time preference",
        "wait_for_slot_selection": "asking user to select a time slot",
        "wait_for_new_date": "asking if user wants to try a different date",
        "wait_for_user_info": "collecting user's contact information",
        "wait_for_new_booking": "asking if user wants to book a meeting"
    }

    context = action_context.get(current_action, "in the booking process")

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are analyzing if a user wants to cancel/exit a booking process.

Context: We are currently {context}
User responded: "{user_message}"

Determine if the user wants to:
- **cancel**: Exit the booking process and do something else
  Examples:
  - "no, let's talk about your services"
  - "cancel"
  - "stop"
  - "nevermind"
  - "tell me about your company"
  - "what do you offer"
  - "I want to know more about you first"
  - "not interested"
  - "let me think about it"

- **continue**: Continue with the booking process
  Examples:
  - "next Tuesday"
  - "tomorrow at 3pm"
  - "slot 2"
  - "my email is john@example.com"
  - "can you show me more times?"
  - "what about Wednesday?"

Return ONLY JSON:
{{{{
  "wants_to_cancel": true or false,
  "confidence": 0.0 to 1.0,
  "reason": "brief explanation"
}}}}"""),
        ("user", "Context: {context}\nUser said: {user_message}")
    ])

    try:
        # Track LLM call
        from utils.llm_tracker import track_llm_call
        track_llm_call(
            call_type="chat",
            location="llm_helpers.py:check_cancellation_intent",
            model=getattr(llm, 'model_name', 'unknown'),
            purpose="Booking cancellation detection"
        )

        chain = prompt | llm
        response = chain.invoke({
            "context": context,
            "user_message": user_message
        })

        # Parse JSON response
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)
        wants_to_cancel = result.get("wants_to_cancel", False)
        confidence = result.get("confidence", 0.0)
        reason = result.get("reason", "")

        logger.info(
            f"Cancellation check: '{user_message}' → {wants_to_cancel} "
            f"(confidence: {confidence}, reason: {reason})"
        )

        # Cache the result for 10 minutes
        cache.set(cache_key, wants_to_cancel, ttl=600)

        return wants_to_cancel

    except Exception as e:
        logger.error(f"Error in cancellation check: {e}")
        logger.error(f"Response content: {response.content if 'response' in locals() else 'N/A'}")
        # Default to not canceling if there's an error (safer to continue)
        return False
