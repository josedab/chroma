"""Integration tests for custom distance metrics with collections"""

import pytest
import numpy as np
import chromadb
from chromadb.config import Settings


@pytest.fixture
def client():
    """Create a test client"""
    return chromadb.Client(Settings(allow_reset=True))


class TestHammingDistanceIntegration:
    """Test Hamming distance with collections"""

    def test_create_collection_with_hamming(self, client):
        """Test creating a collection with Hamming distance"""
        collection = client.create_collection(
            name="hamming_test", metadata={"hnsw:space": "hamming"}
        )
        assert collection.metadata["hnsw:space"] == "hamming"

    def test_hamming_distance_query(self, client):
        """Test querying with Hamming distance"""
        collection = client.create_collection(
            name="hamming_query", metadata={"hnsw:space": "hamming"}
        )

        # Add binary vectors
        collection.add(
            ids=["doc1", "doc2", "doc3"],
            embeddings=[
                [1, 0, 1, 1, 0, 1, 0, 1],
                [1, 0, 0, 1, 0, 1, 0, 1],
                [0, 1, 0, 1, 1, 0, 1, 0],
            ],
        )

        # Query with a binary vector
        results = collection.query(query_embeddings=[[1, 0, 1, 1, 0, 1, 0, 0]], n_results=2)

        # Should return doc1 and doc2 as closest (fewer bit differences)
        assert len(results["ids"][0]) == 2
        assert "doc1" in results["ids"][0]

    def test_hamming_distance_ordering(self, client):
        """Test that Hamming distance returns results in correct order"""
        collection = client.create_collection(
            name="hamming_order", metadata={"hnsw:space": "hamming"}
        )

        # Add vectors with known Hamming distances
        query = [1, 0, 1, 0]
        collection.add(
            ids=["identical", "one_diff", "two_diff", "four_diff"],
            embeddings=[
                [1, 0, 1, 0],  # 0 differences
                [1, 0, 1, 1],  # 1 difference
                [1, 1, 0, 0],  # 2 differences
                [0, 1, 0, 1],  # 4 differences
            ],
        )

        results = collection.query(query_embeddings=[query], n_results=4)

        # Results should be ordered by increasing Hamming distance
        ids = results["ids"][0]
        assert ids[0] == "identical"
        assert ids[1] == "one_diff"
        assert ids[2] == "two_diff"
        assert ids[3] == "four_diff"


class TestManhattanDistanceIntegration:
    """Test Manhattan distance with collections"""

    def test_create_collection_with_manhattan(self, client):
        """Test creating a collection with Manhattan distance"""
        collection = client.create_collection(
            name="manhattan_test", metadata={"hnsw:space": "manhattan"}
        )
        assert collection.metadata["hnsw:space"] == "manhattan"

    def test_manhattan_distance_query(self, client):
        """Test querying with Manhattan distance"""
        collection = client.create_collection(
            name="manhattan_query", metadata={"hnsw:space": "manhattan"}
        )

        # Add vectors
        collection.add(
            ids=["vec1", "vec2", "vec3"],
            embeddings=[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]],
        )

        # Query
        results = collection.query(query_embeddings=[[1.5, 2.5, 3.5]], n_results=2)

        # Should return vec1 as closest
        assert len(results["ids"][0]) == 2
        assert results["ids"][0][0] == "vec1"

    def test_manhattan_distance_ordering(self, client):
        """Test that Manhattan distance returns results in correct order"""
        collection = client.create_collection(
            name="manhattan_order", metadata={"hnsw:space": "manhattan"}
        )

        query = [0.0, 0.0]
        collection.add(
            ids=["close", "medium", "far"],
            embeddings=[[1.0, 1.0], [2.0, 2.0], [5.0, 5.0]],  # L1 = 2  # L1 = 4  # L1 = 10
        )

        results = collection.query(query_embeddings=[query], n_results=3)

        # Results should be ordered by increasing Manhattan distance
        ids = results["ids"][0]
        assert ids[0] == "close"
        assert ids[1] == "medium"
        assert ids[2] == "far"


class TestJaccardDistanceIntegration:
    """Test Jaccard distance with collections"""

    def test_create_collection_with_jaccard(self, client):
        """Test creating a collection with Jaccard distance"""
        collection = client.create_collection(
            name="jaccard_test", metadata={"hnsw:space": "jaccard"}
        )
        assert collection.metadata["hnsw:space"] == "jaccard"

    def test_jaccard_distance_query(self, client):
        """Test querying with Jaccard distance"""
        collection = client.create_collection(
            name="jaccard_query", metadata={"hnsw:space": "jaccard"}
        )

        # Add binary vectors representing sets
        collection.add(
            ids=["set1", "set2", "set3"],
            embeddings=[[1, 1, 0, 0], [1, 0, 1, 0], [0, 0, 1, 1]],
        )

        # Query with a set
        results = collection.query(query_embeddings=[[1, 1, 1, 0]], n_results=2)

        # Should return sets with highest Jaccard similarity
        assert len(results["ids"][0]) == 2

    def test_jaccard_distance_set_similarity(self, client):
        """Test that Jaccard distance correctly measures set similarity"""
        collection = client.create_collection(
            name="jaccard_sets", metadata={"hnsw:space": "jaccard"}
        )

        query = [1, 1, 0, 0]  # Set {0, 1}
        collection.add(
            ids=["identical", "partial", "disjoint"],
            embeddings=[
                [1, 1, 0, 0],  # Same set {0, 1}
                [1, 0, 1, 0],  # Partial overlap {0, 2}
                [0, 0, 1, 1],  # Disjoint {2, 3}
            ],
        )

        results = collection.query(query_embeddings=[query], n_results=3)

        # Identical set should be closest
        ids = results["ids"][0]
        assert ids[0] == "identical"


class TestDistanceMetricValidation:
    """Test validation of distance metrics"""

    def test_invalid_distance_metric(self, client):
        """Test that invalid distance metric raises error"""
        with pytest.raises(Exception):  # Should raise validation error
            client.create_collection(
                name="invalid_metric", metadata={"hnsw:space": "invalid_metric_name"}
            )

    def test_valid_distance_metrics(self, client):
        """Test that all valid distance metrics are accepted"""
        valid_metrics = ["l2", "cosine", "ip", "hamming", "manhattan", "jaccard"]
        for i, metric in enumerate(valid_metrics):
            collection = client.create_collection(
                name=f"test_{metric}_{i}", metadata={"hnsw:space": metric}
            )
            assert collection.metadata["hnsw:space"] == metric


class TestDistanceMetricMigration:
    """Test backward compatibility"""

    def test_default_metric(self, client):
        """Test that default metric is still l2"""
        collection = client.create_collection(name="default_metric")
        # Default should be l2
        assert collection.metadata.get("hnsw:space", "l2") == "l2"

    def test_existing_metrics_still_work(self, client):
        """Test that existing L2, Cosine, IP metrics still work"""
        for metric in ["l2", "cosine", "ip"]:
            collection = client.create_collection(
                name=f"existing_{metric}", metadata={"hnsw:space": metric}
            )
            collection.add(
                ids=["1", "2"], embeddings=[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
            )
            results = collection.query(query_embeddings=[[1.0, 2.0, 3.0]], n_results=1)
            assert len(results["ids"][0]) == 1
