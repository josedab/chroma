"""
Multi-Vector Embeddings Example

This example demonstrates how to use Chroma's multi-vector embeddings feature
to support advanced retrieval models like ColBERT, multi-aspect embeddings,
and multi-modal representations.

Based on RFC-0007: Multi-Vector Embeddings per Document
"""

import chromadb
import numpy as np


def example_colbert_style_retrieval():
    """
    Example 1: ColBERT-Style Late Interaction

    ColBERT embeds each token in a document separately, enabling fine-grained
    matching between query and document tokens.
    """
    print("=" * 60)
    print("Example 1: ColBERT-Style Late Interaction")
    print("=" * 60)

    # Create a client and collection
    client = chromadb.Client()
    collection = client.create_collection("colbert_example")

    # Simulate token-level embeddings for a document
    # In practice, you'd use a ColBERT model to generate these
    doc_text = "The quick brown fox"
    doc_token_embeddings = [
        [0.1, 0.2, 0.3],  # "The"
        [0.4, 0.5, 0.6],  # "quick"
        [0.7, 0.8, 0.9],  # "brown"
        [1.0, 1.1, 1.2],  # "fox"
    ]

    # Add document with multi-vector embeddings
    collection.add(
        ids=["doc1"],
        embeddings=[doc_token_embeddings],  # List of lists of vectors
        documents=[doc_text],
        metadatas=[{"type": "colbert"}],
    )

    # Query with token-level embeddings
    query_text = "fast fox"
    query_token_embeddings = [
        [0.4, 0.5, 0.6],  # "fast" (similar to "quick")
        [1.0, 1.1, 1.2],  # "fox"
    ]

    # Use MaxSim strategy for ColBERT-style retrieval
    results = collection.query(
        query_embeddings=[query_token_embeddings],
        n_results=5,
        multi_vector_strategy="maxsim",
    )

    print(f"Query: {query_text}")
    print(f"Results: {results['documents']}")
    print()


def example_multi_aspect_embeddings():
    """
    Example 2: Multi-Aspect Embeddings

    Different aspects of the same content get separate embedding vectors,
    enabling nuanced retrieval based on different semantic dimensions.
    """
    print("=" * 60)
    print("Example 2: Multi-Aspect Embeddings")
    print("=" * 60)

    client = chromadb.Client()
    collection = client.create_collection("multi_aspect_example")

    # Product with different aspect embeddings
    product_desc = "iPhone 15 Pro - Great camera, fast processor, beautiful display"

    # Simulate embeddings for different aspects
    # In practice, you'd use specialized models or prompts for each aspect
    aspect_embeddings = [
        [0.9, 0.1, 0.0],  # Hardware specs aspect
        [0.1, 0.9, 0.0],  # Visual/design aspect
        [0.0, 0.1, 0.9],  # Performance aspect
    ]

    collection.add(
        ids=["product1"],
        embeddings=[aspect_embeddings],
        documents=[product_desc],
        metadatas=[
            {
                "aspects": ["hardware", "design", "performance"],
                "product": "iPhone 15 Pro",
            }
        ],
    )

    # Query focusing on performance aspect
    performance_query_embeddings = [
        [0.0, 0.0, 1.0],  # Performance-focused query
    ]

    results = collection.query(
        query_embeddings=[performance_query_embeddings],
        n_results=5,
        multi_vector_strategy="maxsim",  # Find best matching aspect
    )

    print(f"Performance query results: {results['documents']}")
    print()


def example_multi_modal_embeddings():
    """
    Example 3: Multi-Modal Embeddings

    Combine embeddings from different modalities (text, image, etc.)
    for the same document.
    """
    print("=" * 60)
    print("Example 3: Multi-Modal Embeddings")
    print("=" * 60)

    client = chromadb.Client()
    collection = client.create_collection("multi_modal_example")

    # Product with both image and text embeddings
    # In practice, you'd use CLIP or similar multi-modal models
    product_name = "Red running shoes"

    multi_modal_embeddings = [
        [0.8, 0.2, 0.0],  # Image embedding (from product photo)
        [0.7, 0.3, 0.0],  # Text embedding (from description)
    ]

    collection.add(
        ids=["shoe1"],
        embeddings=[multi_modal_embeddings],
        documents=[product_name],
        metadatas=[{"modalities": ["image", "text"], "color": "red"}],
    )

    # Query with text embedding
    text_query = [[0.7, 0.3, 0.0]]

    results = collection.query(
        query_embeddings=text_query,
        n_results=5,
        multi_vector_strategy="avg",  # Average across modalities
    )

    print(f"Text query results: {results['documents']}")
    print()


def example_backwards_compatibility():
    """
    Example 4: Backwards Compatibility

    Single-vector embeddings continue to work as before.
    Multi-vector with length 1 is equivalent to single-vector.
    """
    print("=" * 60)
    print("Example 4: Backwards Compatibility")
    print("=" * 60)

    client = chromadb.Client()
    collection = client.create_collection("backwards_compat_example")

    # Traditional single-vector approach (still works!)
    collection.add(
        ids=["doc1", "doc2"],
        embeddings=[
            [0.1, 0.2, 0.3],  # Single vector for doc1
            [0.4, 0.5, 0.6],  # Single vector for doc2
        ],
        documents=["First document", "Second document"],
    )

    # Query with single vector (no multi_vector_strategy needed)
    results = collection.query(
        query_embeddings=[[0.1, 0.2, 0.3]],
        n_results=2,
    )

    print(f"Single-vector query results: {results['documents']}")
    print()


def example_aggregation_strategies():
    """
    Example 5: Different Aggregation Strategies

    Demonstrates the different ways to aggregate multi-vector scores.
    """
    print("=" * 60)
    print("Example 5: Aggregation Strategies")
    print("=" * 60)

    client = chromadb.Client()

    # Same data, different strategies
    doc_embeddings = [
        [
            [1.0, 0.0],
            [0.0, 1.0],
        ]
    ]
    query_embeddings = [
        [
            [1.0, 0.0],
            [0.0, 1.0],
        ]
    ]

    strategies = ["maxsim", "avg", "sum", "first"]

    for strategy in strategies:
        collection = client.create_collection(f"strategy_{strategy}")

        collection.add(
            ids=["doc1"], embeddings=doc_embeddings, documents=["Test document"]
        )

        results = collection.query(
            query_embeddings=query_embeddings,
            n_results=1,
            multi_vector_strategy=strategy,  # type: ignore
        )

        print(f"Strategy '{strategy}': distance = {results['distances'][0][0]:.4f}")

    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("CHROMA MULTI-VECTOR EMBEDDINGS EXAMPLES")
    print("=" * 60 + "\n")

    example_colbert_style_retrieval()
    example_multi_aspect_embeddings()
    example_multi_modal_embeddings()
    example_backwards_compatibility()
    example_aggregation_strategies()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
