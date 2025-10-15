# RAG Document Management Guide

## Adding Documents to Vector Store

### Option 1: Quick Add (No Rate Limiting)
Use this when you have quota available:

```bash
cd backend
uv run python rag/add_document.py ixora_general.pdf
```

### Option 2: Add with Rate Limiting (Recommended)
Use this to avoid hitting API quotas:

```bash
cd backend
uv run python rag/add_document_with_retry.py ixora_general.pdf --batch-size 3 --delay 5
```

**Parameters:**
- `--batch-size`: Number of chunks to process at once (default: 3)
- `--delay`: Seconds to wait between batches (default: 5)

### Option 3: Reinitialize Entire Vector Store
Use this to rebuild from scratch (replaces all data):

```bash
cd backend
# Edit rag/init_vectorstore.py to include all your PDFs
uv run python rag/init_vectorstore.py
```

## Handling Rate Limits

### Google Gemini Free Tier Limits:
- **Per minute**: 1,500 requests
- **Per day**: 15,000 requests

### If you hit the quota:
1. **Wait**: Free tier resets every 24 hours
2. **Upgrade**: Get a paid API key for higher limits
3. **Use smaller batches**: Reduce `--batch-size` to 1 or 2

## Current Document Status

Your PDFs in backend/:
- `ixora.pdf` (45 KB) - Original document
- `ixora_general.pdf` (78 MB) - New document to add

## Testing Retrieval

After adding documents, test retrieval:

```bash
cd backend
uv run python -c "
from rag.vector_store import get_vector_store

vector_store = get_vector_store()
print(f'Total documents: {vector_store._collection.count()}')

# Test query
results = vector_store.similarity_search('company services', k=3)
for i, doc in enumerate(results, 1):
    print(f'\n{i}. {doc.page_content[:200]}...')
    print(f'   Source: {doc.metadata.get(\"source\", \"N/A\")}')
"
```

## Troubleshooting

### Error: "Quota exceeded"
**Solution**: Use the rate-limited script or wait for quota reset

```bash
# Try with smaller batches and longer delays
uv run python rag/add_document_with_retry.py ixora_general.pdf --batch-size 1 --delay 10
```

### Error: "Vector store not initialized"
**Solution**: Initialize it first

```bash
uv run python rag/init_vectorstore.py
```

### Error: "PDF not found"
**Solution**: Make sure you're in the backend directory

```bash
cd backend
ls *.pdf  # Check if PDFs are there
```

## Admin API Integration

Once documents are added, you can re-index via the admin API:

```bash
# Using curl
curl -X POST http://localhost:8000/admin/documents/reindex \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Or use the admin frontend interface.

## Vector Store Location

- **Development**: `backend/chroma_db/`
- **Docker**: `/app/chroma_db` (persisted via volumes)

## Best Practices

1. **Add documents during off-peak hours** to avoid disrupting users
2. **Test with small PDFs first** before adding large files
3. **Use rate limiting** to avoid quota issues
4. **Backup chroma_db/** before major changes
5. **Monitor vector store size** - large stores need more memory
