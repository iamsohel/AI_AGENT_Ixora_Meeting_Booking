"""Vector store management using Chroma DB with configurable embeddings."""

import os
from typing import List

from langchain.schema import Document
from langchain_chroma import Chroma

from dotenv import load_dotenv

load_dotenv()

# Global vector store instance
_vector_store = None


def get_embeddings():
    """
    Get embeddings model based on EMBEDDING_PROVIDER setting.

    Supports:
    - local: HuggingFace sentence-transformers (default, no API required)
    - gemini: Google Gemini embeddings
    - openai: OpenAI embeddings

    Returns:
        Embeddings instance
    """
    provider = os.getenv("EMBEDDING_PROVIDER", "local").lower()

    if provider == "local":
        from langchain_huggingface import HuggingFaceEmbeddings
        model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )

    elif provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        embedding_model = os.getenv("EMBEDDING_MODEL", "models/embedding-001")
        return GoogleGenerativeAIEmbeddings(model=embedding_model)

    elif provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        return OpenAIEmbeddings(model=model_name)

    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")


def initialize_vector_store(
    documents: List[Document] | None = None,
    persist_directory: str | None = None,
    force_recreate: bool = False
) -> Chroma:
    """
    Initialize or load the Chroma vector store.

    Args:
        documents: Documents to add to the vector store (for initial creation)
        persist_directory: Directory to persist the vector store
        force_recreate: If True, recreate the vector store even if it exists

    Returns:
        Chroma vector store instance
    """
    global _vector_store

    if persist_directory is None:
        persist_directory = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")

    embeddings = get_embeddings()

    # Check if vector store already exists
    if os.path.exists(persist_directory) and not force_recreate:
        print(f"Loading existing vector store from {persist_directory}")
        _vector_store = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings
        )
        print(f"✅ Vector store loaded with {_vector_store._collection.count()} documents")

        # Add new documents if provided
        if documents:
            print(f"Adding {len(documents)} new documents to existing vector store")
            _vector_store.add_documents(documents)

    else:
        # Create new vector store
        if documents is None or len(documents) == 0:
            raise ValueError("Documents must be provided to create a new vector store")

        print(f"Creating new vector store at {persist_directory}")
        _vector_store = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=persist_directory
        )
        print(f"✅ Vector store created with {len(documents)} documents")

    return _vector_store


def get_vector_store() -> Chroma:
    """
    Get the current vector store instance.

    Returns:
        Chroma vector store instance

    Raises:
        RuntimeError: If vector store is not initialized
    """
    global _vector_store

    if _vector_store is None:
        # Try to load from default directory
        persist_directory = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
        if os.path.exists(persist_directory):
            _vector_store = initialize_vector_store(persist_directory=persist_directory)
        else:
            raise RuntimeError(
                "Vector store not initialized. Call initialize_vector_store() first."
            )

    return _vector_store


def get_retriever(k: int = 4, search_type: str = "similarity"):
    """
    Get a retriever from the vector store.

    Args:
        k: Number of documents to retrieve
        search_type: Type of search ("similarity" or "mmr")

    Returns:
        VectorStoreRetriever instance
    """
    vector_store = get_vector_store()

    return vector_store.as_retriever(
        search_type=search_type,
        search_kwargs={"k": k}
    )


def add_documents_to_store(documents: List[Document]):
    """
    Add documents to the existing vector store.

    Args:
        documents: List of documents to add
    """
    vector_store = get_vector_store()
    vector_store.add_documents(documents)
    print(f"✅ Added {len(documents)} documents to vector store")


def search_documents(query: str, k: int = 4) -> List[Document]:
    """
    Search for documents similar to the query.

    Args:
        query: Search query
        k: Number of documents to return

    Returns:
        List of relevant documents
    """
    vector_store = get_vector_store()
    return vector_store.similarity_search(query, k=k)


def query_similar_documents(vector_store: Chroma, query: str, k: int = 3) -> List[Document]:
    """
    Query the vector store for similar documents.

    Args:
        vector_store: Chroma vector store instance
        query: Query string
        k: Number of results to return

    Returns:
        List of similar documents
    """
    return vector_store.similarity_search(query, k=k)
