"""Script to add new documents to existing vector store."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.document_loader import load_and_chunk_documents
from rag.vector_store import get_vector_store, add_documents_to_store


def add_pdf_to_vectorstore(pdf_path: str):
    """
    Add a new PDF document to the existing vector store.

    Args:
        pdf_path: Path to the PDF file to add
    """
    print("=" * 60)
    print("Adding New Document to Vector Store")
    print("=" * 60)

    # Check if file exists
    if not Path(pdf_path).exists():
        print(f"❌ Error: {pdf_path} not found!")
        return False

    print(f"\n1. Loading and chunking {pdf_path}...")
    print(f"   File size: {Path(pdf_path).stat().st_size / (1024*1024):.2f} MB")

    try:
        chunks = load_and_chunk_documents(
            file_path=pdf_path,
            chunk_size=1000,
            chunk_overlap=200
        )
        print(f"   ✅ Created {len(chunks)} chunks from document")
    except Exception as e:
        print(f"❌ Error loading document: {e}")
        return False

    # Get existing vector store
    print("\n2. Loading existing vector store...")
    try:
        vector_store = get_vector_store()
        current_count = vector_store._collection.count()
        print(f"   Current documents in vector store: {current_count}")
    except Exception as e:
        print(f"❌ Error loading vector store: {e}")
        print("   Tip: Run 'python rag/init_vectorstore.py' first to create the initial vector store")
        return False

    # Add new documents
    print("\n3. Adding new documents to vector store...")
    try:
        add_documents_to_store(chunks)
        new_count = vector_store._collection.count()
        print(f"   ✅ Vector store now contains {new_count} documents (added {new_count - current_count})")
    except Exception as e:
        print(f"❌ Error adding documents: {e}")
        return False

    # Test retrieval from new document
    print("\n4. Testing retrieval from new document...")
    test_query = "company information"  # Generic query to test
    results = vector_store.similarity_search(test_query, k=3)

    print(f"\nTest Query: '{test_query}'")
    print(f"Retrieved {len(results)} relevant chunks:\n")

    for i, doc in enumerate(results[:2], 1):
        print(f"Chunk {i}:")
        print(f"{doc.page_content[:150]}...")
        source_file = doc.metadata.get('source', 'N/A')
        print(f"Source: {Path(source_file).name} (Page {doc.metadata.get('page', 'N/A')})\n")

    print("=" * 60)
    print("✅ Document added successfully!")
    print("=" * 60)

    return True


def main():
    """Main function to add document."""
    import argparse

    parser = argparse.ArgumentParser(description='Add a PDF document to the vector store')
    parser.add_argument('pdf_path', nargs='?', default='ixora_general.pdf',
                        help='Path to the PDF file (default: ixora_general.pdf)')

    args = parser.parse_args()

    success = add_pdf_to_vectorstore(args.pdf_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
