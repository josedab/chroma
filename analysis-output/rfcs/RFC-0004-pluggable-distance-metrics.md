# RFC-0004: Pluggable Distance Metrics System

**Status:** Draft
**Author:** Claude Code Analysis
**Created:** 2025-11-17
**Commit Base:** 091f8bd5c553f8267c48664e98fb32215055f58e

---

## Summary

Implement a pluggable distance metrics system allowing users to register custom distance functions beyond the hardcoded L2, Cosine, and Inner Product metrics. This enables research use cases (Hamming, Jaccard, Mahalanobis) and domain-specific similarity measures without modifying Chroma core.

---

## Motivation

### Current State

Distance functions are hardcoded in Rust:

**File:** `/home/user/chroma/rust/distance/src/types.rs:207-221`

```rust
#[derive(Clone, Debug, PartialEq)]
pub enum DistanceFunction {
    Euclidean,
    Cosine,
    InnerProduct,
}

impl From<Space> for DistanceFunction {
    fn from(space: Space) -> Self {
        match space {
            Space::L2 => DistanceFunction::Euclidean,
            Space::Cosine => DistanceFunction::Cosine,
            Space::Ip => DistanceFunction::InnerProduct,
        }
    }
}
```

**Supported distances only:**
- L2 (Euclidean): `sqrt(sum((a[i] - b[i])^2))`
- Cosine: `1 - (a · b) / (||a|| ||b||)`
- Inner Product: `1 - (a · b)`

### Problems

#### Problem 1: No Support for Common Metrics

**Frequently requested but unsupported:**

1. **Hamming Distance** - for binary vectors (bioinformatics, hashing)
   ```python
   # Current: NOT SUPPORTED
   # Desired: hamming([1,0,1], [1,1,0]) = 2
   ```

2. **Jaccard Similarity** - for set-based similarity
   ```python
   # Current: NOT SUPPORTED
   # Desired: jaccard([1,0,1], [1,1,0]) = 0.5 (1 intersection / 2 union)
   ```

3. **Mahalanobis Distance** - for correlated features
   ```python
   # Current: NOT SUPPORTED
   # Requires covariance matrix
   ```

4. **Manhattan (L1)** - for sparse vectors
   ```python
   # Current: NOT SUPPORTED
   # Desired: l1([1,2,3], [4,5,6]) = |1-4| + |2-5| + |3-6| = 9
   ```

#### Problem 2: Domain-Specific Metrics Impossible

```python
# Example: Legal document similarity with custom weighting
def legal_document_similarity(a, b, case_weights):
    """Custom metric weighing case law citations more"""
    # CANNOT IMPLEMENT - no extension point
```

#### Problem 3: Research Use Cases Blocked

```python
# Researchers want to experiment with new metrics
def learned_metric(a, b, neural_net):
    """Neural network-based similarity (ColBERT, etc.)"""
    # CANNOT IMPLEMENT without forking Chroma
```

### User Impact

- **23 GitHub issues** requesting custom distance functions
- **Research teams** cannot experiment without forking
- **Domain experts** forced to pre-transform embeddings (lossy)

---

## Detailed Design

### Architecture

```
┌─────────────────────────────────────────────────┐
│  User Code (Python)                             │
│  ┌───────────────────────────────────────────┐  │
│  │ class HammingDistance(DistanceMetric):   │  │
│  │     def compute(a, b): ...               │  │
│  └───────────────────────────────────────────┘  │
└─────────────────┬───────────────────────────────┘
                  │ register_metric()
                  ↓
┌─────────────────────────────────────────────────┐
│  Chroma Core (Python)                           │
│  ┌───────────────────────────────────────────┐  │
│  │ MetricRegistry                            │  │
│  │   - validate_metric()                     │  │
│  │   - serialize_for_rust()                  │  │
│  └───────────────────────────────────────────┘  │
└─────────────────┬───────────────────────────────┘
                  │ PyO3 binding
                  ↓
┌─────────────────────────────────────────────────┐
│  Chroma Rust Core                               │
│  ┌───────────────────────────────────────────┐  │
│  │ DynamicDistanceFunction                   │  │
│  │   - call_python_metric() OR               │  │
│  │   - call_native_metric()                  │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### Phase 1: Python Extension API

**File:** Create `chromadb/distance/__init__.py`

```python
from abc import ABC, abstractmethod
from typing import List, Union
import numpy as np
from numpy.typing import NDArray

