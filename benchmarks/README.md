# Chroma Benchmark Suite

A comprehensive performance testing framework for tracking query latency, throughput, and resource utilization across Chroma releases.

## Overview

This benchmark suite provides:

- **Micro Benchmarks**: Individual operations (add, query, delete) tested in isolation
- **Macro Benchmarks**: Realistic workflows (RAG pipeline, batch operations)
- **Resource Benchmarks**: Memory footprint and startup time measurements
- **Automated Regression Detection**: CI integration to catch performance degradations
- **Historical Tracking**: Baseline comparison and trend analysis

## Quick Start

### Run Standard Benchmark Suite

```bash
# Run with default settings (100 iterations, 10 warmup)
python benchmarks/standard_suite.py

# Run with custom iterations
python benchmarks/standard_suite.py --iterations 50 --warmup 5

# Save results to file
python benchmarks/standard_suite.py --output results/my-results.json
```

### Compare Results

```bash
# Compare current results against baseline
python benchmarks/compare.py baseline.json current.json

# Set custom regression threshold (20% instead of default 10%)
python benchmarks/compare.py baseline.json current.json --threshold 0.20

# Generate detailed comparison report
python benchmarks/compare.py baseline.json current.json --report comparison.json
```

## Benchmark Categories

### Micro Benchmarks

Test individual operations in isolation:

- `add_single_document`: Latency of adding a single document
- `query_10_results`: Query latency for 10 results
- `query_100_results`: Query latency for 100 results
- `get_by_id_10_docs`: Get documents by ID
- `delete_10_documents`: Delete operation latency

### Macro Benchmarks

Test realistic workflows:

- `batch_add_100_documents`: Batch add 100 documents at once
- `rag_workflow_add_query`: Simulate full RAG pipeline (add + query)
- `batch_query_5_queries`: Multiple queries in one call

### Resource Benchmarks

Track memory and startup performance:

- `memory_10k_documents`: Memory footprint with 10K documents
- `cold_start_client_init`: Client initialization time

## Understanding Results

Benchmark results include the following metrics:

```
add_single_document:
  Mean:       12.34ms    # Average latency
  P50:        11.20ms    # Median (50th percentile)
  P95:        18.50ms    # 95th percentile - key metric for SLAs
  P99:        24.10ms    # 99th percentile - worst case scenarios
  Throughput: 81.30 QPS  # Queries per second
  Memory:     45.20 MB   # Peak memory usage during test
  Iterations: 100        # Number of iterations performed
```

**Key Metrics:**

- **P95 Latency**: The primary metric for regression detection. 95% of requests complete within this time.
- **Throughput (QPS)**: Queries per second - higher is better
- **Memory**: Peak memory usage - lower is better

## CI Integration

The benchmark suite automatically runs on:

- **Pull Requests**: Compares PR performance against main branch baseline
- **Main Branch**: Updates baseline results for future comparisons
- **Manual Trigger**: Can be triggered via GitHub Actions

### How It Works

1. **On PR**: Runs benchmarks and compares against baseline
2. **Regression Detection**: Fails if P95 latency increases >15%
3. **PR Comment**: Posts detailed results as PR comment
4. **Baseline Update**: Main branch runs update the baseline

### Interpreting CI Results

PR comments show:

- ✅ **Improvements**: Benchmarks that got faster
- ⚠️ **Warnings**: Slight slowdowns within threshold
- ❌ **Regressions**: Slowdowns exceeding threshold (causes failure)
- 📊 **New**: New benchmarks without baseline

## Writing Custom Benchmarks

### Basic Example

```python
from benchmarks.framework import benchmark

def my_operation():
    # Your code to benchmark
    collection.add(ids=["test"], documents=["test doc"])

result = benchmark(
    name="my_custom_benchmark",
    func=my_operation,
    iterations=100,
    warmup=10
)

print(result)
```

### Advanced Example

```python
from benchmarks.framework import benchmark, BenchmarkResult, save_results
from pathlib import Path

# Setup
client = chromadb.Client()
collection = client.create_collection("test")

# Benchmark multiple operations
results = []

def test_add():
    collection.add(ids=["id1"], documents=["doc"])

def test_query():
    collection.query(query_texts=["query"], n_results=5)

results.append(benchmark("custom_add", test_add))
results.append(benchmark("custom_query", test_query))

# Save results
save_results(results, Path("custom_results.json"))
```

## File Structure

```
benchmarks/
├── __init__.py           # Package initialization
├── README.md             # This file
├── framework.py          # Core benchmark infrastructure
├── standard_suite.py     # Standard benchmark suite
├── compare.py            # Comparison and regression detection
└── results/              # Benchmark results (gitignored)
    ├── latest.json       # Latest main branch results
    └── *.json            # Historical results
```

## Best Practices

### Running Benchmarks

1. **Close other applications**: Minimize background processes
2. **Stable environment**: Run on dedicated hardware when possible
3. **Multiple runs**: Run at least 100 iterations for statistical significance
4. **Warmup**: Always include warmup iterations (10+) to account for JIT compilation

### Interpreting Results

1. **Focus on P95**: More stable than mean, represents user experience
2. **Watch trends**: Single runs vary, track trends over time
3. **Statistical significance**: Small changes (<5%) may be noise
4. **Understand context**: Some regressions may be acceptable tradeoffs

### CI Thresholds

Current regression threshold: **15%** increase in P95 latency

- Chosen to balance sensitivity vs. noise
- Can be adjusted per benchmark if needed
- Configurable via `--threshold` flag

## Troubleshooting

### Benchmarks are slow

- Reduce `--iterations` (e.g., 50 instead of 100)
- Reduce `--warmup` (e.g., 5 instead of 10)
- Run subset of benchmarks by modifying `standard_suite.py`

### High variance in results

- Increase iterations for more stable statistics
- Check for background processes consuming resources
- Consider running on more powerful hardware

### CI baseline not found

- First run on main branch will establish baseline
- Baseline stored as GitHub artifact (90 day retention)
- Can manually create baseline by running locally and committing

## Future Enhancements

Planned improvements:

- [ ] Historical trend visualization (Grafana integration)
- [ ] Per-benchmark custom thresholds
- [ ] Distributed benchmarking (test cluster performance)
- [ ] Long-running stress tests
- [ ] Comparison against previous releases
- [ ] Public benchmark dashboard

## References

- [RFC-0009: Benchmark Suite](../analysis-output/rfcs/RFC-0009-benchmark-suite.md)
- [Google Benchmark](https://github.com/google/benchmark)
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/)
- [Criterion.rs](https://github.com/bheisler/criterion.rs)

## Contributing

To add new benchmarks:

1. Add benchmark function to `standard_suite.py` in appropriate category
2. Follow naming convention: `benchmark_<operation>_<variation>`
3. Document expected performance characteristics
4. Run locally and verify results make sense
5. Update this README if adding new category

## Support

For questions or issues with the benchmark suite:

- File an issue on GitHub
- Tag with `performance` label
- Include benchmark results and environment details
