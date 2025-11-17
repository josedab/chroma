"""
Unit tests for the benchmark framework.

These tests verify the core benchmark logic without requiring chromadb.
Run with: python -m pytest benchmarks/test_framework.py
"""

import time
import tempfile
from pathlib import Path

from framework import (
    BenchmarkResult,
    benchmark,
    compare_results,
    save_results,
    load_results,
)


def test_benchmark_result_creation():
    """Test BenchmarkResult can be created and serialized."""
    result = BenchmarkResult(
        name="test_benchmark",
        mean_ms=10.5,
        p50_ms=10.0,
        p95_ms=15.0,
        p99_ms=20.0,
        throughput_qps=95.2,
        memory_mb=100.0,
        iterations=100
    )

    assert result.name == "test_benchmark"
    assert result.mean_ms == 10.5
    assert result.p95_ms == 15.0

    # Test serialization
    result_dict = result.to_dict()
    assert result_dict["name"] == "test_benchmark"
    assert result_dict["p95_ms"] == 15.0

    # Test JSON round-trip
    json_str = result.to_json()
    result2 = BenchmarkResult.from_json(json_str)
    assert result2.name == result.name
    assert result2.p95_ms == result.p95_ms


def test_benchmark_function():
    """Test benchmark() function with a simple operation."""
    call_count = [0]

    def simple_operation():
        call_count[0] += 1
        time.sleep(0.001)  # 1ms sleep

    result = benchmark(
        name="test_op",
        func=simple_operation,
        iterations=10,
        warmup=2
    )

    # Verify warmup + iterations were called
    assert call_count[0] == 12  # 2 warmup + 10 iterations

    # Verify result structure
    assert result.name == "test_op"
    assert result.iterations == 10
    assert result.mean_ms > 0
    assert result.p50_ms > 0
    assert result.p95_ms > 0
    assert result.p99_ms > 0
    assert result.throughput_qps > 0
    assert result.memory_mb >= 0

    # Verify latency is roughly what we expect (1ms sleep)
    # With some tolerance for overhead
    assert 0.5 < result.mean_ms < 10.0


def test_compare_results_no_regression():
    """Test compare_results when there's no regression."""
    baseline = BenchmarkResult(
        name="test",
        mean_ms=10.0,
        p50_ms=10.0,
        p95_ms=15.0,
        p99_ms=20.0,
        throughput_qps=100.0,
        memory_mb=50.0,
        iterations=100
    )

    # Current is 5% slower (within 10% threshold)
    current = BenchmarkResult(
        name="test",
        mean_ms=10.5,
        p50_ms=10.5,
        p95_ms=15.75,  # 5% increase
        p99_ms=21.0,
        throughput_qps=95.0,
        memory_mb=52.0,
        iterations=100
    )

    result = compare_results(baseline, current, threshold=0.10)
    assert result is True  # No regression (within threshold)


def test_compare_results_with_regression():
    """Test compare_results when there IS a regression."""
    baseline = BenchmarkResult(
        name="test",
        mean_ms=10.0,
        p50_ms=10.0,
        p95_ms=15.0,
        p99_ms=20.0,
        throughput_qps=100.0,
        memory_mb=50.0,
        iterations=100
    )

    # Current is 20% slower (exceeds 10% threshold)
    current = BenchmarkResult(
        name="test",
        mean_ms=12.0,
        p50_ms=12.0,
        p95_ms=18.0,  # 20% increase
        p99_ms=24.0,
        throughput_qps=83.0,
        memory_mb=60.0,
        iterations=100
    )

    result = compare_results(baseline, current, threshold=0.10)
    assert result is False  # Regression detected


def test_compare_results_improvement():
    """Test compare_results when performance improves."""
    baseline = BenchmarkResult(
        name="test",
        mean_ms=10.0,
        p50_ms=10.0,
        p95_ms=15.0,
        p99_ms=20.0,
        throughput_qps=100.0,
        memory_mb=50.0,
        iterations=100
    )

    # Current is faster
    current = BenchmarkResult(
        name="test",
        mean_ms=8.0,
        p50_ms=8.0,
        p95_ms=12.0,  # 20% improvement
        p99_ms=16.0,
        throughput_qps=125.0,
        memory_mb=45.0,
        iterations=100
    )

    result = compare_results(baseline, current, threshold=0.10)
    assert result is True  # Improvement is good!


def test_save_and_load_results():
    """Test saving and loading results to/from JSON."""
    results = [
        BenchmarkResult(
            name="test1",
            mean_ms=10.0,
            p50_ms=10.0,
            p95_ms=15.0,
            p99_ms=20.0,
            throughput_qps=100.0,
            memory_mb=50.0,
            iterations=100
        ),
        BenchmarkResult(
            name="test2",
            mean_ms=5.0,
            p50_ms=5.0,
            p95_ms=7.5,
            p99_ms=10.0,
            throughput_qps=200.0,
            memory_mb=25.0,
            iterations=100
        ),
    ]

    # Save to temporary file
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_results.json"
        save_results(results, output_path)

        # Verify file exists
        assert output_path.exists()

        # Load back
        loaded = load_results(output_path)

        # Verify loaded results match
        assert len(loaded) == 2
        assert loaded[0].name == "test1"
        assert loaded[0].p95_ms == 15.0
        assert loaded[1].name == "test2"
        assert loaded[1].p95_ms == 7.5


def test_percentile_calculation():
    """Test that percentile calculations work correctly."""
    # Create a predictable operation
    values = list(range(100))  # 0-99
    counter = [0]

    def predictable_op():
        # Return values in sequence
        time.sleep(values[counter[0]] / 100000.0)  # Small delays
        counter[0] += 1

    result = benchmark(
        name="percentile_test",
        func=predictable_op,
        iterations=100,
        warmup=0
    )

    # With 100 iterations:
    # P50 should be around the median
    # P95 should be around the 95th value
    # P99 should be around the 99th value
    # Just verify they're in increasing order
    assert result.p50_ms < result.p95_ms
    assert result.p95_ms < result.p99_ms


if __name__ == "__main__":
    # Run tests manually
    print("Running framework tests...")

    test_benchmark_result_creation()
    print("✅ test_benchmark_result_creation passed")

    test_benchmark_function()
    print("✅ test_benchmark_function passed")

    test_compare_results_no_regression()
    print("✅ test_compare_results_no_regression passed")

    test_compare_results_with_regression()
    print("✅ test_compare_results_with_regression passed")

    test_compare_results_improvement()
    print("✅ test_compare_results_improvement passed")

    test_save_and_load_results()
    print("✅ test_save_and_load_results passed")

    test_percentile_calculation()
    print("✅ test_percentile_calculation passed")

    print("\n✅ All tests passed!")
