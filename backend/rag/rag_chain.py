"""RAG chain implementation for question answering."""

import os
from typing import Dict, List

from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI

from .vector_store import get_retriever


def get_llm():
    """Get the Gemini LLM model."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        temperature=0.7,
        max_tokens=2048,
    )


def create_rag_chain():
    """
    Create a RAG chain for answering questions about Ixora Solution.

    Returns:
        Retrieval chain for question answering
    """
    llm = get_llm()
    retriever = get_retriever(k=4)

    # Create the system prompt
    system_prompt = """You are a helpful AI assistant for Ixora Solution, a full-cycle offshore software development company based in Bangladesh.

        Use the following context from the company's documentation to answer questions about Ixora Solution's services, solutions, and capabilities.

        Context:
        {context}

        Instructions:
        - Provide accurate, professional, and friendly responses about Ixora Solution
        - If the answer is found in the context, use it to provide a detailed response
        - If the question is about booking a meeting or scheduling an appointment, politely let the user know you can help them book a meeting with Ixora's team
        - If you don't find relevant information in the context, politely say you don't have that specific information
        - Always maintain a professional tone that reflects Ixora's commitment to quality and customer service
        - Be concise but informative

        Remember: You represent Ixora Solution, so always be helpful and showcase the company's expertise."""

    # Create the prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
        ]
    )

    # Create the document chain
    question_answer_chain = create_stuff_documents_chain(llm, prompt)

    # Create the retrieval chain
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    return rag_chain


def query_rag(question: str, chat_history: List[Dict] | None = None) -> Dict:
    """
    Query the RAG system with a question.

    Args:
        question: User's question
        chat_history: Optional list of previous messages

    Returns:
        Dictionary with 'answer', 'context', and 'source_documents'
    """
    chain = create_rag_chain()

    # Convert chat history to LangChain format if provided
    formatted_history = []
    if chat_history:
        for msg in chat_history:
            if msg.get("role") == "user":
                formatted_history.append(HumanMessage(content=msg["content"]))
            elif msg.get("role") == "assistant":
                formatted_history.append(AIMessage(content=msg["content"]))

    # Run the chain
    result = chain.invoke({"input": question, "chat_history": formatted_history})

    return {
        "answer": result["answer"],
        "context": result.get("context", []),
        "source_documents": [
            {"content": doc.page_content, "metadata": doc.metadata}
            for doc in result.get("context", [])
        ],
    }
