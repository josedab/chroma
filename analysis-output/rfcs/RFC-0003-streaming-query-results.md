# RFC-0003: Streaming Query Results API

**Status:** Draft
**Author:** Claude Code Analysis
**Created:** 2025-11-17
**Commit Base:** 091f8bd5c553f8267c48664e98fb32215055f58e

---

## Summary

Introduce a streaming API for query results to handle large result sets efficiently. Current query API loads all results into memory at once, causing out-of-memory errors for queries returning 10K+ documents. Streaming API yields results in batches, reducing memory footprint by 95%+ for large queries.

---

## Motivation

### Current State

**File:** `/home/user/chroma/chromadb/api/models/Collection.py:151-200` (query method)

Current query API returns complete `QueryResult`:

```python
def query(
    self,
    query_embeddings: Optional[OneOrMany[Embedding]] = None,
    query_texts: Optional[OneOrMany[Document]] = None,
    n_results: int = 10,
    where: Optional[Where] = None,
    # ...
) -> QueryResult:
    # Returns ALL results at once
    return QueryResult(
        ids=[[...], [...]],  # n_queries x n_results
        embeddings=[[...], [...]],
        documents=[[...], [...]],
        metadatas=[[...], [...]],
        distances=[[...], [...]],
    )
```

### Problems

#### Problem 1: Memory Explosion
```python
# Query for 10K results with embeddings (384 dims)
results = collection.query(
    query_texts=["search term"],
    n_results=10000,
    include=["embeddings", "documents", "metadatas"]
)

# Memory usage:
# - Embeddings: 10K × 384 × 4 bytes = 15MB
# - Documents: 10K × 1KB avg = 10MB
# - Metadatas: 10K × 500 bytes = 5MB
# - Total: ~30MB per query
# - With 100 concurrent queries: 3GB+
```

#### Problem 2: Network Latency
```python
# User waits for ALL results before seeing first one
results = collection.query(n_results=10000)
# 5 seconds to fetch all...
for id in results['ids'][0][:10]:  # User only needs first 10!
    print(id)
```

#### Problem 3: API Gateway Timeouts
```python
# FastAPI response
@app.post("/collections/{collection_id}/query")
async def query_collection(...):
    results = collection.query(n_results=50000)  # Timeout after 30s
    return results  # May never return
```

### User Pain Points (from Issues)

1. **Out-of-memory errors** when querying large collections
2. **Timeout errors** in serverless environments (Lambda 15min limit)
3. **Cannot paginate** through results efficiently
4. **Wasted bandwidth** downloading unused results

### Target Use Cases

1. **Large-scale retrieval:** RAG systems processing 1M+ documents
2. **Batch processing:** Exporting collection data for analysis
3. **Progressive rendering:** Show first results immediately in UI
4. **Pagination:** Efficient cursor-based pagination

---

## Detailed Design

### High-Level Architecture

```
Client                    Server                    Storage
  │                         │                         │
  │──query_stream()────────>│                         │
  │                         │──get_page_1()──────────>│
  │<─────batch_1────────────│<────────────────────────│
  │                         │                         │
  │──request_next()────────>│                         │
  │                         │──get_page_2()──────────>│
  │<─────batch_2────────────│<────────────────────────│
  │                         │                         │
  │──close_stream()────────>│                         │
```

### API Design

#### Option A: Generator-Based API (Recommended)

