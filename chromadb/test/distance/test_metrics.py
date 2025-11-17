"""Tests for custom distance metrics"""

import pytest
import numpy as np
from chromadb.distance import (
    DistanceMetric,
    MetricRegistry,
    HammingDistance,
    ManhattanDistance,
    JaccardDistance,
)


class TestMetricRegistry:
    """Test MetricRegistry functionality"""

    def test_register_metric(self):
        """Test registering a custom metric"""

        class TestMetric(DistanceMetric):
            def name(self) -> str:
                return "test_metric"

            def compute(self, a, b) -> float:
                return 1.0

        # Reset registry for testing
        original_metrics = MetricRegistry._metrics.copy()
        try:
            MetricRegistry._metrics = {}
            MetricRegistry.register(TestMetric())
            assert "test_metric" in MetricRegistry.list_metrics()
        finally:
            MetricRegistry._metrics = original_metrics

    def test_duplicate_registration(self):
        """Test that duplicate registration raises an error"""

        class TestMetric(DistanceMetric):
            def name(self) -> str:
                return "duplicate"

            def compute(self, a, b) -> float:
                return 1.0

        original_metrics = MetricRegistry._metrics.copy()
        try:
            MetricRegistry._metrics = {}
            MetricRegistry.register(TestMetric())
            with pytest.raises(ValueError, match="already registered"):
                MetricRegistry.register(TestMetric())
        finally:
            MetricRegistry._metrics = original_metrics

    def test_get_metric(self):
        """Test getting a registered metric"""
        assert MetricRegistry.is_registered("hamming")
        metric = MetricRegistry.get("hamming")
        assert isinstance(metric, HammingDistance)

    def test_get_unknown_metric(self):
        """Test that getting unknown metric raises error"""
        with pytest.raises(ValueError, match="Unknown metric"):
            MetricRegistry.get("unknown_metric")

    def test_list_metrics(self):
        """Test listing all registered metrics"""
        metrics = MetricRegistry.list_metrics()
        assert "hamming" in metrics
        assert "manhattan" in metrics
        assert "jaccard" in metrics


class TestHammingDistance:
    """Test Hamming distance metric"""

    def test_hamming_distance(self):
        """Test Hamming distance computation"""
        metric = HammingDistance()
        a = np.array([1, 0, 1, 1])
        b = np.array([1, 1, 0, 1])
        distance = metric.compute(a, b)
        assert distance == 2.0  # 2 bits differ

    def test_hamming_distance_identical(self):
        """Test Hamming distance for identical vectors"""
        metric = HammingDistance()
        a = np.array([1, 0, 1, 1])
        distance = metric.compute(a, a)
        assert distance == 0.0

    def test_hamming_distance_all_different(self):
        """Test Hamming distance for completely different vectors"""
        metric = HammingDistance()
        a = np.array([1, 1, 1, 1])
        b = np.array([0, 0, 0, 0])
        distance = metric.compute(a, b)
        assert distance == 4.0

    def test_hamming_batch_compute(self):
        """Test batch computation for Hamming distance"""
        metric = HammingDistance()
        queries = np.array([[1, 0, 1], [0, 1, 0]], dtype=np.float32)
        vectors = np.array([[1, 0, 0], [0, 1, 1]], dtype=np.float32)
        distances = metric.batch_compute(queries, vectors)
        assert distances.shape == (2, 2)
        # First query vs first vector: 1 difference
        assert distances[0, 0] == 1.0
        # Second query vs second vector: 1 difference
        assert distances[1, 1] == 1.0


class TestManhattanDistance:
    """Test Manhattan distance metric"""

    def test_manhattan_distance(self):
        """Test Manhattan distance computation"""
        metric = ManhattanDistance()
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([4.0, 5.0, 6.0])
        distance = metric.compute(a, b)
        assert distance == 9.0  # |1-4| + |2-5| + |3-6| = 3 + 3 + 3 = 9

    def test_manhattan_distance_identical(self):
        """Test Manhattan distance for identical vectors"""
        metric = ManhattanDistance()
        a = np.array([1.0, 2.0, 3.0])
        distance = metric.compute(a, a)
        assert distance == 0.0

    def test_manhattan_batch_compute(self):
        """Test batch computation for Manhattan distance"""
        metric = ManhattanDistance()
        queries = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
        vectors = np.array([[0.0, 0.0], [1.0, 1.0]], dtype=np.float32)
        distances = metric.batch_compute(queries, vectors)
        assert distances.shape == (2, 2)
        # First query vs first vector: |1-0| + |2-0| = 3
        assert distances[0, 0] == 3.0


