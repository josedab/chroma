"""
Pluggable distance metrics system for Chroma.

This module provides a framework for registering and using custom distance metrics
beyond the built-in L2, Cosine, and Inner Product metrics.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Union
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
            assert isinstance(distance, (int, float, np.number))
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

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a metric is registered"""
        return name in cls._metrics


# Built-in custom metrics


class HammingDistance(DistanceMetric):
    """Hamming distance for binary/integer vectors"""

    def name(self) -> str:
        return "hamming"

    def compute(
        self,
        a: Union[NDArray, List[float]],
        b: Union[NDArray, List[float]],
    ) -> float:
        if not isinstance(a, np.ndarray):
            a = np.array(a)
        if not isinstance(b, np.ndarray):
            b = np.array(b)
        return float(np.sum(a != b))

    def batch_compute(
        self,
        queries: NDArray[np.float32],
        vectors: NDArray[np.float32],
    ) -> NDArray[np.float32]:
        # Optimized batch computation
        # queries: [n_queries, dim]
        # vectors: [n_vectors, dim]
        # result: [n_queries, n_vectors]
        return np.sum(
            queries[:, np.newaxis, :] != vectors[np.newaxis, :, :],
            axis=2,
            dtype=np.float32,
        )


class ManhattanDistance(DistanceMetric):
    """L1 / Manhattan distance"""

    def name(self) -> str:
        return "manhattan"

    def compute(
        self,
        a: Union[NDArray, List[float]],
        b: Union[NDArray, List[float]],
    ) -> float:
        if not isinstance(a, np.ndarray):
            a = np.array(a)
        if not isinstance(b, np.ndarray):
            b = np.array(b)
        return float(np.sum(np.abs(a - b)))

    def batch_compute(
        self,
        queries: NDArray[np.float32],
        vectors: NDArray[np.float32],
    ) -> NDArray[np.float32]:
        # Optimized batch computation
        return np.sum(
            np.abs(queries[:, np.newaxis, :] - vectors[np.newaxis, :, :]),
            axis=2,
            dtype=np.float32,
        )


class JaccardDistance(DistanceMetric):
    """Jaccard distance for binary vectors"""

    def name(self) -> str:
        return "jaccard"

    def compute(
        self,
        a: Union[NDArray, List[float]],
        b: Union[NDArray, List[float]],
    ) -> float:
        if not isinstance(a, np.ndarray):
            a = np.array(a)
        if not isinstance(b, np.ndarray):
            b = np.array(b)

        intersection = np.sum(np.logical_and(a, b))
        union = np.sum(np.logical_or(a, b))
        if union == 0:
            return 0.0
        return float(1.0 - (intersection / union))

    def batch_compute(
        self,
        queries: NDArray[np.float32],
        vectors: NDArray[np.float32],
    ) -> NDArray[np.float32]:
        # Optimized batch computation
        # queries: [n_queries, dim]
        # vectors: [n_vectors, dim]
        # Convert to boolean for logical operations
        q_bool = queries.astype(bool)
        v_bool = vectors.astype(bool)

        # Compute intersection and union
        intersection = np.sum(
            np.logical_and(q_bool[:, np.newaxis, :], v_bool[np.newaxis, :, :]),
            axis=2,
            dtype=np.float32,
        )
        union = np.sum(
            np.logical_or(q_bool[:, np.newaxis, :], v_bool[np.newaxis, :, :]),
            axis=2,
            dtype=np.float32,
        )

        # Avoid division by zero
        distances = np.ones_like(intersection)
        mask = union > 0
        distances[mask] = 1.0 - (intersection[mask] / union[mask])
        return distances


# Register built-in metrics
MetricRegistry.register(HammingDistance())
MetricRegistry.register(ManhattanDistance())
MetricRegistry.register(JaccardDistance())


__all__ = [
    "DistanceMetric",
    "MetricRegistry",
    "HammingDistance",
    "ManhattanDistance",
    "JaccardDistance",
]
