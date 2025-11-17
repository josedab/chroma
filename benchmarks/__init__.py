"""
Chroma Benchmark Suite

A comprehensive performance testing framework for Chroma, including:
- Micro benchmarks for individual operations
- Macro benchmarks for realistic workflows
- Resource benchmarks for memory and startup time
- Automated regression detection

Usage:
    # Run standard benchmark suite
    python -m benchmarks.standard_suite

    # Compare results
    python -m benchmarks.compare baseline.json current.json

    # Programmatic usage
    from benchmarks.framework import benchmark, BenchmarkResult
    from benchmarks.standard_suite import run_standard_suite

    results = run_standard_suite(iterations=50)
"""

from .framework import (
    BenchmarkResult,
    benchmark,
    compare_results,
    save_results,
    load_results,
    print_results,
)

__all__ = [
    "BenchmarkResult",
    "benchmark",
    "compare_results",
    "save_results",
    "load_results",
    "print_results",
]

__version__ = "1.0.0"
