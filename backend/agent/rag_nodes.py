"""RAG agent nodes for answering company information questions."""

import os
import sys
from pathlib import Path
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Add parent directory to path for RAG imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.rag_chain import query_rag


def rag_query_node(state: dict, llm) -> dict:
    """
    Answer user questions using RAG (company information).

    Args:
        state: Current agent state
        llm: Language model instance

    Returns:
        Updated state with RAG response
    """
    messages = state["messages"]

    # Get the last user message
    last_user_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_message = msg.content
            break

    if not last_user_message:
        state["messages"].append(
            AIMessage(content="How can I help you learn about Ixora Solution?")
        )
        state["next_action"] = ""
        return state

    # Check if RAG is disabled
    disable_rag = os.getenv("DISABLE_RAG", "false").lower() == "true"

    if disable_rag:
        # Use LLM to generate a contextual response without RAG
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("⚠️ RAG is disabled - using LLM to generate response without vector search")

        # Track LLM call
        from utils.llm_tracker import track_llm_call
        track_llm_call(
            call_type="chat",
            location="rag_nodes.py:rag_query_node",
            model=getattr(llm, 'model_name', 'unknown'),
            purpose="Generate response without RAG (quota exhausted)"
        )

        # Use LLM to generate contextual response based on the question
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant for Ixora Solution.

RAG (vector search) is currently unavailable, but you can still help with general information about the company.

**What you know about Ixora Solution:**
- Full-cycle offshore software development company based in Bangladesh
- Specializes in: custom software solutions, web and mobile development, and IT consulting services
- Provides services like: software development, mobile apps, web applications, IT consulting, cloud solutions
- Works with various technologies and frameworks
- Has experienced development teams

**Important:**
- Be helpful and answer based on the general information above
- If you need more specific details, suggest booking a meeting with the team
- Don't make up specific details you don't know
- Be conversational and natural

Answer the user's question based on this general knowledge."""),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("user", "{question}")
        ])

        # Prepare chat history
        chat_history = []
        for msg in messages[:-1]:
            if isinstance(msg, HumanMessage):
                chat_history.append(("user", msg.content))
            elif isinstance(msg, AIMessage):
                chat_history.append(("assistant", msg.content))

        chain = prompt | llm
        response = chain.invoke({
            "chat_history": chat_history,
            "question": last_user_message
        })

        state["messages"].append(AIMessage(content=response.content))
        state["next_action"] = "rag_complete"
        return state

    # Convert chat history to format expected by RAG
    chat_history = []
    for msg in messages[:-1]:  # Exclude the current message
        if isinstance(msg, HumanMessage):
            chat_history.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            chat_history.append({"role": "assistant", "content": msg.content})

    try:
        # Track RAG query (involves embedding + generation)
        import logging
        logger = logging.getLogger(__name__)
        logger.info("🤖 RAG QUERY: Embedding + Generation (2 API calls)")

        from utils.llm_tracker import track_llm_call
        track_llm_call(
            call_type="embedding",
            location="rag_nodes.py:rag_query_node",
            model="embedding-001",
            purpose="RAG: Embed user query for vector search"
        )
        track_llm_call(
            call_type="chat",
            location="rag_nodes.py:rag_query_node",
            model="gemini-flash",
            purpose="RAG: Generate answer from retrieved docs"
        )

        # Query the RAG system
        result = query_rag(
            question=last_user_message,
            chat_history=chat_history
        )

        answer = result["answer"]

        # Check if the answer mentions booking
        answer_lower = answer.lower()
        if any(keyword in answer_lower for keyword in ["book", "schedule", "meeting", "appointment"]):
            # Add a helpful prompt about booking
            answer += "\n\nWould you like me to help you book a meeting with our team?"

        # Add the RAG response to messages
        state["messages"].append(AIMessage(content=answer))

        # Store source documents for potential reference
        state["rag_sources"] = result.get("source_documents", [])

        # Check if user might want to book a meeting based on the question
        question_lower = last_user_message.lower()
        booking_intent_keywords = [
            "book", "schedule", "meeting", "appointment",
            "talk", "discuss", "consultation", "demo"
        ]

        if any(keyword in question_lower for keyword in booking_intent_keywords):
            state["next_action"] = "suggest_booking"
        else:
            state["next_action"] = "rag_complete"

    except Exception as e:
        # Handle errors gracefully - use LLM fallback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"RAG query error: {e}")

        # Check if it's a quota/rate limit error
        error_str = str(e).lower()
        is_quota_error = "quota" in error_str or "429" in error_str or "rate limit" in error_str

        if is_quota_error:
            logger.warning("⚠️ Quota error detected - using LLM fallback")

        # Use LLM to generate contextual response as fallback
        try:
            # Track LLM call
            from utils.llm_tracker import track_llm_call
            track_llm_call(
                call_type="chat",
                location="rag_nodes.py:rag_query_node (error handler)",
                model=getattr(llm, 'model_name', 'unknown'),
                purpose="Generate response after RAG error"
            )

            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a helpful AI assistant for Ixora Solution.

The vector search system encountered an error, but you can still help with general information.

**What you know about Ixora Solution:**
- Full-cycle offshore software development company based in Bangladesh
- Specializes in: custom software solutions, web and mobile development, and IT consulting services
- Provides services like: software development, mobile apps, web applications, IT consulting, cloud solutions

Answer the user's question based on this general knowledge. If you need more details, suggest booking a meeting."""),
                ("user", "{question}")
            ])

            chain = prompt | llm
            response = chain.invoke({"question": last_user_message})
            state["messages"].append(AIMessage(content=response.content))
        except Exception as llm_error:
            # If LLM also fails, use a simple fallback
            logger.error(f"LLM fallback also failed: {llm_error}")
            state["messages"].append(
                AIMessage(
                    content="I apologize, but I'm having trouble accessing information right now. "
                            "However, I can help you book a meeting with our team. Would you like to schedule a meeting?"
                )
            )

        state["next_action"] = "rag_complete"

    return state


def check_rag_complete(state: dict) -> Literal["continue", "complete"]:
    """Check if RAG interaction is complete or should suggest booking."""
    next_action = state.get("next_action", "")

    if next_action == "suggest_booking":
        return "suggest_booking"

    return "complete"
