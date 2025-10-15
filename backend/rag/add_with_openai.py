"""Script to add documents using OpenAI embeddings (alternative to Gemini)."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from rag.document_loader import load_and_chunk_documents

load_dotenv()


def add_pdf_with_openai(pdf_path: str):
    """
    Add a new PDF using OpenAI embeddings instead of Gemini.

    Args:
        pdf_path: Path to the PDF file to add
    """
    print("=" * 60)
    print("Adding Document with OpenAI Embeddings")
    print("=" * 60)

    # Check OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in .env file")
        print("\nTo use OpenAI embeddings:")
        print("1. Get API key from: https://platform.openai.com/api-keys")
        print("2. Add to .env file: OPENAI_API_KEY=sk-...")
        return False

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

    # Initialize OpenAI embeddings
    print("\n2. Initializing OpenAI embeddings...")
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",  # Cheaper and faster
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    print("   ✅ OpenAI embeddings ready")

    # Load or create vector store
    persist_directory = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")

    print(f"\n3. Loading vector store from {persist_directory}...")

    try:
        if os.path.exists(persist_directory):
            vector_store = Chroma(
                persist_directory=persist_directory,
                embedding_function=embeddings
            )
            current_count = vector_store._collection.count()
            print(f"   Current documents: {current_count}")

            # Add new documents
            print(f"\n4. Adding {len(chunks)} new chunks...")
            vector_store.add_documents(chunks)
            new_count = vector_store._collection.count()
            print(f"   ✅ Total documents now: {new_count} (added {new_count - current_count})")

        else:
            # Create new vector store
            print("   Creating new vector store...")
            vector_store = Chroma.from_documents(
                documents=chunks,
                embedding=embeddings,
                persist_directory=persist_directory
            )
            print(f"   ✅ Created with {len(chunks)} documents")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    # Test retrieval
    print("\n5. Testing retrieval...")
    test_query = "company information"
    results = vector_store.similarity_search(test_query, k=2)

    print(f"\nTest Query: '{test_query}'")
    print(f"Retrieved {len(results)} chunks:\n")

    for i, doc in enumerate(results, 1):
        print(f"Chunk {i}:")
        print(f"{doc.page_content[:150]}...")
        source_file = doc.metadata.get('source', 'N/A')
        print(f"Source: {Path(source_file).name}\n")

    print("=" * 60)
    print("✅ Document added successfully with OpenAI embeddings!")
    print("=" * 60)
    print("\n⚠️  Note: Your vector store now uses OpenAI embeddings.")
    print("Update .env to use OpenAI for all operations:")
    print("EMBEDDING_PROVIDER=openai")

    return True


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description='Add PDF using OpenAI embeddings')
    parser.add_argument('pdf_path', nargs='?', default='ixora_general.pdf',
                        help='Path to PDF file (default: ixora_general.pdf)')

    args = parser.parse_args()

    success = add_pdf_with_openai(args.pdf_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