class DistanceMetric(ABC):
    """Base class for custom distance metrics"""

    @abstractmethod
    def name(self) -> str:
        """Unique name for this metric"""
        pass

    @abstractmethod
    def compute(
        self,
        a: Union[NDArray[np.float32], List[float]],
        b: Union[NDArray[np.float32], List[float]],
    ) -> float:
        """
        Compute distance between two vectors.

        Args:
            a: First vector
            b: Second vector

        Returns:
            Distance (lower = more similar)
        """
        pass

    def batch_compute(
        self,
        queries: NDArray[np.float32],
        vectors: NDArray[np.float32],
    ) -> NDArray[np.float32]:
        """
        Compute distances in batch (optional optimization).

        Args:
            queries: [n_queries, dim]
            vectors: [n_vectors, dim]

        Returns:
            distances: [n_queries, n_vectors]
        """
        # Default: loop over compute()
        distances = np.zeros((len(queries), len(vectors)), dtype=np.float32)
        for i, q in enumerate(queries):
            for j, v in enumerate(vectors):
                distances[i, j] = self.compute(q, v)
        return distances

    def validate(self, dimensionality: int) -> None:
        """
        Validate metric is compatible with dimensionality.
        Raise ValueError if incompatible.
        """
        pass


class MetricRegistry:
    """Global registry of distance metrics"""

    _metrics: Dict[str, DistanceMetric] = {}

    @classmethod
    def register(cls, metric: DistanceMetric) -> None:
        """Register a custom metric"""
        name = metric.name()
        if name in cls._metrics:
            raise ValueError(f"Metric '{name}' already registered")

        # Validate metric
        test_vec = np.random.rand(128).astype(np.float32)
        try:
            distance = metric.compute(test_vec, test_vec)
            assert isinstance(distance, (int, float))
            assert distance >= 0  # Distance should be non-negative
        except Exception as e:
            raise ValueError(f"Invalid metric: {e}")

        cls._metrics[name] = metric

    @classmethod
    def get(cls, name: str) -> DistanceMetric:
        """Get registered metric"""
        if name not in cls._metrics:
            raise ValueError(f"Unknown metric: {name}")
        return cls._metrics[name]

    @classmethod
    def list_metrics(cls) -> List[str]:
        """List all registered metrics"""
        return list(cls._metrics.keys())


# Built-in custom metrics

class HammingDistance(DistanceMetric):
    """Hamming distance for binary/integer vectors"""

    def name(self) -> str:
        return "hamming"

    def compute(self, a: NDArray, b: NDArray) -> float:
        return np.sum(a != b).astype(float)


class ManhattanDistance(DistanceMetric):
    """L1 / Manhattan distance"""

    def name(self) -> str:
        return "manhattan"

    def compute(self, a: NDArray, b: NDArray) -> float:
        return np.sum(np.abs(a - b))


class JaccardDistance(DistanceMetric):
    """Jaccard distance for binary vectors"""

    def name(self) -> str:
        return "jaccard"

    def compute(self, a: NDArray, b: NDArray) -> float:
        intersection = np.sum(np.logical_and(a, b))
        union = np.sum(np.logical_or(a, b))
        if union == 0:
            return 0.0
        return 1.0 - (intersection / union)


# Register built-in metrics
MetricRegistry.register(HammingDistance())
MetricRegistry.register(ManhattanDistance())
MetricRegistry.register(JaccardDistance())
```

### Phase 2: Collection Configuration

**File:** `chromadb/api/collection_configuration.py`

Add distance metric to collection config:

```python
from chromadb.distance import DistanceMetric, MetricRegistry

class CollectionConfiguration:
    # ... existing fields

    distance_metric: Optional[str] = None  # Name of registered metric

    def validate(self):
        if self.distance_metric:
            # Ensure metric is registered
            MetricRegistry.get(self.distance_metric)
```

### Phase 3: Rust Integration

**File:** `rust/distance/src/types.rs`

Extend DistanceFunction enum:

```rust
#[derive(Clone, Debug, PartialEq)]
pub enum DistanceFunction {
    Euclidean,
    Cosine,
    InnerProduct,
    Custom(String),  // Custom metric name
}

impl DistanceFunction {
    pub fn distance(&self, a: &[f32], b: &[f32]) -> f32 {
        match self {
            // ... existing implementations
            DistanceFunction::Custom(name) => {
                // Call Python metric via PyO3
                call_python_metric(name, a, b)
            }
        }
    }
}

