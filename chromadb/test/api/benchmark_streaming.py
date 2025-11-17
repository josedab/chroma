"""Benchmark script for comparing regular query vs streaming query performance.

This benchmark measures:
- Peak memory usage
- Total latency
- Time to first result

Run with: python -m pytest chromadb/test/api/benchmark_streaming.py -v -s
"""

import tracemalloc
import time
import chromadb
import pytest
from chromadb.api import ClientAPI


def benchmark_regular_query(collection, n_results: int = 10000):
    """Benchmark regular query method."""
    tracemalloc.start()
    start = time.time()

    results = collection.query(
        query_texts=["test"],
        n_results=n_results,
        include=["documents", "metadatas", "embeddings", "distances"]
    )

    peak_memory = tracemalloc.get_traced_memory()[1]
    latency = time.time() - start
    tracemalloc.stop()

    return {
        'method': 'regular_query',
        'n_results': n_results,
        'peak_memory_mb': peak_memory / 1024 / 1024,
        'latency_s': latency,
        'time_to_first_result': latency,  # Same as latency for regular query
        'total_results': len(results['ids'][0]),
    }


def benchmark_streaming_query(collection, n_results: int = 10000, batch_size: int = 100):
    """Benchmark streaming query method."""
    tracemalloc.start()
    start = time.time()
    first_result_time = None
    total_results = 0

    for batch in collection.query_stream(
        query_texts=["test"],
        n_results=n_results,
        batch_size=batch_size,
        include=["documents", "metadatas", "embeddings", "distances"]
    ):
        if first_result_time is None:
            first_result_time = time.time() - start
        total_results += len(batch['ids'])

    peak_memory = tracemalloc.get_traced_memory()[1]
    total_latency = time.time() - start
    tracemalloc.stop()

    return {
        'method': 'streaming_query',
        'n_results': n_results,
        'batch_size': batch_size,
        'peak_memory_mb': peak_memory / 1024 / 1024,
        'latency_s': total_latency,
        'time_to_first_result': first_result_time,
        'total_results': total_results,
    }


def benchmark_streaming_query_early_stop(collection, n_results: int = 10000, batch_size: int = 100, stop_after: int = 100):
    """Benchmark streaming query with early stopping."""
    tracemalloc.start()
    start = time.time()
    first_result_time = None
    total_results = 0
    batches_consumed = 0

    for batch in collection.query_stream(
        query_texts=["test"],
        n_results=n_results,
        batch_size=batch_size,
        include=["documents", "metadatas", "embeddings", "distances"]
    ):
        if first_result_time is None:
            first_result_time = time.time() - start
        total_results += len(batch['ids'])
        batches_consumed += 1

        if total_results >= stop_after:
            break

    peak_memory = tracemalloc.get_traced_memory()[1]
    total_latency = time.time() - start
    tracemalloc.stop()

    return {
        'method': 'streaming_query_early_stop',
        'n_results': n_results,
        'batch_size': batch_size,
        'stop_after': stop_after,
        'batches_consumed': batches_consumed,
        'peak_memory_mb': peak_memory / 1024 / 1024,
        'latency_s': total_latency,
        'time_to_first_result': first_result_time,
        'total_results': total_results,
    }