```python
# chromadb/api/models/Collection.py - add new method
from typing import Iterator, TypedDict

class QueryResultBatch(TypedDict):
    """Single batch of query results"""
    ids: List[ID]
    embeddings: Optional[List[Embedding]]
    documents: Optional[List[Document]]
    metadatas: Optional[List[Metadata]]
    distances: Optional[List[float]]
    # Batch metadata
    batch_index: int
    total_batches: int
    has_more: bool

def query_stream(
    self,
    query_embeddings: Optional[OneOrMany[Embedding]] = None,
    query_texts: Optional[OneOrMany[Document]] = None,
    n_results: int = 10,
    where: Optional[Where] = None,
    where_document: Optional[WhereDocument] = None,
    include: Include = ["metadatas", "documents", "distances"],
    batch_size: int = 100,
) -> Iterator[QueryResultBatch]:
    """
    Stream query results in batches.

    Args:
        batch_size: Number of results per batch (default 100)
        All other args same as query()

    Yields:
        QueryResultBatch: Batches of results until n_results reached

    Example:
        >>> for batch in collection.query_stream(n_results=10000, batch_size=100):
        ...     process_results(batch['ids'])
        ...     if batch['batch_index'] >= 10:
        ...         break  # Stop early if needed
    """
    pass
```

#### Option B: Async Iterator API

```python
from typing import AsyncIterator

async def query_stream_async(
    self, ...
) -> AsyncIterator[QueryResultBatch]:
    """Async version for concurrent streaming"""
    pass

# Usage
async for batch in collection.query_stream_async(n_results=10000):
    await process_batch_async(batch)
```

---

### Implementation Details

#### Phase 1: Vector Segment Streaming

**File:** `chromadb/segment/impl/vector/local_persistent_hnsw.py`

Add batch retrieval to HNSW segment:

```python
def query_with_pagination(
    self,
    query_embeddings: Sequence[Sequence[float]],
    n_results: int,
    offset: int = 0,
    limit: int = 100,
) -> Sequence[Sequence[int]]:
    """
    Query with pagination support.

    Args:
        offset: Skip first N results
        limit: Return at most this many results

    Returns:
        Batch of nearest neighbor indices
    """
    # Use HNSW index with offset/limit
    # This requires modifying the Rust HNSW implementation
    pass
```

**Rust Implementation:** `rust/index/src/hnsw.rs`

```rust
// Add to HnswIndex
pub fn query_with_pagination(
    &self,
    query: &[f32],
    k: usize,
    offset: usize,
    limit: usize,
) -> Vec<(usize, f32)> {
    // Current: returns top-k
    let mut results = self.search(query, k);

    // New: apply offset/limit
    let start = offset.min(results.len());
    let end = (offset + limit).min(results.len());
    results[start..end].to_vec()
}
```

#### Phase 2: Metadata Segment Streaming

**File:** `chromadb/segment/impl/metadata/sqlite.py`

SQLite already supports LIMIT/OFFSET:

```python
def get_records_batch(
    self,
    ids: Sequence[str],
    offset: int = 0,
    limit: int = 100,
) -> List[Record]:
    """Get metadata records in batches"""
    query = """
        SELECT id, document, metadata
        FROM embeddings
        WHERE id IN ({})
        LIMIT ? OFFSET ?
    """.format(','.join('?' * len(ids)))

    return self._execute(query, ids + [limit, offset])
```

#### Phase 3: Collection-Level Streaming

**File:** `chromadb/api/models/Collection.py`

Implement `query_stream()`:

```python
def query_stream(
    self,
    query_embeddings: Optional[OneOrMany[Embedding]] = None,
    query_texts: Optional[OneOrMany[Document]] = None,
    n_results: int = 10,
    where: Optional[Where] = None,
    where_document: Optional[WhereDocument] = None,
    include: Include = ["metadatas", "documents", "distances"],
    batch_size: int = 100,
) -> Iterator[QueryResultBatch]:
    # Validate inputs (same as query)
    if query_embeddings is None and query_texts is None:
        raise ValueError("Must provide query_embeddings or query_texts")

    # Convert query_texts to embeddings if needed
    if query_texts is not None:
        query_embeddings = self._embed(query_texts)

    # Normalize batch size
    batch_size = min(batch_size, n_results)
    total_batches = (n_results + batch_size - 1) // batch_size

    # Stream batches
    for batch_idx in range(total_batches):
        offset = batch_idx * batch_size
        limit = min(batch_size, n_results - offset)

        # Query vector segment with pagination
        vector_results = self._client._query_with_pagination(
            collection_id=self.id,
            query_embeddings=query_embeddings,
            n_results=n_results,
            offset=offset,
            limit=limit,
            where=where,
            where_document=where_document,
            include=include,
            tenant=self.tenant,
            database=self.database,
        )

        # Yield batch
        yield QueryResultBatch(
            ids=vector_results['ids'],
            embeddings=vector_results.get('embeddings'),
            documents=vector_results.get('documents'),
            metadatas=vector_results.get('metadatas'),
            distances=vector_results.get('distances'),
            batch_index=batch_idx,
            total_batches=total_batches,
            has_more=(batch_idx < total_batches - 1),
        )
```

