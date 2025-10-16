"""Script to add new documents to existing vector store with duplicate prevention and rate limiting."""

import hashlib
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.document_loader import load_and_chunk_documents
from rag.vector_store import get_vector_store


def add_chunk_metadata(chunks, source_file: str):
    """
    Add metadata to each chunk for duplicate prevention.

    Metadata includes:
    - source file name
    - page number
    - chunk_index
    - content hash (optional, for edits within a page)
    """
    new_chunks = []
    for page_num, chunk in enumerate(chunks):
        chunk_index = getattr(
            chunk, "chunk_index", 0
        )  # fallback if chunk_index not set
        content_hash = hashlib.md5(chunk.page_content.encode()).hexdigest()
        chunk.metadata.update(
            {
                "source": Path(source_file).name,
                "page": page_num + 1,
                "chunk_index": chunk_index,
                "chunk_id": content_hash,
            }
        )
        new_chunks.append(chunk)
    return new_chunks


def add_pdf_to_vectorstore_with_retry(
    pdf_path: str, batch_size: int = 5, delay: int = 2
):
    """
    Add a new PDF document to the existing vector store with duplicate prevention and rate limiting.

    Args:
        pdf_path: Path to the PDF file to add
        batch_size: Number of documents to add in each batch
        delay: Delay in seconds between batches
    """
    print("=" * 60)
    print("Adding New Document to Vector Store (with Duplicate Prevention)")
    print("=" * 60)

    # Check if file exists
    if not Path(pdf_path).exists():
        print(f"❌ Error: {pdf_path} not found!")
        return False

    print(f"\n1. Loading and chunking {pdf_path}...")
    print(f"   File size: {Path(pdf_path).stat().st_size / (1024 * 1024):.2f} MB")

    try:
        chunks = load_and_chunk_documents(
            file_path=pdf_path, chunk_size=1000, chunk_overlap=200
        )
        # Add metadata for duplicate detection
        chunks = add_chunk_metadata(chunks, pdf_path)
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
        print(
            "   Tip: Run 'python rag/init_vectorstore.py' first to create the initial vector store"
        )
        return False

    # Prevent duplicate embeddings
    print("\n3. Filtering out already embedded chunks...")
    try:
        existing_metadatas = vector_store.get(include=["metadatas"])["metadatas"]
        existing_ids = {m["chunk_id"] for m in existing_metadatas if "chunk_id" in m}
        new_chunks = [c for c in chunks if c.metadata["chunk_id"] not in existing_ids]
        print(f"   {len(new_chunks)}/{len(chunks)} chunks are new and will be added")
    except Exception as e:
        print(f"❌ Error filtering duplicates: {e}")
        return False

    if not new_chunks:
        print("   ✅ No new chunks to add. Exiting.")
        return True

    # Add new documents in batches with rate limiting
    print(
        f"\n4. Adding new chunks in batches of {batch_size} (delay: {delay}s between batches)..."
    )
    total_chunks = len(new_chunks)
    added_count = 0

    for i in range(0, total_chunks, batch_size):
        batch = new_chunks[i : i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_chunks + batch_size - 1) // batch_size

        try:
            print(
                f"   Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)...",
                end=" ",
            )
            vector_store.add_documents(batch)
            vector_store.persist()
            added_count += len(batch)
            print(f"✅ Added ({added_count}/{total_chunks})")

            # Wait between batches
            if i + batch_size < total_chunks:
                time.sleep(delay)

        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                print(f"\n⚠️  Rate limit reached after {added_count} documents")
                print("   Please wait a few minutes and run this command again:")
                print(f"   python rag/add_document_with_retry.py {pdf_path}")
                print(f"\n   Progress: {added_count}/{total_chunks} documents added")
                return False
            else:
                print(f"\n❌ Error: {e}")
                return False

    new_count = vector_store._collection.count()
    print(
        f"\n   ✅ Vector store now contains {new_count} documents (added {new_count - current_count})"
    )

    # Optional: Test retrieval from new document
    print("\n5. Testing retrieval from new document...")
    test_query = "company information"
    results = vector_store.similarity_search(test_query, k=3)

    print(f"\nTest Query: '{test_query}'")
    print(f"Retrieved {len(results)} relevant chunks:\n")

    for i, doc in enumerate(results[:2], 1):
        print(f"Chunk {i}:")
        print(f"{doc.page_content[:150]}...")
        source_file = doc.metadata.get("source", "N/A")
        print(
            f"Source: {Path(source_file).name} (Page {doc.metadata.get('page', 'N/A')})\n"
        )

    print("=" * 60)
    print("✅ Document added successfully!")
    print("=" * 60)

    return True


def main():
    """Main function to add document."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Add a PDF document to the vector store with duplicate prevention"
    )
    parser.add_argument(
        "pdf_path",
        nargs="?",
        default="ixora_general.pdf",
        help="Path to the PDF file (default: ixora_general.pdf)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=3,
        help="Number of documents per batch (default: 3)",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=5,
        help="Delay in seconds between batches (default: 5)",
    )

    args = parser.parse_args()

    success = add_pdf_to_vectorstore_with_retry(
        args.pdf_path, batch_size=args.batch_size, delay=args.delay
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
