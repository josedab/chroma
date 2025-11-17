# RFC-0009: Benchmark Suite & Performance Regression Testing

**Status:** Draft
**Author:** Claude Code Analysis
**Created:** 2025-11-17
**Commit Base:** 091f8bd5c553f8267c48664e98fb32215055f58e

---

## Summary

Establish a comprehensive benchmark suite with automated performance regression testing to track query latency, throughput, and resource utilization across releases. Integrate with CI/CD to catch performance degradations before production.

---

## Motivation

### Current State

Limited benchmarking:

**File:** `/home/user/chroma/sample_apps/generative_benchmarking/`

Some ad-hoc benchmarking exists, but:
- No automated CI integration
- No historical tracking
- No regression detection
- No standardized workloads

### Problems

1. **Performance Regressions Undetected:** Code changes can slow queries without notice
2. **No Baseline:** Can't quantify "is this fast enough?"
3. **No Trend Analysis:** Don't know if performance improving or degrading over time
4. **Manual Testing:** Requires developer to remember to benchmark

### User Impact

- Performance bugs reach production
- No confidence in performance claims
- Hard to justify optimizations without data

---

## Detailed Design

### Benchmark Categories

#### 1. Micro Benchmarks
**Purpose:** Test individual operations in isolation

```python
def benchmark_add_latency():
    """Measure latency of adding single document"""
    # Add 1 document, measure time
    
def benchmark_query_latency():
    """Measure query latency (warm cache)"""
    # Query with 10 results, measure time

def benchmark_embedding_function():
    """Measure embedding generation time"""
    # Generate embedding for 100-char text
```

#### 2. Macro Benchmarks
**Purpose:** Test realistic workloads

```python
def benchmark_rag_workflow():
    """Simulate full RAG pipeline"""
    # 1. Index 10K documents
    # 2. Run 100 queries
    # 3. Measure end-to-end latency

def benchmark_high_throughput():
    """Test concurrent load"""
    # 100 concurrent clients
    # Each runs 10 queries
    # Measure throughput (QPS)
```

#### 3. Resource Benchmarks
**Purpose:** Track memory, CPU, disk usage

```python
def benchmark_memory_footprint():
    """Measure memory for 1M documents"""
    # Add 1M documents
    # Track RSS, heap size

def benchmark_cold_start():
    """Measure startup time"""
    # Start server, measure time to first query
```

### Benchmark Framework

**File:** Create `benchmarks/framework.py`

```python
import time
import tracemalloc
import statistics
from dataclasses import dataclass
from typing import Callable, List
import chromadb

@dataclass
class BenchmarkResult:
    name: str
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    throughput_qps: float
    memory_mb: float

def benchmark(
    name: str,
    func: Callable,
    iterations: int = 100,
    warmup: int = 10
) -> BenchmarkResult:
    """
    Run benchmark and collect metrics.
    
    Args:
        name: Benchmark name
        func: Function to benchmark
        iterations: Number of iterations
        warmup: Warmup iterations (not counted)
    
    Returns:
        BenchmarkResult with statistics
    """
    # Warmup
    for _ in range(warmup):
        func()
    
    # Measure
    tracemalloc.start()
    latencies = []
    
    start = time.time()
    for _ in range(iterations):
        iter_start = time.time()
        func()
        latencies.append((time.time() - iter_start) * 1000)  # ms
    
    total_time = time.time() - start
    peak_memory = tracemalloc.get_traced_memory()[1] / 1024 / 1024  # MB
    tracemalloc.stop()
    
    # Compute statistics
    latencies.sort()
    return BenchmarkResult(
        name=name,
        mean_ms=statistics.mean(latencies),
        p50_ms=latencies[len(latencies) // 2],
        p95_ms=latencies[int(len(latencies) * 0.95)],
        p99_ms=latencies[int(len(latencies) * 0.99)],
        throughput_qps=iterations / total_time,
        memory_mb=peak_memory,
    )

def compare_results(
    baseline: BenchmarkResult,
    current: BenchmarkResult,
    threshold: float = 0.10  # 10% regression threshold
) -> bool:
    """
    Compare current results to baseline.
    
    Returns:
        True if no regression, False if regression detected
    """
    regression_pct = (current.p95_ms - baseline.p95_ms) / baseline.p95_ms
    
    if regression_pct > threshold:
        print(f"REGRESSION: {current.name} p95 increased by {regression_pct*100:.1f}%")
        return False
    
    return True
```

### Standard Benchmark Suite

**File:** Create `benchmarks/standard_suite.py`