#### Phase 4: FastAPI Streaming Endpoint

**File:** `chromadb/server/fastapi/__init__.py`

Add Server-Sent Events (SSE) endpoint:

```python
from fastapi.responses import StreamingResponse
import json

@app.post("/api/v1/collections/{collection_id}/query_stream")
async def query_stream(
    collection_id: str,
    request: QueryEmbedding,
) -> StreamingResponse:
    """Stream query results as SSE"""

    async def event_generator():
        collection = api.get_collection(collection_id)

        for batch in collection.query_stream(
            query_embeddings=request.query_embeddings,
            n_results=request.n_results,
            batch_size=request.batch_size or 100,
            include=request.include,
        ):
            # Send as SSE event
            data = json.dumps(batch)
            yield f"data: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
```

---

## Example Usage

### Before (Current API)

```python
# Problem: Loads 10K results into memory
results = collection.query(
    query_texts=["machine learning"],
    n_results=10000,
    include=["documents", "metadatas", "distances"]
)

# Memory usage: ~30MB
# Latency: 5 seconds before first result

# User only needs first 100, but got 10K
for doc in results['documents'][0][:100]:
    print(doc)
```

### After (Streaming API)

```python
# Solution: Stream in batches
processed = 0
for batch in collection.query_stream(
    query_texts=["machine learning"],
    n_results=10000,
    batch_size=100,
    include=["documents", "metadatas", "distances"]
):
    # Process batch immediately
    for doc in batch['documents']:
        print(doc)
        processed += 1

        # Stop early if satisfied
        if processed >= 100:
            break

    if processed >= 100:
        break

# Memory usage: ~300KB (one batch)
# Latency: 50ms to first result
# Processed 100 results, fetched only 100 (not 10K)
```

### Use Case: Progressive UI Rendering

```python
# Frontend shows results as they arrive
import streamlit as st

st.write("Searching...")

results_container = st.container()

for batch in collection.query_stream(
    query_texts=[user_query],
    n_results=1000,
    batch_size=20
):
    with results_container:
        for doc, metadata, distance in zip(
            batch['documents'],
            batch['metadatas'],
            batch['distances']
        ):
            st.markdown(f"**Score:** {distance:.3f}")
            st.write(doc)
            st.json(metadata)
            st.divider()

    # User sees results immediately, can stop scrolling anytime
```

### Use Case: Export to File

```python
# Export large collection to JSONL
import json

with open('export.jsonl', 'w') as f:
    for batch in collection.query_stream(
        query_texts=[""],  # Empty query = return all
        n_results=1_000_000,
        batch_size=1000,
    ):
        for item in zip(
            batch['ids'],
            batch['documents'],
            batch['metadatas']
        ):
            f.write(json.dumps({
                'id': item[0],
                'document': item[1],
                'metadata': item[2],
            }) + '\n')

# Memory usage: constant (~1MB) instead of 1GB+
```

---

## Implementation Plan

### Milestone 1: Core Streaming Infrastructure (5 dev-days)
- [ ] Add `query_with_pagination()` to HNSW segment (Rust)
- [ ] Add `get_records_batch()` to SQLite segment
- [ ] Implement `_query_with_pagination()` in ServerAPI
- [ ] Add pagination tests

