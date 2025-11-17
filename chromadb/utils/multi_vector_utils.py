"""Utilities for multi-vector embedding operations.

This module provides aggregation strategies for combining multiple embedding vectors
per document, supporting use cases like:
- ColBERT-style late interaction (MaxSim)
- Multi-aspect embeddings
- Multi-modal representations
"""

from typing import List, Literal
import numpy as np
from numpy.typing import NDArray
from chromadb.api.types import MultiVector, Embedding


MultiVectorStrategy = Literal["maxsim", "avg", "sum", "first"]


def cosine_similarity(vec1: NDArray, vec2: NDArray) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score (higher is more similar)
    """
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(dot_product / (norm1 * norm2))


def maxsim_score(query_vectors: MultiVector, doc_vectors: MultiVector) -> float:
    """Compute MaxSim score between query and document multi-vectors.

    MaxSim (Maximum Similarity) is used in ColBERT-style late interaction:
    For each query vector, find the maximum similarity with any document vector,
    then sum these maximum similarities.

    Args:
        query_vectors: List of query embedding vectors
        doc_vectors: List of document embedding vectors

    Returns:
        MaxSim aggregated score (higher is more similar)
    """
    if not query_vectors or not doc_vectors:
        return 0.0

    total_score = 0.0
    for q_vec in query_vectors:
        max_sim = max(
            cosine_similarity(q_vec, d_vec)
            for d_vec in doc_vectors
        )
        total_score += max_sim

    return total_score


def average_score(query_vectors: MultiVector, doc_vectors: MultiVector) -> float:
    """Compute average of all pairwise similarities.

    Computes cosine similarity between all query-document vector pairs
    and returns their average.

    Args:
        query_vectors: List of query embedding vectors
        doc_vectors: List of document embedding vectors

    Returns:
        Average similarity score
    """
    if not query_vectors or not doc_vectors:
        return 0.0

    total = 0.0
    count = 0

    for q_vec in query_vectors:
        for d_vec in doc_vectors:
            total += cosine_similarity(q_vec, d_vec)
            count += 1

    return total / count if count > 0 else 0.0


def sum_score(query_vectors: MultiVector, doc_vectors: MultiVector) -> float:
    """Compute sum of all pairwise similarities.

    Args:
        query_vectors: List of query embedding vectors
        doc_vectors: List of document embedding vectors

    Returns:
        Sum of similarity scores
    """
    if not query_vectors or not doc_vectors:
        return 0.0

    total = 0.0
    for q_vec in query_vectors:
        for d_vec in doc_vectors:
            total += cosine_similarity(q_vec, d_vec)

    return total


def first_score(query_vectors: MultiVector, doc_vectors: MultiVector) -> float:
    """Compute similarity using only the first vectors.

    Uses only the first embedding from each multi-vector, ignoring the rest.
    Useful for backwards compatibility or when additional vectors are metadata.

    Args:
        query_vectors: List of query embedding vectors
        doc_vectors: List of document embedding vectors

    Returns:
        Cosine similarity of first vectors
    """
    if not query_vectors or not doc_vectors:
        return 0.0

    return cosine_similarity(query_vectors[0], doc_vectors[0])


def aggregate_multi_vector_scores(
    query_vectors: MultiVector,
    doc_vectors: MultiVector,
    strategy: MultiVectorStrategy = "maxsim"
) -> float:
    """Aggregate multi-vector embeddings using specified strategy.

    Args:
        query_vectors: List of query embedding vectors
        doc_vectors: List of document embedding vectors
        strategy: Aggregation strategy ("maxsim", "avg", "sum", "first")

    Returns:
        Aggregated similarity score

    Raises:
        ValueError: If strategy is not recognized
    """
    if strategy == "maxsim":
        return maxsim_score(query_vectors, doc_vectors)
    elif strategy == "avg":
        return average_score(query_vectors, doc_vectors)
    elif strategy == "sum":
        return sum_score(query_vectors, doc_vectors)
    elif strategy == "first":
        return first_score(query_vectors, doc_vectors)
    else:
        raise ValueError(
            f"Unknown multi-vector strategy: {strategy}. "
            f"Expected one of: maxsim, avg, sum, first"
        )


def flatten_multi_vectors_for_storage(
    doc_id: str,
    multi_vector: MultiVector
) -> List[tuple]:
    """Flatten multi-vector for storage with vector indices.

    Converts a multi-vector into a list of (doc_id, vector_index, embedding) tuples
    for storage in the segment layer.

    Args:
        doc_id: Document identifier
        multi_vector: List of embedding vectors for this document

    Returns:
        List of tuples (doc_id, vector_index, embedding)
    """
    return [
        (doc_id, idx, embedding)
        for idx, embedding in enumerate(multi_vector)
    ]


def unflatten_multi_vectors_from_storage(
    flattened_records: List[tuple]
) -> MultiVector:
    """Reconstruct multi-vector from flattened storage format.

    Args:
        flattened_records: List of (doc_id, vector_index, embedding) tuples

    Returns:
        Multi-vector (list of embeddings)
    """
    # Sort by vector index to ensure correct order
    sorted_records = sorted(flattened_records, key=lambda x: x[1])
    return [embedding for _, _, embedding in sorted_records]


def convert_multi_vector_to_synthetic_ids(
    doc_id: str,
    multi_vector: MultiVector,
    metadata: dict = None,
    document: str = None
) -> List[dict]:
    """Convert a multi-vector into multiple entries with synthetic IDs.

    This is a simplified storage approach that works with existing storage layer.
    Each vector in the multi-vector gets its own entry with a decorated ID.

    Args:
        doc_id: Original document ID
        multi_vector: List of embedding vectors
        metadata: Original metadata
        document: Original document text

    Returns:
        List of dicts with synthetic IDs and vectors
    """
    entries = []
    for idx, vector in enumerate(multi_vector):
        synthetic_id = f"{doc_id}__mvidx_{idx}"
        entry = {
            "id": synthetic_id,
            "embedding": vector,
            "metadata": {
                **(metadata or {}),
                "__multi_vector_parent": doc_id,
                "__multi_vector_index": idx,
                "__multi_vector_count": len(multi_vector),
            },
            "document": document,
        }
        entries.append(entry)
    return entries


def extract_parent_id_from_synthetic(synthetic_id: str) -> str:
    """Extract the original document ID from a synthetic multi-vector ID.

    Args:
        synthetic_id: ID in format "doc_id__mvidx_N"

    Returns:
        Original document ID
    """
    if "__mvidx_" in synthetic_id:
        return synthetic_id.split("__mvidx_")[0]
    return synthetic_id


def is_synthetic_multi_vector_id(doc_id: str) -> bool:
    """Check if an ID is a synthetic multi-vector ID.

    Args:
        doc_id: Document ID to check

    Returns:
        True if this is a synthetic multi-vector ID
    """
    return "__mvidx_" in doc_id
