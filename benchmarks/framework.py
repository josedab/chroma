"""
Benchmark framework for Chroma performance testing.

This module provides the core infrastructure for running and analyzing benchmarks,
including result collection, statistical analysis, and regression detection.
"""

import time
import tracemalloc
import statistics
import json
from dataclasses import dataclass, asdict
from typing import Callable, List, Optional, Dict, Any
from pathlib import Path


@dataclass
class BenchmarkResult:
    """
    Results from a benchmark run.

    Attributes:
        name: Benchmark name
        mean_ms: Mean latency in milliseconds
        p50_ms: Median (50th percentile) latency in milliseconds
        p95_ms: 95th percentile latency in milliseconds
        p99_ms: 99th percentile latency in milliseconds
        throughput_qps: Throughput in queries per second
        memory_mb: Peak memory usage in megabytes
        iterations: Number of iterations performed
    """
    name: str
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    throughput_qps: float
    memory_mb: float
    iterations: int = 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert result to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BenchmarkResult":
        """Create BenchmarkResult from dictionary."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "BenchmarkResult":
        """Create BenchmarkResult from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def __str__(self) -> str:
        """Pretty print benchmark results."""
        return f"""
{self.name}:
  Mean:       {self.mean_ms:8.2f}ms
  P50:        {self.p50_ms:8.2f}ms
  P95:        {self.p95_ms:8.2f}ms
  P99:        {self.p99_ms:8.2f}ms
  Throughput: {self.throughput_qps:8.2f} QPS
  Memory:     {self.memory_mb:8.2f} MB
  Iterations: {self.iterations:8d}
"""


def benchmark(
    name: str,
    func: Callable,
    iterations: int = 100,
    warmup: int = 10
) -> BenchmarkResult:
    """
    Run benchmark and collect metrics.

    This function runs the provided callable multiple times, collecting
    latency and memory usage statistics. It includes a warmup phase to
    ensure stable measurements.

    Args:
        name: Benchmark name for identification
        func: Function to benchmark (should be a callable with no arguments)
        iterations: Number of iterations to run (default: 100)
        warmup: Number of warmup iterations (not counted in results, default: 10)

    Returns:
        BenchmarkResult with statistical analysis of the benchmark

    Example:
        >>> def my_operation():
        ...     # Some operation to benchmark
        ...     pass
        >>> result = benchmark("my_operation", my_operation, iterations=50)
        >>> print(result)
    """
    # Warmup phase - important for JIT compilation, cache warmup, etc.
    for _ in range(warmup):
        func()

    # Start memory tracking
    tracemalloc.start()
    latencies = []

    # Measure total time and individual iterations
    start = time.time()
    for _ in range(iterations):
        iter_start = time.time()
        func()
        iter_end = time.time()
        latencies.append((iter_end - iter_start) * 1000)  # Convert to ms

    total_time = time.time() - start

    # Get peak memory usage
    peak_memory = tracemalloc.get_traced_memory()[1] / 1024 / 1024  # Convert to MB
    tracemalloc.stop()

    # Compute statistics
    latencies.sort()

    def percentile(data: List[float], p: float) -> float:
        """Calculate percentile from sorted data."""
        k = (len(data) - 1) * p
        f = int(k)
        c = min(f + 1, len(data) - 1)
        if f == c:
            return data[f]
        return data[f] * (c - k) + data[c] * (k - f)

    return BenchmarkResult(
        name=name,
        mean_ms=statistics.mean(latencies),
        p50_ms=percentile(latencies, 0.50),
        p95_ms=percentile(latencies, 0.95),
        p99_ms=percentile(latencies, 0.99),
        throughput_qps=iterations / total_time,
        memory_mb=peak_memory,
        iterations=iterations,
    )


def compare_results(
    baseline: BenchmarkResult,
    current: BenchmarkResult,
    threshold: float = 0.10  # 10% regression threshold
) -> bool:
    """
    Compare current results to baseline and detect performance regressions.

    A regression is detected when the P95 latency increases by more than
    the threshold percentage.

    Args:
        baseline: Baseline benchmark result to compare against
        current: Current benchmark result to evaluate
        threshold: Maximum acceptable regression as a fraction (default: 0.10 for 10%)

    Returns:
        True if no regression detected, False if regression detected

    Example:
        >>> baseline = BenchmarkResult(name="test", mean_ms=10, p50_ms=10,
        ...                           p95_ms=15, p99_ms=20, throughput_qps=100,
        ...                           memory_mb=50, iterations=100)
        >>> current = BenchmarkResult(name="test", mean_ms=12, p50_ms=12,
        ...                          p95_ms=18, p99_ms=22, throughput_qps=90,
        ...                          memory_mb=52, iterations=100)
        >>> compare_results(baseline, current)  # Returns True or False
    """
    if baseline.name != current.name:
        print(f"WARNING: Comparing different benchmarks: {baseline.name} vs {current.name}")

    regression_pct = (current.p95_ms - baseline.p95_ms) / baseline.p95_ms

    if regression_pct > threshold:
        print(f"❌ REGRESSION: {current.name} p95 increased by {regression_pct*100:.1f}%")
        print(f"   Baseline: {baseline.p95_ms:.2f}ms → Current: {current.p95_ms:.2f}ms")
        return False

    if regression_pct > 0:
        print(f"⚠️  {current.name} p95 increased by {regression_pct*100:.1f}% (within threshold)")
    else:
        improvement_pct = abs(regression_pct)
        print(f"✅ {current.name} p95 improved by {improvement_pct*100:.1f}%")

    return True


def save_results(results: List[BenchmarkResult], output_path: Path) -> None:
    """
    Save benchmark results to a JSON file.

    Args:
        results: List of benchmark results to save
        output_path: Path to output file
    """
    data = {
        "timestamp": time.time(),
        "results": [r.to_dict() for r in results]
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Results saved to {output_path}")


def load_results(input_path: Path) -> List[BenchmarkResult]:
    """
    Load benchmark results from a JSON file.

    Args:
        input_path: Path to input file

    Returns:
        List of BenchmarkResult objects
    """
    with open(input_path, 'r') as f:
        data = json.load(f)

    return [BenchmarkResult.from_dict(r) for r in data["results"]]


def print_results(results: List[BenchmarkResult]) -> None:
    """
    Pretty print a list of benchmark results.

    Args:
        results: List of benchmark results to print
    """
    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS")
    print("=" * 70)

    for result in results:
        print(result)

    print("=" * 70)
