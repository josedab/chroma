# Custom Distance Metrics

Chroma now supports pluggable distance metrics beyond the traditional L2 (Euclidean), Cosine, and Inner Product metrics. This enables specialized use cases such as binary vector comparison, sparse vector analysis, and domain-specific similarity measures.

## Built-in Distance Metrics

### Standard Metrics
- **L2 (Euclidean)**: `l2` - Default metric for dense vectors
- **Cosine**: `cosine` - Normalized dot product similarity
- **Inner Product**: `ip` - Raw dot product similarity

### Custom Metrics
- **Hamming**: `hamming` - Count of differing positions (ideal for binary vectors)
- **Manhattan**: `manhattan` - L1 norm / sum of absolute differences (ideal for sparse vectors)
- **Jaccard**: `jaccard` - Set similarity for binary vectors

## Usage

### Using Built-in Custom Metrics

Simply specify the metric name when creating a collection:

```python
import chromadb

client = chromadb.Client()

# Create collection with Hamming distance
collection = client.create_collection(
    name="binary_hashes",
    metadata={"hnsw:space": "hamming"}
)

# Add binary vectors
collection.add(
    ids=["doc1", "doc2", "doc3"],
    embeddings=[
        [1, 0, 1, 1, 0, 1, 0, 1],
        [1, 0, 0, 1, 0, 1, 0, 1],
        [0, 1, 0, 1, 1, 0, 1, 0],
    ]
)

# Query returns documents with fewest bit differences
results = collection.query(
    query_embeddings=[[1, 0, 1, 1, 0, 1, 0, 0]],
    n_results=2
)
```

### Manhattan Distance Example

```python
# Create collection with Manhattan (L1) distance
collection = client.create_collection(
    name="sparse_vectors",
    metadata={"hnsw:space": "manhattan"}
)

# Add sparse vectors
collection.add(
    ids=["vec1", "vec2", "vec3"],
    embeddings=[
        [1.0, 0.0, 3.0, 0.0, 5.0],
        [0.0, 2.0, 0.0, 4.0, 0.0],
        [1.0, 1.0, 1.0, 1.0, 1.0],
    ]
)

# Query with Manhattan distance
results = collection.query(
    query_embeddings=[[1.0, 0.0, 2.0, 0.0, 4.0]],
    n_results=2
)
```

### Jaccard Distance Example

```python
# Create collection with Jaccard distance for set similarity
collection = client.create_collection(
    name="sets",
    metadata={"hnsw:space": "jaccard"}
)

# Add binary vectors representing sets
# Each position represents presence (1) or absence (0) of an element
collection.add(
    ids=["set1", "set2", "set3"],
    embeddings=[
        [1, 1, 0, 0, 1],  # Set {0, 1, 4}
        [1, 0, 1, 0, 0],  # Set {0, 2}
        [0, 1, 1, 1, 0],  # Set {1, 2, 3}
    ]
)

# Query finds sets with highest overlap
results = collection.query(
    query_embeddings=[[1, 1, 1, 0, 0]],  # Set {0, 1, 2}
    n_results=2
)
```

## Custom User-Defined Metrics

You can also define your own custom distance metrics using the Python API:

```python
from chromadb.distance import DistanceMetric, MetricRegistry
import numpy as np

class MyCustomMetric(DistanceMetric):
    """Example: Weighted Euclidean distance"""

    def __init__(self, weights):
        self.weights = np.array(weights)

    def name(self) -> str:
        return "weighted_euclidean"

    def compute(self, a, b) -> float:
        if not isinstance(a, np.ndarray):
            a = np.array(a)
        if not isinstance(b, np.ndarray):
            b = np.array(b)
        diff = a - b
        return float(np.sqrt(np.sum(self.weights * diff * diff)))

    def batch_compute(self, queries, vectors):
        """Optional: optimize batch computation"""
        # queries: [n_queries, dim]
        # vectors: [n_vectors, dim]
        diff = queries[:, np.newaxis, :] - vectors[np.newaxis, :, :]
        weighted_sq = self.weights * diff * diff
        return np.sqrt(np.sum(weighted_sq, axis=2))

# Register the metric
weights = [1.0, 2.0, 1.0, 3.0]  # Emphasize certain dimensions
MetricRegistry.register(MyCustomMetric(weights))

# Use in a collection
# Note: Custom Python metrics are currently registered globally
# but not yet fully integrated with collection creation
```

## Use Cases

### Hamming Distance
- **Binary hashes**: Perceptual hashing, SimHash, MinHash
- **Bioinformatics**: DNA/RNA sequence comparison
- **Error detection**: Comparing binary codes
- **Feature vectors**: Binary bag-of-words representations

### Manhattan Distance
- **Sparse vectors**: Text embeddings with many zeros
- **Grid-based distances**: Manhattan distance in city blocks
- **Robust to outliers**: Less sensitive than Euclidean distance
- **High-dimensional data**: Often performs better than L2

### Jaccard Distance
- **Set similarity**: Document overlap, tag matching
- **Collaborative filtering**: User preference comparison
- **Image similarity**: Binary feature descriptors
- **Recommendation systems**: Item set comparison

## Performance Considerations

### Native vs. Custom Metrics

| Metric Type | Performance | Notes |
|-------------|-------------|-------|
| L2, Cosine, IP (SIMD) | ~10ns per pair | Hardware-accelerated |
| Hamming, Manhattan, Jaccard | ~50ns per pair | Rust implementation |
| Custom Python metrics | ~100-200µs per pair | Python call overhead |

### Optimization Tips

1. **Use built-in metrics when possible**: They're implemented in Rust for best performance
2. **Implement batch_compute**: Amortizes overhead for custom metrics
3. **Pre-process vectors**: Normalize or transform before adding to collection
4. **Choose appropriate metric**: Match the metric to your data type

## Distance Metric Properties

| Metric | Range | Best For | Normalized |
|--------|-------|----------|------------|
| L2 | [0, ∞) | Dense vectors | No |
| Cosine | [0, 2] | Directional similarity | Yes |
| Inner Product | (-∞, ∞) | Learned embeddings | No |
| Hamming | [0, dim] | Binary vectors | No |
| Manhattan | [0, ∞) | Sparse vectors | No |
| Jaccard | [0, 1] | Set similarity | Yes |

## Backward Compatibility

All existing functionality remains unchanged:
- Default metric is still L2
- Existing L2, Cosine, and IP metrics work exactly as before
- Collections created with old code will continue to work

## Implementation Notes

The custom distance metrics are implemented at multiple levels:
1. **Python API**: `chromadb.distance` module for custom metric registration
2. **Rust Core**: Native implementations in `chroma-distance` crate
3. **Type System**: Extended `Space` enum to include new metrics

## Future Enhancements

Potential future additions (not yet implemented):
- PyO3 callbacks for arbitrary Python metrics in queries
- GPU-accelerated custom metrics
- Learned distance metrics
- Distance metric auto-selection based on data characteristics

## Examples

See the test files for complete examples:
- `chromadb/test/distance/test_metrics.py` - Unit tests for metric implementations
- `chromadb/test/distance/test_integration.py` - Integration tests with collections

## References

- [RFC-0004: Pluggable Distance Metrics System](../analysis-output/rfcs/RFC-0004-pluggable-distance-metrics.md)
- [scipy.spatial.distance](https://docs.scipy.org/doc/scipy/reference/spatial.distance.html) - Reference implementations
- [Metric space](https://en.wikipedia.org/wiki/Metric_space) - Mathematical background