@pytest.mark.benchmark
def test_benchmark_comparison(client: ClientAPI):
    """Compare regular query vs streaming query performance."""
    client.reset()
    collection = client.create_collection("benchmark_collection")

    # Add test data (10K documents)
    n_documents = 10000
    print(f"\nAdding {n_documents} documents to collection...")

    # Add in batches to avoid memory issues during setup
    batch_size = 1000
    for i in range(0, n_documents, batch_size):
        end_idx = min(i + batch_size, n_documents)
        collection.add(
            ids=[str(j) for j in range(i, end_idx)],
            embeddings=[[float(j % 384), float((j + 1) % 384), float((j + 2) % 384)] for j in range(i, end_idx)],
            documents=[f"document {j}" for j in range(i, end_idx)],
            metadatas=[{"index": j} for j in range(i, end_idx)],
        )

    print(f"Collection has {collection.count()} documents\n")

    # Benchmark 1: Regular query with 1000 results
    print("=" * 80)
    print("Benchmark 1: Regular query (n_results=1000)")
    print("=" * 80)
    regular_1k = benchmark_regular_query(collection, n_results=1000)
    print(f"Peak memory: {regular_1k['peak_memory_mb']:.2f} MB")
    print(f"Total latency: {regular_1k['latency_s']:.3f} s")
    print(f"Time to first result: {regular_1k['time_to_first_result']:.3f} s")
    print(f"Total results: {regular_1k['total_results']}\n")

    # Benchmark 2: Streaming query with 1000 results, batch_size=100
    print("=" * 80)
    print("Benchmark 2: Streaming query (n_results=1000, batch_size=100)")
    print("=" * 80)
    streaming_1k = benchmark_streaming_query(collection, n_results=1000, batch_size=100)
    print(f"Peak memory: {streaming_1k['peak_memory_mb']:.2f} MB")
    print(f"Total latency: {streaming_1k['latency_s']:.3f} s")
    print(f"Time to first result: {streaming_1k['time_to_first_result']:.3f} s")
    print(f"Total results: {streaming_1k['total_results']}\n")

    # Benchmark 3: Streaming query with early stop
    print("=" * 80)
    print("Benchmark 3: Streaming query with early stop (fetch 100 of 1000)")
    print("=" * 80)
    streaming_early = benchmark_streaming_query_early_stop(
        collection,
        n_results=1000,
        batch_size=100,
        stop_after=100
    )
    print(f"Peak memory: {streaming_early['peak_memory_mb']:.2f} MB")
    print(f"Total latency: {streaming_early['latency_s']:.3f} s")
    print(f"Time to first result: {streaming_early['time_to_first_result']:.3f} s")
    print(f"Total results: {streaming_early['total_results']}")
    print(f"Batches consumed: {streaming_early['batches_consumed']}\n")

    # Calculate improvements
    print("=" * 80)
    print("Performance Comparison Summary")
    print("=" * 80)

    if regular_1k['peak_memory_mb'] > 0:
        memory_reduction = (1 - streaming_1k['peak_memory_mb'] / regular_1k['peak_memory_mb']) * 100
        print(f"Memory reduction (streaming vs regular): {memory_reduction:.1f}%")

    if regular_1k['time_to_first_result'] > 0:
        ttfr_improvement = (1 - streaming_1k['time_to_first_result'] / regular_1k['time_to_first_result']) * 100
        print(f"Time-to-first-result improvement: {ttfr_improvement:.1f}%")

    print(f"\nEarly stop demonstration:")
    print(f"  - Only fetched {streaming_early['total_results']} results instead of 1000")
    print(f"  - Memory used: {streaming_early['peak_memory_mb']:.2f} MB")
    print(f"  - Time: {streaming_early['latency_s']:.3f} s")
    print("=" * 80)


@pytest.mark.benchmark
def test_benchmark_batch_sizes(client: ClientAPI):
    """Compare different batch sizes for streaming."""
    client.reset()
    collection = client.create_collection("benchmark_batch_sizes")

    # Add test data
    n_documents = 5000
    print(f"\nAdding {n_documents} documents to collection...")

    batch_size = 1000
    for i in range(0, n_documents, batch_size):
        end_idx = min(i + batch_size, n_documents)
        collection.add(
            ids=[str(j) for j in range(i, end_idx)],
            embeddings=[[float(j % 384), float((j + 1) % 384), float((j + 2) % 384)] for j in range(i, end_idx)],
            documents=[f"document {j}" for j in range(i, end_idx)],
        )

    print(f"Collection has {collection.count()} documents\n")

    batch_sizes = [10, 50, 100, 500, 1000]
    results = []

    print("=" * 80)
    print("Testing different batch sizes")
    print("=" * 80)

    for batch_size in batch_sizes:
        result = benchmark_streaming_query(collection, n_results=1000, batch_size=batch_size)
        results.append(result)
        print(f"Batch size {batch_size:4d}: "
              f"Memory={result['peak_memory_mb']:6.2f} MB, "
              f"Latency={result['latency_s']:6.3f} s, "
              f"TTFR={result['time_to_first_result']:6.3f} s")

    print("=" * 80)


if __name__ == "__main__":
    # For manual testing
    import chromadb
    client = chromadb.Client()
    test_benchmark_comparison(client)
    test_benchmark_batch_sizes(client)
