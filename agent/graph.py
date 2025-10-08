"""LangGraph state machine for meeting booking agent."""

from typing import Literal
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from agent.nodes import (
    AgentState,
    extract_requirements_node,
    check_requirements_complete,
    ask_for_missing_info_node,
    fetch_slots_node,
    select_slot_node,
    process_slot_selection_node,
    collect_user_info_node,
    extract_user_info_node,
    confirm_booking_node,
    check_confirmation,
    book_meeting_node,
)
from agent.tools import get_all_tools


def create_agent_executor(llm):
    """Create the tool-calling agent executor."""
    tools = get_all_tools()

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful assistant for booking meetings with Ixora Solution's CEO.
        You have access to tools to:
        - Parse dates from natural language
        - Fetch available meeting slots
        - Validate user information
        - Book meetings
        - Analyze the booking page structure

        Use these tools to help users book meetings efficiently.
        Always be polite and professional."""),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        return_intermediate_steps=True,  # Needed to extract tool outputs
    )

    return agent_executor


def create_workflow(llm, agent_executor: AgentExecutor):
    """Create the complete booking workflow graph."""

    workflow = StateGraph(AgentState)

    # Add all nodes
    workflow.add_node("extract_requirements", lambda s: extract_requirements_node(s, llm))
    workflow.add_node("ask_missing_info", lambda s: ask_for_missing_info_node(s, llm))
    workflow.add_node("fetch_slots", lambda s: fetch_slots_node(s, agent_executor))
    workflow.add_node("select_slot", lambda s: select_slot_node(s, llm))
    workflow.add_node("collect_user_info", lambda s: collect_user_info_node(s, llm))
    workflow.add_node("extract_user_info", lambda s: extract_user_info_node(s, llm))
    workflow.add_node("confirm_booking", lambda s: confirm_booking_node(s, llm))
    workflow.add_node("book_meeting", lambda s: book_meeting_node(s, agent_executor))

    # Set entry point
    workflow.set_entry_point("extract_requirements")

    # Define the workflow edges
    workflow.add_conditional_edges(
        "extract_requirements",
        check_requirements_complete,
        {
            "complete": "fetch_slots",
            "incomplete": "ask_missing_info"
        }
    )

    # Ask for missing info ends the graph (waits for user input)
    workflow.add_edge("ask_missing_info", END)

    # Fetch slots -> Select slot
    workflow.add_edge("fetch_slots", "select_slot")

    # Select slot either waits for user selection or proceeds to collect info
    def check_slot_selection(state: AgentState) -> Literal["wait", "proceed"]:
        """Check if we need to wait for user to select a slot."""
        if state.get("next_action") == "wait_for_slot_selection":
            return "wait"
        return "proceed"

    workflow.add_conditional_edges(
        "select_slot",
        check_slot_selection,
        {
            "wait": END,  # Wait for user to select slot
            "proceed": "collect_user_info"
        }
    )

    # Collect user info either ends (to wait for input) or goes to confirmation
    def check_user_info_complete(state: AgentState) -> Literal["wait", "confirm"]:
        """Check if user info collection is complete."""
        if state.get("next_action") == "wait_for_user_info":
            return "wait"
        return "confirm"

    workflow.add_conditional_edges(
        "collect_user_info",
        check_user_info_complete,
        {
            "wait": END,
            "confirm": "confirm_booking"
        }
    )

    # Extract user info loops back to collect
    workflow.add_edge("extract_user_info", "collect_user_info")

    # Confirm booking ends (waits for confirmation)
    workflow.add_edge("confirm_booking", END)

    # Book meeting ends the workflow
    workflow.add_edge("book_meeting", END)

    return workflow.compile()


class BookingAgent:
    """Main booking agent class."""

    def __init__(self, llm):
        self.llm = llm
        self.agent_executor = create_agent_executor(llm)
        self.workflow = create_workflow(llm, self.agent_executor)
        self.state = None

    def initialize_state(self):
        """Initialize a new conversation state."""
        self.state = {
            "messages": [],
            "user_intent": "",
            "date_preference": "not_specified",
            "time_preference": "not_specified",
            "meeting_purpose": "not_specified",
            "user_name": "",
            "user_email": "",
            "user_phone": "",
            "available_slots": [],
            "selected_slot": {},
            "booking_confirmed": False,
            "next_action": ""
        }

    def process_message(self, user_message: str):
        """Process a user message through the workflow."""
        from langchain_core.messages import HumanMessage

        if self.state is None:
            self.initialize_state()

        # Add user message to state
        self.state["messages"].append(HumanMessage(content=user_message))

        # Determine which node to run based on state
        current_action = self.state.get("next_action", "")

        if current_action == "wait_for_user_input":
            # User provided missing info, re-extract requirements
            self.state = extract_requirements_node(self.state, self.llm)
            if check_requirements_complete(self.state) == "complete":
                self.state = fetch_slots_node(self.state, self.agent_executor)
                self.state = select_slot_node(self.state, self.llm)
                # Don't proceed further, wait for user to select a slot

        elif current_action == "wait_for_slot_selection":
            # User is selecting a time slot
            self.state = process_slot_selection_node(self.state, self.llm)
            # After selection, proceed to collect user info if slot selected
            if self.state.get("next_action") == "collect_user_info":
                self.state = collect_user_info_node(self.state, self.llm)

        elif current_action == "wait_for_user_info":
            # Check if user wants to start a new booking instead
            user_msg_lower = user_message.lower()
            booking_keywords = ["book", "schedule", "meeting", "appointment"]
            date_keywords = [
                "jan", "january", "feb", "february", "mar", "march",
                "apr", "april", "may", "jun", "june", "jul", "july",
                "aug", "august", "sep", "september", "oct", "october",
                "nov", "november", "dec", "december",
                "tomorrow", "today", "next week", "next monday", "next tuesday",
                "next wednesday", "next thursday", "next friday", "next saturday", "next sunday"
            ]

            if any(keyword in user_msg_lower for keyword in booking_keywords) and \
               any(date_word in user_msg_lower for date_word in date_keywords):
                # User wants to start a new booking, reset and restart
                self.initialize_state()
                self.state["messages"].append(HumanMessage(content=user_message))
                result = self.workflow.invoke(self.state)
                self.state = result
            else:
                # User provided contact info
                self.state = extract_user_info_node(self.state, self.llm)
                self.state = collect_user_info_node(self.state, self.llm)
                # If all info is now collected, proceed to confirmation
                if self.state.get("next_action") == "wait_for_confirmation":
                    self.state = confirm_booking_node(self.state, self.llm)

        elif current_action == "wait_for_confirmation":
            # User confirmed or declined
            if check_confirmation(self.state, self.llm) == "confirmed":
                self.state = book_meeting_node(self.state, self.agent_executor)
            else:
                from langchain_core.messages import AIMessage
                self.state["messages"].append(
                    AIMessage(content="Booking cancelled. Let me know if you'd like to book a different time.")
                )

        else:
            # Initial message or new conversation
            result = self.workflow.invoke(self.state)
            self.state = result

        # Return the last AI message
        for msg in reversed(self.state["messages"]):
            from langchain_core.messages import AIMessage
            if isinstance(msg, AIMessage):
                return msg.content

        return "I'm here to help you book a meeting. What date and time work for you?"

    def get_conversation_history(self):
        """Get the full conversation history."""
        return self.state["messages"] if self.state else []

    def reset(self):
        """Reset the agent state."""
        self.state = None
