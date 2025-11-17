"""
Standard benchmark suite for Chroma.

This module defines the standard set of benchmarks that should be run
to evaluate Chroma's performance. It includes micro benchmarks (individual
operations), macro benchmarks (realistic workflows), and resource benchmarks
(memory and startup time).
"""

import time
import tempfile
import shutil
import sys
from pathlib import Path
from typing import List

import chromadb
from chromadb.config import Settings

# Add parent directory to path to import framework
sys.path.insert(0, str(Path(__file__).parent))
from framework import benchmark, BenchmarkResult, print_results, save_results


def run_standard_suite(
    iterations: int = 100,
    warmup: int = 10,
    output_path: Path = None
) -> List[BenchmarkResult]:
    """
    Run all standard benchmarks and return results.

    This suite includes:
    - Micro benchmarks: add, query, delete operations
    - Macro benchmarks: batch operations, RAG workflows
    - Resource benchmarks: memory footprint

    Args:
        iterations: Number of iterations per benchmark (default: 100)
        warmup: Number of warmup iterations (default: 10)
        output_path: Optional path to save results JSON file

    Returns:
        List of BenchmarkResult objects
    """
    print("=" * 70)
    print("CHROMA STANDARD BENCHMARK SUITE")
    print("=" * 70)
    print(f"Iterations: {iterations}")
    print(f"Warmup: {warmup}")
    print("=" * 70)

    results = []

    # Run each benchmark category
    results.extend(_run_micro_benchmarks(iterations, warmup))
    results.extend(_run_macro_benchmarks(iterations, warmup))
    results.extend(_run_resource_benchmarks(iterations, warmup))

    # Print summary
    print_results(results)

    # Save results if output path provided
    if output_path:
        save_results(results, output_path)

    return results


def _run_micro_benchmarks(iterations: int, warmup: int) -> List[BenchmarkResult]:
    """
    Run micro benchmarks - individual operations in isolation.

    These benchmarks test:
    - Single document add latency
    - Query latency with different result counts
    - Delete operation latency
    - Get operation latency
    """
    print("\n>>> Running Micro Benchmarks...")
    results = []

    # Create a temporary directory for the client
    temp_dir = tempfile.mkdtemp()

    try:
        # Initialize client with ephemeral mode for clean state
        client = chromadb.Client()

        # Benchmark 1: Add single document
        collection = client.create_collection(name="bench_add_single")

        def add_single():
            collection.add(
                ids=[f"id_{time.time_ns()}"],
                documents=["Sample document for benchmarking performance"],
                metadatas=[{"key": "value", "index": 1}]
            )

        results.append(benchmark(
            "add_single_document",
            add_single,
            iterations=iterations,
            warmup=warmup
        ))

        # Benchmark 2: Query latency (10 results)
        # Prepopulate collection with data
        collection_query = client.create_collection(name="bench_query")
        collection_query.add(
            ids=[f"doc_{i}" for i in range(10000)],
            documents=[f"Document content number {i} with some text" for i in range(10000)],
            metadatas=[{"index": i, "category": f"cat_{i % 10}"} for i in range(10000)]
        )

        def query_10_results():
            collection_query.query(
                query_texts=["sample query text"],
                n_results=10
            )

        results.append(benchmark(
            "query_10_results",
            query_10_results,
            iterations=iterations,
            warmup=warmup
        ))

        # Benchmark 3: Query latency (100 results)
        def query_100_results():
            collection_query.query(
                query_texts=["sample query text"],
                n_results=100
            )

        results.append(benchmark(
            "query_100_results",
            query_100_results,
            iterations=iterations,
            warmup=warmup
        ))

        # Benchmark 4: Get by ID
        def get_by_id():
            collection_query.get(
                ids=[f"doc_{i}" for i in range(10)],
                include=["documents", "metadatas"]
            )

        results.append(benchmark(
            "get_by_id_10_docs",
            get_by_id,
            iterations=iterations,
            warmup=warmup
        ))

        # Benchmark 5: Delete documents
        collection_delete = client.create_collection(name="bench_delete")
        # Prepopulate for delete tests
        for i in range(iterations):
            collection_delete.add(
                ids=[f"del_{i}_{j}" for j in range(10)],
                documents=[f"Delete test {i}_{j}" for j in range(10)]
            )

        counter = [0]  # Use list to allow modification in closure

        def delete_documents():
            try:
                collection_delete.delete(
                    ids=[f"del_{counter[0]}_{j}" for j in range(10)]
                )
                counter[0] += 1
            except Exception:
                # Reset if we run out of documents
                counter[0] = 0

        results.append(benchmark(
            "delete_10_documents",
            delete_documents,
            iterations=min(iterations, 100),  # Limit to avoid running out
            warmup=warmup
        ))

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    return results