```python
def run_standard_suite() -> List[BenchmarkResult]:
    """Run all standard benchmarks"""
    results = []
    
    client = chromadb.Client()
    collection = client.create_collection("bench")
    
    # Benchmark 1: Add latency
    def add_single():
        collection.add(
            ids=[f"id_{time.time()}"],
            documents=["Sample document for benchmarking"],
            metadatas=[{"key": "value"}]
        )
    
    results.append(benchmark("add_single_document", add_single))
    
    # Benchmark 2: Query latency (10 results)
    # Prepopulate collection
    collection.add(
        ids=[f"doc_{i}" for i in range(10000)],
        documents=[f"Document {i}" for i in range(10000)]
    )
    
    def query_10_results():
        collection.query(
            query_texts=["sample query"],
            n_results=10
        )
    
    results.append(benchmark("query_10_results", query_10_results))
    
    # Benchmark 3: Query latency (100 results)
    def query_100_results():
        collection.query(
            query_texts=["sample query"],
            n_results=100
        )
    
    results.append(benchmark("query_100_results", query_100_results))
    
    return results
```

### CI Integration

**File:** `.github/workflows/benchmark.yml`

```yaml
name: Performance Benchmarks

on:
  push:
    branches: [main]
  pull_request:

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -e .[dev]
      
      - name: Download baseline results
        run: |
          # Download from S3 or GitHub artifacts
          aws s3 cp s3://chroma-benchmarks/baseline.json baseline.json
      
      - name: Run benchmarks
        run: python benchmarks/standard_suite.py > current.json
      
      - name: Compare to baseline
        run: |
          python benchmarks/compare.py baseline.json current.json
          # Fails if regression detected
      
      - name: Upload results
        if: github.ref == 'refs/heads/main'
        run: |
          # Upload to S3 for historical tracking
          aws s3 cp current.json s3://chroma-benchmarks/$(date +%Y%m%d).json
          
      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const results = JSON.parse(fs.readFileSync('comparison.json'));
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              body: `## Benchmark Results\n\n${results.summary}`
            });
```

---

## Implementation Plan

### Milestone 1: Framework (2 dev-days)
- [ ] Implement `benchmark()` function
- [ ] Add result comparison logic
- [ ] JSON serialization
- [ ] Basic reporting

### Milestone 2: Standard Suite (3 dev-days)
- [ ] Define 10+ standard benchmarks
- [ ] Add micro benchmarks (add, query, delete)
- [ ] Add macro benchmarks (RAG workflow)
- [ ] Add resource benchmarks (memory, startup)

### Milestone 3: CI Integration (1 dev-day)
- [ ] GitHub Actions workflow
- [ ] Baseline storage (S3 or artifacts)
- [ ] Regression detection
- [ ] PR comments with results

### Milestone 4: Visualization (1 dev-day)
- [ ] Historical trend dashboard
- [ ] Grafana integration
- [ ] Regression alerts
- [ ] Public benchmarks page

---

## Example Usage

### Running Benchmarks Locally

```bash
# Run standard suite
python benchmarks/standard_suite.py

# Output:
# Benchmark Results
# =================
# add_single_document:
#   Mean: 12.3ms
#   P95: 18.5ms
#   P99: 24.1ms
#   Throughput: 81.3 QPS
#
# query_10_results:
#   Mean: 8.7ms
#   P95: 12.1ms
#   P99: 15.8ms
#   Throughput: 114.9 QPS
```

### Compare to Baseline

```bash
# Compare current to main branch
python benchmarks/compare.py \
  --baseline s3://chroma-benchmarks/main-latest.json \
  --current ./current.json

# Output:
# Comparison Results
# ==================
# ✅ add_single_document: 12.3ms (baseline: 11.8ms) +4.2%
# ❌ query_10_results: 15.2ms (baseline: 8.7ms) +74.7% REGRESSION!
# ✅ query_100_results: 45.1ms (baseline: 43.2ms) +4.4%
```

---

## Backwards Compatibility

Not applicable - purely additive tooling.

---

## Success Criteria

- [ ] 10+ standard benchmarks defined
- [ ] CI runs benchmarks on every PR
- [ ] Regressions detected automatically
- [ ] Historical data tracked

---

## Effort Estimation

| Phase | Dev-Days |
|-------|----------|
| Framework | 2 |
| Standard suite | 3 |
| CI integration | 1 |
| Visualization | 1 |
| **Total** | **7** |

---

## References

- [Google Benchmark](https://github.com/google/benchmark)
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/)
- [Criterion.rs](https://github.com/bheisler/criterion.rs)

---

## Revision History

- **v1.0** (2025-11-17): Initial RFC
