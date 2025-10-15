"""Script to initialize the vector store with company documents."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.document_loader import load_and_chunk_documents
from rag.vector_store import initialize_vector_store


def main():
    """Initialize the vector store with ixora.pdf."""
    print("=" * 60)
    print("Initializing Ixora Solution Vector Store")
    print("=" * 60)

    # Load and chunk the ixora.pdf document
    pdf_path = "ixora.pdf"

    if not Path(pdf_path).exists():
        print(f"Error: {pdf_path} not found!")
        return

    print(f"\n1. Loading and chunking {pdf_path}...")
    chunks = load_and_chunk_documents(
        file_path=pdf_path,
        chunk_size=1000,
        chunk_overlap=200
    )

    # Initialize vector store
    print("\n2. Creating vector store with embeddings...")
    vector_store = initialize_vector_store(
        documents=chunks,
        force_recreate=True
    )

    print("\n3. Vector store initialized successfully!")
    print(f"   - Total chunks: {len(chunks)}")
    print(f"   - Persist directory: {vector_store._persist_directory}")

    # Test retrieval
    print("\n4. Testing retrieval...")
    test_query = "What services does Ixora Solution provide?"
    results = vector_store.similarity_search(test_query, k=2)

    print(f"\nTest Query: '{test_query}'")
    print(f"Retrieved {len(results)} relevant chunks:\n")

    for i, doc in enumerate(results, 1):
        print(f"Chunk {i}:")
        print(f"{doc.page_content[:200]}...")
        print(f"Source: Page {doc.metadata.get('page', 'N/A')}\n")

    print("=" * 60)
    print("Initialization complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