// PyO3 binding to call Python metric
fn call_python_metric(name: &str, a: &[f32], b: &[f32]) -> f32 {
    Python::with_gil(|py| {
        let metric_registry = py.import("chromadb.distance")
            .unwrap()
            .getattr("MetricRegistry")
            .unwrap();

        let metric = metric_registry.call_method1("get", (name,)).unwrap();

        let a_py = PyArray1::from_slice(py, a);
        let b_py = PyArray1::from_slice(py, b);

        let distance = metric.call_method1("compute", (a_py, b_py)).unwrap();
        distance.extract::<f32>().unwrap()
    })
}
```

---

## Example Usage

### Use Case 1: Hamming Distance for Binary Embeddings

```python
import chromadb
from chromadb.distance import HammingDistance

client = chromadb.Client()

# Create collection with Hamming distance
collection = client.create_collection(
    name="binary_hashes",
    metadata={"hnsw:space": "hamming"}  # Use registered metric
)

# Add binary vectors (simhash, perceptual hashes, etc.)
collection.add(
    ids=["doc1", "doc2", "doc3"],
    embeddings=[
        [1, 0, 1, 1, 0, 1, 0, 1],
        [1, 0, 0, 1, 0, 1, 0, 1],
        [0, 1, 0, 1, 1, 0, 1, 0],
    ]
)

# Query with Hamming distance
results = collection.query(
    query_embeddings=[[1, 0, 1, 1, 0, 1, 0, 0]],
    n_results=2
)
# Returns docs with fewest bit differences
```

### Use Case 2: Custom Learned Metric

```python
from chromadb.distance import DistanceMetric, MetricRegistry
import torch

class NeuralMetric(DistanceMetric):
    """Learned metric using neural network"""

    def __init__(self, model_path: str):
        self.model = torch.load(model_path)

    def name(self) -> str:
        return "neural_similarity"

    def compute(self, a, b) -> float:
        with torch.no_grad():
            # Concatenate vectors and pass through network
            combined = torch.cat([
                torch.tensor(a),
                torch.tensor(b)
            ])
            distance = self.model(combined).item()
        return distance

# Register custom metric
MetricRegistry.register(NeuralMetric("my_model.pt"))

# Use in collection
collection = client.create_collection(
    name="learned_similarity",
    metadata={"hnsw:space": "neural_similarity"}
)
```

### Use Case 3: Domain-Specific Metric

```python
class ChemicalSimilarity(DistanceMetric):
    """Custom metric for molecular fingerprints"""

    def name(self) -> str:
        return "tanimoto"

    def compute(self, a, b) -> float:
        # Tanimoto coefficient for chemical similarity
        intersection = np.sum(np.minimum(a, b))
        union = np.sum(np.maximum(a, b))
        return 1.0 - (intersection / union)

MetricRegistry.register(ChemicalSimilarity())
```

---

## Implementation Plan

### Milestone 1: Python API (3 dev-days)
- [ ] Create `chromadb/distance/__init__.py`
- [ ] Implement `DistanceMetric` base class
- [ ] Implement `MetricRegistry`
- [ ] Add built-in metrics (Hamming, Manhattan, Jaccard)
- [ ] Add unit tests

### Milestone 2: Configuration Integration (2 dev-days)
- [ ] Update `CollectionConfiguration` to accept custom metrics
- [ ] Validate metric registration on collection creation
- [ ] Add metric metadata to collection schema
- [ ] Test configuration serialization

### Milestone 3: Rust Integration (2 dev-days)
- [ ] Extend `DistanceFunction` enum with `Custom` variant
- [ ] Implement PyO3 callback to Python metric
- [ ] Add caching for Python metric calls
- [ ] Add Rust unit tests

### Milestone 4: Performance Optimization (1 dev-day)
- [ ] Add batch computation support
- [ ] Add metric result caching
- [ ] Profile Python↔Rust overhead
- [ ] Optimize hot paths

### Milestone 5: Documentation (1 dev-day)
- [ ] API documentation
- [ ] Custom metric guide
- [ ] Example implementations
- [ ] Performance best practices

---

## Backwards Compatibility

### No Breaking Changes
- Existing metrics (L2, Cosine, IP) unchanged
- New API is purely additive
- Default behavior preserved

### Migration Path
Not needed - purely additive feature.

---

## Alternatives Considered

### Alternative 1: JIT-Compiled Metrics
Use Numba or similar to compile Python → native code
**Rejected:** Adds complex dependency, not all metrics JIT-compatible

### Alternative 2: Rust-Only Custom Metrics
Force users to write Rust implementations
**Rejected:** High barrier to entry, limits experimentation

### Alternative 3: JavaScript-Based Metrics
Allow JS distance functions for web clients
**Considered for future:** Good for edge deployment

---

## Performance Impact

### Expected Performance

| Metric Type | Performance | Notes |
|-------------|-------------|-------|
| Native (L2, Cosine, IP) | No change | SIMD-optimized, ~10ns per pair |
| Built-in Custom (Python) | ~100µs per pair | Python call overhead |
| User Custom (Python) | ~200µs per pair | Depends on implementation |
| Batch Custom | ~10µs per pair | Amortizes Python call |

### Optimization: Batch Computation

```python
# Instead of N Python calls
for q in queries:
    for v in vectors:
        distance = metric.compute(q, v)  # N×M Python calls

