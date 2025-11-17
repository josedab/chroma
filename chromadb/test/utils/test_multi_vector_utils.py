"""Tests for multi-vector embedding utilities."""

import numpy as np
import pytest
from chromadb.utils.multi_vector_utils import (
    cosine_similarity,
    maxsim_score,
    average_score,
    sum_score,
    first_score,
    aggregate_multi_vector_scores,
    convert_multi_vector_to_synthetic_ids,
    extract_parent_id_from_synthetic,
    is_synthetic_multi_vector_id,
)


class TestCosineSimilarity:
    """Test cosine similarity computation."""

    def test_identical_vectors(self):
        """Identical vectors should have similarity of 1.0."""
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])
        assert cosine_similarity(vec1, vec2) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        """Orthogonal vectors should have similarity of 0.0."""
        vec1 = np.array([1.0, 0.0])
        vec2 = np.array([0.0, 1.0])
        assert cosine_similarity(vec1, vec2) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        """Opposite vectors should have similarity of -1.0."""
        vec1 = np.array([1.0, 0.0])
        vec2 = np.array([-1.0, 0.0])
        assert cosine_similarity(vec1, vec2) == pytest.approx(-1.0)

    def test_zero_vector(self):
        """Zero vectors should return 0.0."""
        vec1 = np.array([0.0, 0.0])
        vec2 = np.array([1.0, 0.0])
        assert cosine_similarity(vec1, vec2) == 0.0


class TestMaxSimScore:
    """Test MaxSim aggregation strategy."""

    def test_perfect_match(self):
        """Perfect match should score highly."""
        query_vectors = [
            np.array([1.0, 0.0]),
            np.array([0.0, 1.0]),
        ]
        doc_vectors = [
            np.array([1.0, 0.0]),
            np.array([0.0, 1.0]),
        ]
        score = maxsim_score(query_vectors, doc_vectors)
        assert score == pytest.approx(2.0)  # Two perfect matches

    def test_partial_match(self):
        """Partial match should score moderately."""
        query_vectors = [np.array([1.0, 0.0])]
        doc_vectors = [
            np.array([0.707, 0.707]),  # 45-degree angle
            np.array([0.0, 1.0]),  # Orthogonal
        ]
        score = maxsim_score(query_vectors, doc_vectors)
        # Should pick the best match (0.707)
        assert score == pytest.approx(0.707, rel=1e-2)

    def test_empty_vectors(self):
        """Empty vectors should return 0.0."""
        assert maxsim_score([], [np.array([1.0, 0.0])]) == 0.0
        assert maxsim_score([np.array([1.0, 0.0])], []) == 0.0


class TestAverageScore:
    """Test average pooling strategy."""

    def test_all_perfect_matches(self):
        """All perfect matches should score 1.0."""
        query_vectors = [np.array([1.0, 0.0]), np.array([0.0, 1.0])]
        doc_vectors = [np.array([1.0, 0.0]), np.array([0.0, 1.0])]
        score = average_score(query_vectors, doc_vectors)
        # (1.0 + 0.0 + 0.0 + 1.0) / 4 = 0.5
        assert score == pytest.approx(0.5)

    def test_empty_vectors(self):
        """Empty vectors should return 0.0."""
        assert average_score([], [np.array([1.0, 0.0])]) == 0.0


class TestSumScore:
    """Test sum aggregation strategy."""

    def test_sum_of_similarities(self):
        """Should sum all pairwise similarities."""
        query_vectors = [np.array([1.0, 0.0])]
        doc_vectors = [np.array([1.0, 0.0]), np.array([0.0, 1.0])]
        score = sum_score(query_vectors, doc_vectors)
        # 1.0 (perfect match) + 0.0 (orthogonal) = 1.0
        assert score == pytest.approx(1.0)


class TestFirstScore:
    """Test first-vector-only strategy."""

    def test_uses_only_first_vectors(self):
        """Should only use first vectors from each multi-vector."""
        query_vectors = [
            np.array([1.0, 0.0]),
            np.array([0.0, 1.0]),  # Should be ignored
        ]
        doc_vectors = [
            np.array([1.0, 0.0]),
            np.array([0.0, 1.0]),  # Should be ignored
        ]
        score = first_score(query_vectors, doc_vectors)
        assert score == pytest.approx(1.0)  # Perfect match of first vectors