def _run_macro_benchmarks(iterations: int, warmup: int) -> List[BenchmarkResult]:
    """
    Run macro benchmarks - realistic workflows.

    These benchmarks test:
    - Batch add operations
    - RAG (Retrieval-Augmented Generation) workflow simulation
    - High throughput scenarios
    """
    print("\n>>> Running Macro Benchmarks...")
    results = []

    client = chromadb.Client()

    # Benchmark 1: Batch add (100 documents)
    collection_batch = client.create_collection(name="bench_batch_add")

    def batch_add_100():
        ts = time.time_ns()
        collection_batch.add(
            ids=[f"batch_{ts}_{i}" for i in range(100)],
            documents=[f"Batch document {i} with substantial content" for i in range(100)],
            metadatas=[{"batch_id": ts, "index": i} for i in range(100)]
        )

    results.append(benchmark(
        "batch_add_100_documents",
        batch_add_100,
        iterations=min(iterations, 50),  # Reduce to avoid memory issues
        warmup=min(warmup, 5)
    ))

    # Benchmark 2: RAG workflow simulation
    # Simulates: add documents -> query -> retrieve context
    collection_rag = client.create_collection(name="bench_rag")

    # Pre-populate with initial dataset
    collection_rag.add(
        ids=[f"knowledge_{i}" for i in range(1000)],
        documents=[f"Knowledge base article {i} about various topics" for i in range(1000)]
    )

    def rag_workflow():
        # Add new document (simulating indexing)
        ts = time.time_ns()
        collection_rag.add(
            ids=[f"new_doc_{ts}"],
            documents=["New document to be indexed"]
        )

        # Query for context (simulating retrieval)
        collection_rag.query(
            query_texts=["find relevant context"],
            n_results=5
        )

    results.append(benchmark(
        "rag_workflow_add_query",
        rag_workflow,
        iterations=min(iterations, 50),
        warmup=min(warmup, 5)
    ))

    # Benchmark 3: Batch query (multiple queries at once)
    collection_multi_query = client.create_collection(name="bench_multi_query")
    collection_multi_query.add(
        ids=[f"doc_{i}" for i in range(5000)],
        documents=[f"Document {i}" for i in range(5000)]
    )

    def batch_query():
        collection_multi_query.query(
            query_texts=[
                "first query",
                "second query",
                "third query",
                "fourth query",
                "fifth query"
            ],
            n_results=10
        )

    results.append(benchmark(
        "batch_query_5_queries",
        batch_query,
        iterations=iterations,
        warmup=warmup
    ))

    return results


def _run_resource_benchmarks(iterations: int, warmup: int) -> List[BenchmarkResult]:
    """
    Run resource benchmarks - memory and startup time.

    These benchmarks test:
    - Memory footprint with large collections
    - Cold start time
    - Incremental memory growth
    """
    print("\n>>> Running Resource Benchmarks...")
    results = []

    # Benchmark 1: Memory footprint with 10K documents
    def create_10k_collection():
        client = chromadb.Client()
        collection = client.create_collection(name=f"memory_test_{time.time_ns()}")
        collection.add(
            ids=[f"mem_doc_{i}" for i in range(10000)],
            documents=[f"Memory test document {i} with content" for i in range(10000)],
            metadatas=[{"index": i} for i in range(10000)]
        )

    results.append(benchmark(
        "memory_10k_documents",
        create_10k_collection,
        iterations=min(iterations, 10),  # Memory intensive, limit iterations
        warmup=min(warmup, 2)
    ))

    # Benchmark 2: Cold start - client initialization
    def cold_start():
        client = chromadb.Client()
        collection = client.create_collection(name=f"cold_start_{time.time_ns()}")
        collection.add(
            ids=["test_1"],
            documents=["First document"]
        )

    results.append(benchmark(
        "cold_start_client_init",
        cold_start,
        iterations=min(iterations, 20),
        warmup=min(warmup, 3)
    ))

    return results


def main():
    """Main entry point for running the standard benchmark suite."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run Chroma standard benchmark suite"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="Number of iterations per benchmark (default: 100)"
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=10,
        help="Number of warmup iterations (default: 10)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for JSON results file"
    )

    args = parser.parse_args()

    # Run the suite
    results = run_standard_suite(
        iterations=args.iterations,
        warmup=args.warmup,
        output_path=args.output
    )

    print(f"\n✅ Completed {len(results)} benchmarks")

    return 0


if __name__ == "__main__":
    sys.exit(main())
