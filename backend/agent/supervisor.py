"""Supervisor agent for routing between RAG and Booking agents."""

import json
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


def classify_intent_node(state: dict, llm) -> dict:
    """
    Classify user intent to route to appropriate agent.

    Routes to:
    - RAG: Questions about company services, capabilities, information
    - Booking: Requests to schedule meetings or appointments

    Args:
        state: Current agent state
        llm: Language model instance

    Returns:
        Updated state with agent_mode set
    """
    messages = state["messages"]

    # Get the last user message
    last_user_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_message = msg.content
            break

    if not last_user_message:
        # Default to RAG for initial greeting
        state["agent_mode"] = "rag"
        return state

    # Check current action - if already in booking flow, stay in booking
    current_action = state.get("next_action", "")
    booking_actions = [
        "wait_for_user_input",
        "wait_for_slot_selection",
        "wait_for_new_date",
        "wait_for_user_info",
        "wait_for_confirmation",
        "wait_for_new_booking"
    ]

    if current_action in booking_actions:
        state["agent_mode"] = "booking"
        return state

    # Check cache first to avoid redundant LLM calls
    from utils.cache import get_cache
    cache = get_cache()
    cache_key = f"intent_classification:{last_user_message.lower().strip()}"
    cached_intent = cache.get(cache_key)

    if cached_intent:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"✅ Using cached intent classification for: {last_user_message[:50]}")
        state["agent_mode"] = cached_intent
        state["intent_classification"] = {"intent": cached_intent, "cached": True}
        return state

    # Use LLM to classify the intent
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an intent classifier for Ixora Solution's AI assistant.

Classify the user's message into one of these categories:

1. **RAG** (Company Information):
   - Questions about services, solutions, technologies
   - Questions about company background, team, or capabilities
   - General inquiries about what Ixora does
   - Pricing, process, or methodology questions
   - Questions starting with: what, how, why, who, when (about the company)

2. **BOOKING** (Meeting Scheduling):
   - Explicit requests to book, schedule, or arrange a meeting
   - Mentions of specific dates, times for meetings
   - User wants to talk to someone, have a consultation
   - Follow-up responses during active booking process
   - Confirmations, selections, or providing contact information

Important rules:
- If user explicitly asks to book/schedule → BOOKING
- If user asks "can I book" or "how do I schedule" → BOOKING
- If user asks about services/capabilities → RAG
- If uncertain and it's a question → RAG
- If it's a greeting or acknowledgment and no booking is in progress → RAG

Return ONLY a JSON object with:
{{
  "intent": "rag" or "booking",
  "confidence": 0.0 to 1.0,
  "reason": "brief explanation"
}}"""),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("user", "Classify this message: {message}")
    ])

    # Prepare chat history (last 3 messages for context)
    chat_history = []
    if len(messages) > 1:
        for msg in messages[-4:-1]:  # Last 3 messages excluding current
            chat_history.append(msg)

    # Track LLM call
    from utils.llm_tracker import track_llm_call
    track_llm_call(
        call_type="chat",
        location="supervisor.py:classify_intent_node",
        model=getattr(llm, 'model_name', 'unknown'),
        purpose="Intent classification (RAG vs Booking)"
    )

    chain = prompt | llm
    response = chain.invoke({
        "chat_history": chat_history,
        "message": last_user_message
    })

    # Parse the classification
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        classification = json.loads(content)
        intent = classification.get("intent", "rag").lower()

        # Store classification metadata
        state["intent_classification"] = classification

        # Set agent mode
        if intent == "booking":
            state["agent_mode"] = "booking"
        else:
            state["agent_mode"] = "rag"

        # Cache the intent for 5 minutes (300 seconds)
        cache.set(cache_key, state["agent_mode"], ttl=300)

    except Exception as e:
        # Default to RAG on parsing error
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Intent classification error: {e}")
        logger.error(f"Response content: {response.content}")
        state["agent_mode"] = "rag"

    return state


def route_to_agent(state: dict) -> Literal["rag", "booking"]:
    """
    Route to the appropriate agent based on classified intent.

    Args:
        state: Current agent state

    Returns:
        Agent mode to route to
    """
    agent_mode = state.get("agent_mode", "rag")

    # Additional safety check for booking keywords
    last_user_message = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_user_message = msg.content.lower()
            break

    # Override to booking if explicit booking keywords found
    booking_keywords = [
        "book a meeting",
        "schedule a meeting",
        "arrange a meeting",
        "set up a meeting",
        "book meeting",
        "schedule meeting",
        "i want to book",
        "i'd like to book",
        "can i book",
        "help me book"
    ]

    if any(keyword in last_user_message for keyword in booking_keywords):
        return "booking"

    return agent_mode


def handle_agent_switch(state: dict, llm) -> dict:
    """
    Handle transitions when switching between agents.

    Args:
        state: Current agent state
        llm: Language model instance

    Returns:
        Updated state
    """
    # Get previous and current agent modes
    previous_mode = state.get("previous_agent_mode", "")
    current_mode = state.get("agent_mode", "rag")

    # If switching from RAG to booking, add a helpful transition message
    if previous_mode == "rag" and current_mode == "booking":
        # Check if we haven't already added a transition message
        last_ai_message = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage):
                last_ai_message = msg.content
                break

        transition_keywords = ["help you book", "schedule a meeting", "book a meeting"]
        if not any(keyword in last_ai_message.lower() for keyword in transition_keywords) if last_ai_message else True:
            state["messages"].append(
                AIMessage(content="Great! I'll help you book a meeting. What date works best for you?")
            )

    # Update previous mode
    state["previous_agent_mode"] = current_mode

    return state
