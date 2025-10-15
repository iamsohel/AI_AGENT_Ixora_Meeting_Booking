"""Agent executor for tool-calling (date parsing)."""

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from agent.tools import get_all_tools


def create_agent_executor(llm):
    """
    Create the tool-calling agent executor.

    Used by booking nodes to parse dates using LangChain tools.
    """
    tools = get_all_tools()

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful assistant for booking meetings.
        You have access to tools to:
        - Parse dates from natural language
        - Fetch available meeting slots
        - Validate user information
        - Book meetings

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
        verbose=False,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
    )

    return agent_executor
