# Multi-Vector Embeddings

## Overview

Chroma now supports **multi-vector embeddings** - the ability to store multiple embedding vectors per document. This enables advanced retrieval architectures including:

- **ColBERT-style late interaction**: Token-level embeddings for fine-grained matching
- **Multi-aspect embeddings**: Different semantic dimensions of the same content
- **Multi-modal representations**: Combine text, image, and other modality embeddings

## Quick Start

### Basic Usage

```python
import chromadb

client = chromadb.Client()
collection = client.create_collection("my_collection")

# Add a document with multiple embedding vectors
collection.add(
    ids=["doc1"],
    embeddings=[
        [  # Multi-vector for doc1
            [0.1, 0.2, 0.3],  # Vector 1
            [0.4, 0.5, 0.6],  # Vector 2
            [0.7, 0.8, 0.9],  # Vector 3
        ]
    ],
    documents=["My document text"]
)

# Query with multi-vector and aggregation strategy
results = collection.query(
    query_embeddings=[
        [  # Multi-vector query
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
        ]
    ],
    n_results=10,
    multi_vector_strategy="maxsim"  # ColBERT-style MaxSim
)
```

## Aggregation Strategies

When querying with multi-vector embeddings, you can specify how to aggregate scores:

### 1. MaxSim (ColBERT)

**Use case**: Token-level late interaction, fine-grained matching

For each query vector, finds the maximum similarity with any document vector, then sums these maximums.

```python
results = collection.query(
    query_embeddings=[query_vectors],
    multi_vector_strategy="maxsim"
)
```

**Formula**: `score = Σ max(sim(q_i, d_j)) for all query vectors q_i`

### 2. Average

**Use case**: Balanced multi-aspect matching

Computes the average of all pairwise similarities between query and document vectors.

```python
results = collection.query(
    query_embeddings=[query_vectors],
    multi_vector_strategy="avg"
)
```

**Formula**: `score = (Σ sim(q_i, d_j)) / (|q| × |d|)`

### 3. Sum

**Use case**: When you want total similarity magnitude

Sums all pairwise similarities (similar to average but not normalized).

```python
results = collection.query(
    query_embeddings=[query_vectors],
    multi_vector_strategy="sum"
)
```

**Formula**: `score = Σ sim(q_i, d_j) for all q_i, d_j pairs`

### 4. First

**Use case**: Backwards compatibility, hierarchical embeddings

Uses only the first vector from each multi-vector, ignoring the rest.

```python
results = collection.query(
    query_embeddings=[query_vectors],
    multi_vector_strategy="first"
)
```

**Formula**: `score = sim(q_0, d_0)`

## Use Cases

### ColBERT-Style Retrieval

```python
# Simulate token-level embeddings (use actual ColBERT model in production)
doc_token_embeddings = [
    [0.1, 0.2, 0.3],  # "The"
    [0.4, 0.5, 0.6],  # "quick"
    [0.7, 0.8, 0.9],  # "brown"
]

collection.add(
    ids=["doc1"],
    embeddings=[doc_token_embeddings],
    documents=["The quick brown fox"],
    metadatas=[{"embedding_type": "colbert"}]
)

# Query with token embeddings
query_token_embeddings = [
    [0.4, 0.5, 0.6],  # "fast"
    [0.7, 0.8, 0.9],  # "animal"
]

results = collection.query(
    query_embeddings=[query_token_embeddings],
    multi_vector_strategy="maxsim"
)
```

### Multi-Aspect Embeddings

```python
# Different aspects of a product
product_embeddings = [
    [0.9, 0.1, 0.0],  # Technical specs
    [0.1, 0.9, 0.0],  # Design/aesthetics
    [0.0, 0.1, 0.9],  # User reviews
]

collection.add(
    ids=["product1"],
    embeddings=[product_embeddings],
    documents=["iPhone 15 Pro - Great camera, fast processor"],
    metadatas=[{"aspects": ["specs", "design", "reviews"]}]
)

# Query will match best aspect
results = collection.query(
    query_embeddings=[[[0.9, 0.1, 0.0]]],  # Specs-focused query
    multi_vector_strategy="maxsim"
)
```

### Multi-Modal Embeddings

```python
# Combine image and text embeddings (use CLIP or similar in production)
multimodal_embeddings = [
    [0.8, 0.2, 0.0],  # Image embedding
    [0.7, 0.3, 0.0],  # Text embedding
]

collection.add(
    ids=["item1"],
    embeddings=[multimodal_embeddings],
    documents=["Red sneakers"],
    metadatas=[{"modalities": ["image", "text"]}]
)

# Query with either modality
results = collection.query(
    query_embeddings=[[[0.7, 0.3, 0.0]]],  # Text query
    multi_vector_strategy="avg"
)
```

## Backwards Compatibility

Single-vector embeddings continue to work exactly as before:

```python
# Traditional single-vector (still works!)
collection.add(
    ids=["doc1"],
    embeddings=[[0.1, 0.2, 0.3]],  # Single vector
    documents=["Traditional document"]
)

# Query without multi_vector_strategy
results = collection.query(
    query_embeddings=[[0.1, 0.2, 0.3]],
    n_results=10
)
```

Multi-vector with length 1 is equivalent to single-vector:

```python
# These are equivalent:
embeddings=[[0.1, 0.2, 0.3]]           # Single-vector
embeddings=[[[0.1, 0.2, 0.3]]]         # Multi-vector with 1 vector
```

## API Reference

### Collection.add()

```python
def add(
    self,
    ids: List[str],
    embeddings: Optional[Union[
        List[List[float]],              # Single-vector
        List[List[List[float]]]         # Multi-vector
    ]] = None,
    metadatas: Optional[List[dict]] = None,
    documents: Optional[List[str]] = None,
    ...
) -> None:
```

**Multi-vector format**: `List[List[List[float]]]`
- Outer list: one entry per document
- Middle list: multiple vectors per document
- Inner list: embedding dimensions

**Example**:
```python
embeddings=[
    [[0.1, 0.2], [0.3, 0.4]],  # Doc 1: 2 vectors
    [[0.5, 0.6], [0.7, 0.8], [0.9, 1.0]]  # Doc 2: 3 vectors
]
```

### Collection.query()

```python
def query(
    self,
    query_embeddings: Optional[Union[
        List[List[float]],              # Single-vector
        List[List[List[float]]]         # Multi-vector
    ]] = None,
    n_results: int = 10,
    multi_vector_strategy: Optional[Literal[
        "maxsim", "avg", "sum", "first"
    ]] = None,
    ...
) -> QueryResult:
```

**Parameters**:
- `query_embeddings`: Query vectors (single or multi-vector format)
- `multi_vector_strategy`: How to aggregate multi-vector scores
  - `"maxsim"`: ColBERT-style maximum similarity
  - `"avg"`: Average of all pairwise similarities
  - `"sum"`: Sum of all pairwise similarities
  - `"first"`: Use only first vectors
- Other parameters work as before

## Implementation Details

### Type System

New types in `chromadb.api.types`:

```python
# Single vector types (existing)
PyEmbedding = List[float]
Embedding = np.ndarray

# Multi-vector types (new)
PyMultiVector = List[PyEmbedding]
MultiVector = List[Embedding]

# Aggregation strategy
MultiVectorStrategy = Literal["maxsim", "avg", "sum", "first"]
```

### Validation

Multi-vector embeddings are validated to ensure:
- All vectors in a multi-vector have the same dimensionality
- All values are numeric (int or float)
- No empty vectors or multi-vectors

### Storage Format

Currently implemented using a simplified approach:
- Each vector in a multi-vector is stored with a synthetic ID: `{doc_id}__mvidx_{index}`
- Original document metadata includes multi-vector tracking fields
- Query aggregation happens at query time

## Performance Considerations

### Storage Overhead

Multi-vector embeddings require more storage:
- **Single-vector**: 1 vector per document
- **Multi-vector**: N vectors per document (where N = number of vectors)

**Example**: Document with 10 token embeddings requires 10x storage.

### Query Performance

Query time increases with multi-vector:
- **MaxSim**: O(|q| × |d|) similarity computations per document
- **Average/Sum**: O(|q| × |d|) similarity computations per document
- **First**: O(1) similarity computations per document (same as single-vector)

Where |q| = number of query vectors, |d| = number of document vectors.

**Recommendation**: Use multi-vector only when the retrieval quality improvement justifies the performance cost.

### Optimization Tips

1. **Use "first" strategy** when possible for faster queries
2. **Limit vector count** per document (typically 10-50 for ColBERT)
3. **Consider filtering** to reduce candidate set before multi-vector scoring
4. **Batch queries** when querying multiple multi-vector queries

## Migration Guide

### From Single-Vector to Multi-Vector

To convert existing collections:

```python
# Old code (single-vector)
collection.add(
    ids=["doc1"],
    embeddings=[[0.1, 0.2, 0.3]],
    documents=["text"]
)

# New code (multi-vector with 1 vector - backwards compatible)
collection.add(
    ids=["doc1"],
    embeddings=[[[0.1, 0.2, 0.3]]],  # Extra nesting
    documents=["text"]
)
```

No migration needed for existing data - single-vector continues to work!

## Examples

See `examples/multi_vector_embeddings.py` for complete working examples.

## References

- [ColBERT Paper](https://arxiv.org/abs/2004.12832)
- [ColBERT v2 Paper](https://arxiv.org/abs/2112.01488)
- [RFC-0007: Multi-Vector Embeddings](analysis-output/rfcs/RFC-0007-multi-vector-embeddings.md)

## Support

For issues or questions:
- GitHub Issues: https://github.com/chroma-core/chroma/issues
- Discord: https://discord.gg/chroma

---

**Status**: Initial implementation (v1.0)
**Date**: 2025-11-17