class TestAggregateMultiVectorScores:
    """Test the main aggregation dispatcher."""

    def test_maxsim_strategy(self):
        """Should dispatch to maxsim."""
        query = [np.array([1.0, 0.0])]
        doc = [np.array([1.0, 0.0])]
        score = aggregate_multi_vector_scores(query, doc, "maxsim")
        assert score == pytest.approx(1.0)

    def test_avg_strategy(self):
        """Should dispatch to average."""
        query = [np.array([1.0, 0.0])]
        doc = [np.array([1.0, 0.0])]
        score = aggregate_multi_vector_scores(query, doc, "avg")
        assert score == pytest.approx(1.0)

    def test_sum_strategy(self):
        """Should dispatch to sum."""
        query = [np.array([1.0, 0.0])]
        doc = [np.array([1.0, 0.0])]
        score = aggregate_multi_vector_scores(query, doc, "sum")
        assert score == pytest.approx(1.0)

    def test_first_strategy(self):
        """Should dispatch to first."""
        query = [np.array([1.0, 0.0])]
        doc = [np.array([1.0, 0.0])]
        score = aggregate_multi_vector_scores(query, doc, "first")
        assert score == pytest.approx(1.0)

    def test_unknown_strategy(self):
        """Should raise ValueError for unknown strategy."""
        query = [np.array([1.0, 0.0])]
        doc = [np.array([1.0, 0.0])]
        with pytest.raises(ValueError, match="Unknown multi-vector strategy"):
            aggregate_multi_vector_scores(query, doc, "unknown")  # type: ignore


class TestSyntheticIDConversion:
    """Test synthetic ID generation and parsing."""

    def test_convert_multi_vector_to_synthetic_ids(self):
        """Should create synthetic IDs for each vector."""
        doc_id = "doc1"
        multi_vector = [
            np.array([0.1, 0.2]),
            np.array([0.3, 0.4]),
            np.array([0.5, 0.6]),
        ]
        metadata = {"key": "value"}
        document = "test document"

        entries = convert_multi_vector_to_synthetic_ids(
            doc_id, multi_vector, metadata, document
        )

        assert len(entries) == 3
        assert entries[0]["id"] == "doc1__mvidx_0"
        assert entries[1]["id"] == "doc1__mvidx_1"
        assert entries[2]["id"] == "doc1__mvidx_2"

        # Check metadata
        assert entries[0]["metadata"]["__multi_vector_parent"] == "doc1"
        assert entries[0]["metadata"]["__multi_vector_index"] == 0
        assert entries[0]["metadata"]["__multi_vector_count"] == 3
        assert entries[0]["metadata"]["key"] == "value"

        # Check embedding
        assert np.array_equal(entries[0]["embedding"], multi_vector[0])
        assert np.array_equal(entries[1]["embedding"], multi_vector[1])
        assert np.array_equal(entries[2]["embedding"], multi_vector[2])

    def test_extract_parent_id_from_synthetic(self):
        """Should extract parent ID from synthetic ID."""
        assert extract_parent_id_from_synthetic("doc1__mvidx_0") == "doc1"
        assert extract_parent_id_from_synthetic("doc1__mvidx_5") == "doc1"
        assert extract_parent_id_from_synthetic("my_doc__mvidx_10") == "my_doc"

        # Non-synthetic IDs should return as-is
        assert extract_parent_id_from_synthetic("regular_id") == "regular_id"

    def test_is_synthetic_multi_vector_id(self):
        """Should detect synthetic multi-vector IDs."""
        assert is_synthetic_multi_vector_id("doc1__mvidx_0") is True
        assert is_synthetic_multi_vector_id("doc1__mvidx_5") is True
        assert is_synthetic_multi_vector_id("regular_id") is False
        assert is_synthetic_multi_vector_id("doc1__other_suffix") is False