class TestJaccardDistance:
    """Test Jaccard distance metric"""

    def test_jaccard_distance(self):
        """Test Jaccard distance computation"""
        metric = JaccardDistance()
        # Binary vectors representing sets
        a = np.array([1, 0, 1, 0])
        b = np.array([1, 1, 0, 0])
        # Intersection: 1 (position 0)
        # Union: 3 (positions 0, 1, 2)
        # Jaccard similarity: 1/3
        # Jaccard distance: 1 - 1/3 = 2/3
        distance = metric.compute(a, b)
        assert abs(distance - 2.0 / 3.0) < 1e-6

    def test_jaccard_distance_identical(self):
        """Test Jaccard distance for identical vectors"""
        metric = JaccardDistance()
        a = np.array([1, 0, 1, 1])
        distance = metric.compute(a, a)
        assert abs(distance - 0.0) < 1e-6

    def test_jaccard_distance_no_overlap(self):
        """Test Jaccard distance for vectors with no overlap"""
        metric = JaccardDistance()
        a = np.array([1, 1, 0, 0])
        b = np.array([0, 0, 1, 1])
        # No intersection, union = 4
        # Jaccard distance = 1.0
        distance = metric.compute(a, b)
        assert abs(distance - 1.0) < 1e-6

    def test_jaccard_distance_empty_vectors(self):
        """Test Jaccard distance for empty vectors"""
        metric = JaccardDistance()
        a = np.array([0, 0, 0, 0])
        b = np.array([0, 0, 0, 0])
        # Both empty, distance should be 0
        distance = metric.compute(a, b)
        assert distance == 0.0

    def test_jaccard_batch_compute(self):
        """Test batch computation for Jaccard distance"""
        metric = JaccardDistance()
        queries = np.array([[1, 0, 1], [0, 1, 0]], dtype=np.float32)
        vectors = np.array([[1, 0, 0], [0, 1, 1]], dtype=np.float32)
        distances = metric.batch_compute(queries, vectors)
        assert distances.shape == (2, 2)
        # Check that distances are in valid range [0, 1]
        assert np.all(distances >= 0.0)
        assert np.all(distances <= 1.0)


class TestCustomMetric:
    """Test custom user-defined metric"""

    def test_custom_metric_implementation(self):
        """Test implementing a custom metric"""

        class EuclideanMetric(DistanceMetric):
            """Simple Euclidean distance implementation"""

            def name(self) -> str:
                return "custom_euclidean"

            def compute(self, a, b) -> float:
                if not isinstance(a, np.ndarray):
                    a = np.array(a)
                if not isinstance(b, np.ndarray):
                    b = np.array(b)
                return float(np.sqrt(np.sum((a - b) ** 2)))

        metric = EuclideanMetric()
        a = np.array([0.0, 0.0, 0.0])
        b = np.array([3.0, 4.0, 0.0])
        distance = metric.compute(a, b)
        assert abs(distance - 5.0) < 1e-6  # 3-4-5 triangle

    def test_invalid_metric_registration(self):
        """Test that invalid metrics are rejected"""

        class InvalidMetric(DistanceMetric):
            def name(self) -> str:
                return "invalid"

            def compute(self, a, b) -> float:
                # This will fail validation (negative distance)
                return -1.0

        original_metrics = MetricRegistry._metrics.copy()
        try:
            MetricRegistry._metrics = {}
            with pytest.raises(ValueError, match="Invalid metric"):
                MetricRegistry.register(InvalidMetric())
        finally:
            MetricRegistry._metrics = original_metrics
