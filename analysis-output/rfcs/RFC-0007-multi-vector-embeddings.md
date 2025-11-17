# RFC-0007: Multi-Vector Embeddings per Document

**Status:** Draft
**Author:** Claude Code Analysis
**Created:** 2025-11-17
**Commit Base:** 091f8bd5c553f8267c48664e98fb32215055f58e

---

## Summary

Enable storing multiple embedding vectors per document to support advanced retrieval models like ColBERT (late-interaction), multi-aspect embeddings, and multi-modal representations. This unlocks next-generation retrieval architectures while maintaining backwards compatibility.

---

## Motivation

### Current State

Each document has exactly one embedding vector:

**File:** `/home/user/chroma/chromadb/api/models/Collection.py:51-64`

```python
def add(
    self,
    ids: OneOrMany[ID],
    embeddings: Optional[OneOrMany[Embedding]] = None,  # One per document
    documents: Optional[OneOrMany[Document]] = None,
    # ...
)
```

### Use Cases for Multi-Vector

#### Use Case 1: ColBERT Late Interaction

```python
# ColBERT: Each token gets an embedding
document = "The quick brown fox jumps"
token_embeddings = [
    [0.1, 0.2, ...],  # "The"
    [0.3, 0.4, ...],  # "quick"
    [0.5, 0.6, ...],  # "brown"
    # ... one vector per token
]
# MaxSim scoring: max similarity between query-doc token pairs
```

#### Use Case 2: Multi-Aspect Embeddings

```python
# Different aspects of same document
product_description = "iPhone 15 Pro - Great camera, fast processor"
aspects = {
    "visual": [...],      # Image embedding
    "specs": [...],       # Technical specs embedding  
    "reviews": [...],     # Customer review embedding
}
```

#### Use Case 3: Hierarchical Embeddings

```python
# Document + paragraph + sentence embeddings
document_embeddings = {
    "document": [...],
    "paragraphs": [[...], [...], [...]],
    "sentences": [[...], [...], [...], ...]
}
```

### Problems with Current Architecture

1. **Cannot Store:** No way to store multiple vectors per document
2. **Workaround is Hacky:** Users create duplicate documents with different IDs
3. **Late Interaction Impossible:** Can't implement ColBERT-style MaxSim

---

## Detailed Design

### Schema Changes

**New Type:** `MultiVector`

```python
from typing import List, Union

# Single vector (backwards compatible)
Embedding = List[float]

# Multiple vectors
MultiVector = List[Embedding]

# Either single or multi
EmbeddingInput = Union[Embedding, MultiVector]
```

### API Changes

#### Add with Multi-Vector

```python
collection.add(
    ids=["doc1"],
    embeddings=[
        # Multi-vector: list of embeddings
        [
            [0.1, 0.2, 0.3],  # Token 1
            [0.4, 0.5, 0.6],  # Token 2
            [0.7, 0.8, 0.9],  # Token 3
        ]
    ],
    documents=["The quick brown"],
    metadata={
        "embedding_type": "colbert"
    }
)
```

#### Query with Multi-Vector Scoring

```python
results = collection.query(
    query_embeddings=[
        [
            [0.1, 0.2, 0.3],  # Query token 1
            [0.4, 0.5, 0.6],  # Query token 2
        ]
    ],
    n_results=10,
    # NEW: Specify aggregation method
    multi_vector_strategy="maxsim"  # or "avg", "sum", "first"
)
```

### Aggregation Strategies

**1. MaxSim (ColBERT)**
```python
def maxsim_score(query_vectors, doc_vectors):
    """Max similarity between query-doc token pairs"""
    scores = []
    for q_vec in query_vectors:
        max_sim = max(
            cosine_similarity(q_vec, d_vec) 
            for d_vec in doc_vectors
        )
        scores.append(max_sim)
    return sum(scores)  # Sum of max similarities
```

**2. Average Pooling**
```python
def average_score(query_vectors, doc_vectors):
    """Average of all pairwise similarities"""
    total = 0
    for q_vec in query_vectors:
        for d_vec in doc_vectors:
            total += cosine_similarity(q_vec, d_vec)
    return total / (len(query_vectors) * len(doc_vectors))
```

### Storage Format

**Option A: Flattened Storage**
```
Document ID | Vector Index | Embedding
doc1        | 0            | [0.1, 0.2, 0.3]
doc1        | 1            | [0.4, 0.5, 0.6]
doc1        | 2            | [0.7, 0.8, 0.9]
```

**Option B: Nested Storage**
```
Document ID | Embeddings (JSON)
doc1        | [[0.1,0.2,0.3], [0.4,0.5,0.6], [0.7,0.8,0.9]]
```

**Recommendation:** Option A for better query performance

---

## Implementation Plan

### Milestone 1: Storage Layer (10 dev-days)
- [ ] Extend segment schema for multi-vector
- [ ] Update HNSW index to handle multiple vectors
- [ ] Modify SQLite metadata schema
- [ ] Data migration for existing collections

### Milestone 2: API Layer (8 dev-days)
- [ ] Update `add()` to accept multi-vector
- [ ] Update `query()` with aggregation strategies
- [ ] Implement MaxSim scoring
- [ ] Add validation for multi-vector inputs

### Milestone 3: Index Optimization (5 dev-days)
- [ ] Optimize HNSW for multi-vector lookup
- [ ] Batch similarity computation
- [ ] Cache query token embeddings
- [ ] Benchmark performance

