"""Document loading and processing utilities for RAG."""

import os
from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document


def load_documents(file_path: str | None = None, directory_path: str | None = None) -> List[Document]:
    """
    Load documents from a file or directory.

    Args:
        file_path: Path to a single PDF file
        directory_path: Path to a directory containing PDF files

    Returns:
        List of Document objects
    """
    documents = []

    if file_path:
        # Load single PDF
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        print(f"Loaded {len(documents)} pages from {file_path}")

    elif directory_path:
        # Load all PDFs from directory
        loader = DirectoryLoader(
            directory_path,
            glob="**/*.pdf",
            loader_cls=PyPDFLoader,
            show_progress=True
        )
        documents = loader.load()
        print(f"Loaded {len(documents)} pages from {directory_path}")

    else:
        raise ValueError("Either file_path or directory_path must be provided")

    return documents


def chunk_documents(
    documents: List[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[Document]:
    """
    Split documents into smaller chunks for better retrieval.

    Args:
        documents: List of Document objects to chunk
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of characters to overlap between chunks

    Returns:
        List of chunked Document objects
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )

    chunks = text_splitter.split_documents(documents)
    print(f"Split {len(documents)} documents into {len(chunks)} chunks")

    return chunks


def load_and_chunk_documents(
    file_path: str | None = None,
    directory_path: str | None = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[Document]:
    """
    Convenience function to load and chunk documents in one step.

    Args:
        file_path: Path to a single PDF file
        directory_path: Path to a directory containing PDF files
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of characters to overlap between chunks

    Returns:
        List of chunked Document objects
    """
    documents = load_documents(file_path, directory_path)
    chunks = chunk_documents(documents, chunk_size, chunk_overlap)
    return chunks