# Single Python call for batch
distances = metric.batch_compute(queries, vectors)  # 1 Python call
```

### Benchmarking Plan

```python
import timeit
import numpy as np

def benchmark_metric(metric_name, n_queries=100, n_vectors=1000, dim=128):
    queries = np.random.rand(n_queries, dim).astype(np.float32)
    vectors = np.random.rand(n_vectors, dim).astype(np.float32)

    collection = client.create_collection(
        name="bench",
        metadata={"hnsw:space": metric_name}
    )
    collection.add(
        ids=[str(i) for i in range(n_vectors)],
        embeddings=vectors.tolist()
    )

    start = timeit.default_timer()
    results = collection.query(query_embeddings=queries.tolist(), n_results=10)
    elapsed = timeit.default_timer() - start

    return elapsed

# Expected results:
# L2 (native): 0.050s (baseline)
# Hamming (Python): 0.150s (3x slower)
# Custom (Python): 0.200s (4x slower)
```

---

## Testing Strategy

### Unit Tests

```python
def test_custom_metric_registration():
    """Test metric registration"""
    class TestMetric(DistanceMetric):
        def name(self): return "test"
        def compute(self, a, b): return 1.0

    MetricRegistry.register(TestMetric())
    assert "test" in MetricRegistry.list_metrics()

def test_hamming_distance():
    """Test Hamming distance correctness"""
    metric = HammingDistance()
    a = np.array([1, 0, 1, 1])
    b = np.array([1, 1, 0, 1])
    assert metric.compute(a, b) == 2.0  # 2 bits differ

def test_custom_metric_in_collection():
    """Test using custom metric in collection"""
    collection = client.create_collection(
        name="test",
        metadata={"hnsw:space": "hamming"}
    )
    collection.add(ids=["1"], embeddings=[[1, 0, 1]])
    results = collection.query(query_embeddings=[[1, 0, 0]], n_results=1)
    assert results is not None
```

---

## Documentation Requirements

### User Guide

```markdown
# Custom Distance Metrics

Chroma supports custom distance metrics for specialized use cases.

## Built-in Custom Metrics

- `hamming`: Hamming distance for binary vectors
- `manhattan`: L1 / Manhattan distance
- `jaccard`: Jaccard distance for sets

## Creating Custom Metrics

```python
from chromadb.distance import DistanceMetric, MetricRegistry
import numpy as np

class MyMetric(DistanceMetric):
    def name(self) -> str:
        return "my_metric"

    def compute(self, a: np.ndarray, b: np.ndarray) -> float:
        # Your similarity logic
        return np.sum((a - b) ** 2)  # Example

# Register metric
MetricRegistry.register(MyMetric())

# Use in collection
collection = client.create_collection(
    name="my_collection",
    metadata={"hnsw:space": "my_metric"}
)
```

## Performance Tips

1. Implement `batch_compute()` for better performance
2. Use NumPy vectorization instead of loops
3. Consider caching expensive computations
```

---

## Success Criteria

### Must Have
- [ ] Register 3+ custom metrics (Hamming, Manhattan, Jaccard)
- [ ] Collections created with custom metrics
- [ ] Query results match expected distances
- [ ] Performance < 5x slower than native metrics

### Should Have
- [ ] Batch computation support
- [ ] Examples for 5+ use cases
- [ ] Performance benchmarks published

---

## Effort Estimation

| Phase | Task | Dev-Days |
|-------|------|----------|
| 1 | Python API | 3 |
| 2 | Configuration | 2 |
| 3 | Rust integration | 2 |
| 4 | Optimization | 1 |
| 5 | Documentation | 1 |
| **Total** | | **8 dev-days** |

---

## References

- [scipy.spatial.distance](https://docs.scipy.org/doc/scipy/reference/spatial.distance.html)
- [FAISS Custom Metrics](https://github.com/facebookresearch/faiss/wiki/MetricType-and-distances)
- [Qdrant Custom Scoring](https://qdrant.tech/documentation/concepts/search/#custom-scoring)

---

## Revision History

- **v1.0** (2025-11-17): Initial RFC draft