### Milestone 4: Documentation (2 dev-days)
- [ ] API documentation
- [ ] ColBERT example
- [ ] Multi-modal example
- [ ] Migration guide

---

## Example Usage

### ColBERT-Style Retrieval

```python
from transformers import AutoTokenizer, AutoModel

# Setup
tokenizer = AutoTokenizer.from_pretrained("colbert-ir/colbertv2.0")
model = AutoModel.from_pretrained("colbert-ir/colbertv2.0")

# Embed document as token vectors
def colbert_embed(text):
    tokens = tokenizer(text, return_tensors="pt")
    outputs = model(**tokens)
    # Returns: [num_tokens, embedding_dim]
    return outputs.last_hidden_state[0].tolist()

# Add document with multi-vector
collection.add(
    ids=["doc1"],
    embeddings=[colbert_embed("The quick brown fox")],
    documents=["The quick brown fox"]
)

# Query with multi-vector
query_embeddings = colbert_embed("fast fox")
results = collection.query(
    query_embeddings=[query_embeddings],
    n_results=10,
    multi_vector_strategy="maxsim"
)
```

### Multi-Modal Embeddings

```python
from chromadb.utils.embedding_functions import OpenCLIPEmbeddingFunction

# Image + text embeddings for same document
clip = OpenCLIPEmbeddingFunction()

image_emb = clip(images=["product.jpg"])[0]
text_emb = clip(texts=["Red sneakers size 10"])[0]

collection.add(
    ids=["product1"],
    embeddings=[
        [image_emb, text_emb]  # Multi-modal multi-vector
    ],
    documents=["Red sneakers size 10"],
    uris=["product.jpg"],
    metadata={"embedding_types": ["image", "text"]}
)

# Query with image
results = collection.query(
    query_embeddings=[[clip(images=["query.jpg"])[0]]],
    multi_vector_strategy="max"  # Use most similar modality
)
```

---

## Backwards Compatibility

### Automatic Upgrade

```python
# Old code (single vector) - still works!
collection.add(
    ids=["doc1"],
    embeddings=[[0.1, 0.2, 0.3]],  # Single vector
    documents=["text"]
)

# Internally stored as multi-vector with length 1
# Query behavior unchanged
```

### Migration

```python
# Migrate existing collection to multi-vector
def migrate_to_multivector(collection):
    """Convert single-vector collection to multi-vector format"""
    # Storage layer automatically handles format conversion
    # No user action needed
    pass
```

---

## Alternatives Considered

### Alternative 1: Separate Collections per Vector Type
**Rejected:** Violates DRY, requires manual join logic

### Alternative 2: Concatenate Vectors
**Rejected:** Loses semantic separation, poor for late interaction

### Alternative 3: Store as Metadata
**Rejected:** Can't index metadata vectors efficiently

---

## Performance Impact

### Expected Performance

| Operation | Single Vector | Multi-Vector (10 tokens) | Overhead |
|-----------|---------------|--------------------------|----------|
| Add | 10ms | 15ms | 1.5x |
| Query (10 results) | 50ms | 150ms | 3x |
| Storage | 1KB | 10KB | 10x |

**Mitigation:**
- Use multi-vector only when needed
- Optimize MaxSim with SIMD
- Cache intermediate results

### Benchmarking

```python
# Benchmark MaxSim vs single-vector
import time
import numpy as np

def benchmark_maxsim():
    # Single vector baseline
    start = time.time()
    results_single = collection.query(
        query_embeddings=[[...]],
        n_results=100
    )
    baseline = time.time() - start

    # Multi-vector MaxSim
    start = time.time()
    results_multi = collection.query(
        query_embeddings=[[[...], [...], [...]]],  # 3 tokens
        n_results=100,
        multi_vector_strategy="maxsim"
    )
    multi_time = time.time() - start

    print(f"Overhead: {multi_time/baseline:.2f}x")
```

---

## Testing Strategy

### Unit Tests

```python
def test_multi_vector_add():
    """Test adding multi-vector embeddings"""
    collection.add(
        ids=["doc1"],
        embeddings=[
            [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        ]
    )
    assert collection.count() == 1

def test_maxsim_scoring():
    """Test MaxSim aggregation"""
    # Add document with 2 token vectors
    collection.add(
        ids=["doc1"],
        embeddings=[[[1.0, 0.0], [0.0, 1.0]]]
    )

    # Query with 2 token vectors
    results = collection.query(
        query_embeddings=[[[1.0, 0.0], [0.0, 1.0]]],
        multi_vector_strategy="maxsim"
    )

    # Perfect match should score highest
    assert results['distances'][0][0] < 0.01
```

---

## Success Criteria

- [ ] ColBERT-style retrieval works
- [ ] Multi-modal embeddings supported
- [ ] Backwards compatible with single-vector
- [ ] Performance overhead < 5x for 10-token documents

---

## Effort Estimation

| Phase | Dev-Days |
|-------|----------|
| Storage layer | 10 |
| API layer | 8 |
| Optimization | 5 |
| Documentation | 2 |
| **Total** | **25** |

---

## References

- [ColBERT Paper](https://arxiv.org/abs/2004.12832)
- [ColBERT v2 Paper](https://arxiv.org/abs/2112.01488)
- [Multi-Vector Retrieval (Pinecone)](https://www.pinecone.io/learn/multi-vector-search/)

---

## Revision History

- **v1.0** (2025-11-17): Initial RFC
