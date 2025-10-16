"""Script to add documents using local HuggingFace embeddings (no API required)."""

import hashlib
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from rag.document_loader import load_and_chunk_documents

load_dotenv()


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


def add_pdf_with_local_embeddings(pdf_path: str, model_name: str = "all-MiniLM-L6-v2"):
    """
    Add a new PDF using local HuggingFace embeddings (runs on your machine, no API).

    Args:
        pdf_path: Path to the PDF file to add
        model_name: HuggingFace model name (default: all-MiniLM-L6-v2 - fast and good)
    """
    print("=" * 60)
    print("Adding Document with Local Embeddings (No API Required)")
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
        chunks = add_chunk_metadata(chunks, pdf_path)
        print(f"   ✅ Created {len(chunks)} chunks from document")
    except Exception as e:
        print(f"❌ Error loading document: {e}")
        return False

    # Initialize local embeddings
    print(f"\n2. Initializing local embeddings (model: {model_name})...")
    print("   This will download the model on first use (~90MB)")

    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu"},  # Use 'cuda' if you have GPU
            encode_kwargs={"normalize_embeddings": True},
        )
        print("   ✅ Local embeddings ready (running on CPU)")
    except Exception as e:
        print(f"❌ Error loading embeddings model: {e}")
        print("\n   Installing sentence-transformers...")
        os.system("pip install -q sentence-transformers")
        try:
            embeddings = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            print("   ✅ Local embeddings ready")
        except Exception as e2:
            print(f"❌ Failed: {e2}")
            return False

    # Load or create vector store
    persist_directory = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")

    print(f"\n3. Loading vector store from {persist_directory}...")

    try:
        if os.path.exists(persist_directory):
            # Load existing store
            vector_store = Chroma(
                persist_directory=persist_directory, embedding_function=embeddings
            )
            current_count = vector_store._collection.count()
            print(f"   Current documents: {current_count}")

            # Prevent duplicate embeddings
            print("\n3. Filtering out already embedded chunks...")
            try:
                existing_metadatas = vector_store.get(include=["metadatas"])[
                    "metadatas"
                ]
                existing_ids = {
                    m["chunk_id"] for m in existing_metadatas if "chunk_id" in m
                }
                new_chunks = [
                    c for c in chunks if c.metadata["chunk_id"] not in existing_ids
                ]
                print(
                    f"   {len(new_chunks)}/{len(chunks)} chunks are new and will be added"
                )
            except Exception as e:
                print(f"❌ Error filtering duplicates: {e}")
                return False

            if not new_chunks:
                print("   ✅ No new chunks to add. Exiting.")
                return True

            # Add new documents
            print(
                f"\n4. Adding {len(chunks)} new chunks (this may take a few minutes)..."
            )
            total = len(chunks)
            for i in range(0, total, 5):
                batch = chunks[i : i + 5]
                vector_store.add_documents(batch)
                progress = min(i + 5, total)
                print(
                    f"   Progress: {progress}/{total} chunks added ({progress * 100 // total}%)"
                )

            new_count = vector_store._collection.count()
            print(
                f"   ✅ Total documents now: {new_count} (added {new_count - current_count})"
            )

        else:
            # Create new vector store
            print("   Creating new vector store...")
            print(
                f"   Processing {len(chunks)} chunks (this may take a few minutes)..."
            )

            vector_store = Chroma.from_documents(
                documents=chunks,
                embedding=embeddings,
                persist_directory=persist_directory,
            )
            print(f"   ✅ Created with {len(chunks)} documents")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
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
        source_file = doc.metadata.get("source", "N/A")
        print(f"Source: {Path(source_file).name}\n")

    print("=" * 60)
    print("✅ Document added successfully with LOCAL embeddings!")

    return True


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Add PDF using local embeddings")
    parser.add_argument(
        "pdf_path",
        nargs="?",
        default="ixora_general.pdf",
        help="Path to PDF file (default: ixora_general.pdf)",
    )
    parser.add_argument(
        "--model",
        default="all-MiniLM-L6-v2",
        help="HuggingFace model (default: all-MiniLM-L6-v2)",
    )

    args = parser.parse_args()

    print("\n💡 Using local embeddings - no API required!")
    print(f"   Model: {args.model}")
    print()

    success = add_pdf_with_local_embeddings(args.pdf_path, args.model)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