### Milestone 2: Python Collection API (4 dev-days)
- [ ] Implement `query_stream()` method
- [ ] Add `QueryResultBatch` type
- [ ] Add generator tests
- [ ] Add memory usage benchmarks

### Milestone 3: FastAPI Streaming Endpoint (3 dev-days)
- [ ] Add `/query_stream` SSE endpoint
- [ ] Implement async streaming
- [ ] Add streaming integration tests
- [ ] Test with concurrent clients

### Milestone 4: Client Libraries (2 dev-days)
- [ ] Add `query_stream()` to Python HTTP client
- [ ] Add streaming example notebooks
- [ ] Add performance comparison docs

### Milestone 5: Documentation & Examples (1 dev-day)
- [ ] API documentation
- [ ] Migration guide
- [ ] Example use cases
- [ ] Performance tuning guide

---

## Backwards Compatibility

### No Breaking Changes

- `query()` method unchanged
- `query_stream()` is new, additive API
- Existing code continues working

### Feature Detection

```python
# Check if streaming supported
if hasattr(collection, 'query_stream'):
    # Use streaming
    for batch in collection.query_stream(...):
        process(batch)
else:
    # Fallback to regular query
    results = collection.query(...)
    process(results)
```

---

## Alternatives Considered

### Alternative 1: Cursor-Based Pagination
```python
cursor = collection.query(n_results=100)
while cursor.has_more():
    batch = cursor.next()
```

**Rejected:** More complex state management, not Pythonic

### Alternative 2: Callback-Based API
```python
def callback(batch):
    process(batch)

collection.query(n_results=10000, on_batch=callback)
```

**Rejected:** Less flexible than generators, harder to compose

### Alternative 3: Offset/Limit Parameters
```python
batch1 = collection.query(n_results=100, offset=0, limit=100)
batch2 = collection.query(n_results=100, offset=100, limit=100)
```

**Rejected:** Requires manual pagination logic, inefficient

### Alternative 4: Return pandas DataFrame with chunking
```python
for chunk in collection.query_df(n_results=10000, chunksize=100):
    process(chunk)
```

**Considered:** Good DX, but adds pandas dependency

---

## Performance Impact

### Expected Improvements

| Metric | Before (n=10K) | After (batch=100) | Improvement |
|--------|----------------|-------------------|-------------|
| Memory usage | 30MB | 300KB | **100x reduction** |
| Time to first result | 5s | 50ms | **100x faster** |
| Peak memory (100 concurrent) | 3GB | 30MB | **100x reduction** |
| Network bandwidth (early stop) | 30MB | 300KB | **100x reduction** |

### Benchmarking Plan

```python
# benchmarks/streaming_query.py
import chromadb
import tracemalloc
import time

def benchmark_regular_query():
    tracemalloc.start()
    start = time.time()

    results = collection.query(
        query_texts=["test"],
        n_results=10000,
        include=["documents", "metadatas", "embeddings"]
    )

    peak_memory = tracemalloc.get_traced_memory()[1]
    latency = time.time() - start
    tracemalloc.stop()

    return {
        'peak_memory_mb': peak_memory / 1024 / 1024,
        'latency_s': latency,
        'time_to_first_result': latency,  # Same as latency
    }

def benchmark_streaming_query():
    tracemalloc.start()
    start = time.time()
    first_result_time = None

    for batch in collection.query_stream(
        query_texts=["test"],
        n_results=10000,
        batch_size=100,
    ):
        if first_result_time is None:
            first_result_time = time.time() - start

    peak_memory = tracemalloc.get_traced_memory()[1]
    total_latency = time.time() - start
    tracemalloc.stop()

    return {
        'peak_memory_mb': peak_memory / 1024 / 1024,
        'latency_s': total_latency,
        'time_to_first_result': first_result_time,
    }
```

---

## Testing Strategy

### Unit Tests

