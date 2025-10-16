"""Script to add new documents to existing vector store with rate limiting."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.vector_store import get_vector_store


def check_current_doc():
    try:
        vector_store = get_vector_store()
        current_count = vector_store._collection.count()
        print(f"   Current documents in vector store: {current_count}")
        existing_metadatas = vector_store.get(include=["metadatas"])["metadatas"]
        print(existing_metadatas)
    except Exception as e:
        print(f"❌ Error loading vector store: {e}")
        print(
            "   Tip: Run 'python rag/init_vectorstore.py' first to create the initial vector store"
        )
        return False

    # test_query = "who are golam zilani"
    # results = vector_store.similarity_search(test_query, k=3)

    # print(f"\nTest Query: '{test_query}'")
    # print(f"Retrieved {len(results)} relevant chunks:\n")

    # for i, doc in enumerate(results[:2], 1):
    #     print(f"Chunk {i}:")
    #     print(f"{doc.page_content[:150]}...")
    #     source_file = doc.metadata.get("source", "N/A")
    #     print(
    #         f"Source: {Path(source_file).name} (Page {doc.metadata.get('page', 'N/A')})\n"
    #     )

    print("=" * 60)

    return True


def main():
    check_current_doc()


if __name__ == "__main__":
    main()