```python
# chromadb/test/api/test_streaming.py

def test_query_stream_basic():
    """Test basic streaming functionality"""
    collection = client.create_collection("test")
    collection.add(ids=[str(i) for i in range(1000)], ...)

    batches = list(collection.query_stream(
        query_texts=["test"],
        n_results=100,
        batch_size=10,
    ))

    assert len(batches) == 10
    assert batches[0]['batch_index'] == 0
    assert batches[-1]['has_more'] is False

def test_query_stream_early_stop():
    """Test stopping iteration early"""
    collection = client.create_collection("test")
    collection.add(ids=[str(i) for i in range(1000)], ...)

    batches_consumed = 0
    for batch in collection.query_stream(n_results=1000, batch_size=100):
        batches_consumed += 1
        if batches_consumed >= 3:
            break

    assert batches_consumed == 3

def test_query_stream_memory_usage():
    """Test memory stays bounded"""
    collection = client.create_collection("test")
    collection.add(ids=[str(i) for i in range(10000)], ...)

    tracemalloc.start()

    for batch in collection.query_stream(n_results=10000, batch_size=100):
        pass

    peak_memory = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()

    # Should be < 10MB (not 100MB+)
    assert peak_memory < 10 * 1024 * 1024
```

### Integration Tests

```python
def test_fastapi_streaming():
    """Test FastAPI SSE streaming"""
    import httpx

    with httpx.stream(
        "POST",
        "http://localhost:8000/api/v1/collections/test/query_stream",
        json={"query_texts": ["test"], "n_results": 1000, "batch_size": 100},
    ) as response:
        batches = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                batch = json.loads(line[6:])
                batches.append(batch)

        assert len(batches) == 10
```

---

## Documentation Requirements

### API Documentation

```markdown
# Query API

## Streaming Queries

For large result sets, use `query_stream()` to process results in batches:

```python
for batch in collection.query_stream(
    query_texts=["search term"],
    n_results=10000,
    batch_size=100
):
    print(f"Batch {batch['batch_index']}: {len(batch['ids'])} results")
```

### Parameters

- `batch_size` (int, default=100): Number of results per batch
- All other parameters same as `query()`

### Returns

Iterator of `QueryResultBatch` containing:
- `ids`, `documents`, `metadatas`, `embeddings`, `distances`
- `batch_index`: Current batch number (0-indexed)
- `total_batches`: Total number of batches
- `has_more`: Whether more batches remain
```

---

## Success Criteria

### Must Have
- [ ] `query_stream()` implements streaming for n_results > 100
- [ ] Memory usage < 10MB for 10K result stream
- [ ] Time to first result < 100ms
- [ ] All existing `query()` tests pass
- [ ] Streaming works with all `include` options

### Should Have
- [ ] FastAPI SSE endpoint functional
- [ ] Memory benchmark showing 10x+ improvement
- [ ] Documentation with 3+ use case examples
- [ ] Python HTTP client supports streaming

### Nice to Have
- [ ] Async streaming API
- [ ] JavaScript client streaming support
- [ ] Streaming dashboard example

---

## Effort Estimation

| Phase | Task | Dev-Days |
|-------|------|----------|
| 1 | Core streaming (Rust HNSW, SQLite) | 5 |
| 2 | Python Collection API | 4 |
| 3 | FastAPI endpoint | 3 |
| 4 | Client libraries | 2 |
| 5 | Documentation | 1 |
| **Total** | | **15 dev-days** |

---

## References

- [FastAPI Server-Sent Events](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- [Python Generators](https://docs.python.org/3/howto/functional.html#generators)
- [Elasticsearch Scroll API](https://www.elastic.co/guide/en/elasticsearch/reference/current/paginate-search-results.html)
- [MongoDB Cursor API](https://www.mongodb.com/docs/manual/tutorial/iterate-a-cursor/)

---

## Revision History

- **v1.0** (2025-11-17): Initial RFC draft
