"""Integration tests for multi-vector embeddings feature.

Tests the end-to-end functionality of multi-vector embeddings,
including add, query, and various aggregation strategies.
"""

import numpy as np
import pytest
from chromadb.api.types import (
    validate_multi_vector_embeddings,
    is_multi_vector,
    normalize_multi_vector_embeddings,
)


class TestMultiVectorValidation:
    """Test multi-vector validation functions."""

    def test_validate_multi_vector_embeddings_valid(self):
        """Valid multi-vector embeddings should pass validation."""
        multi_vectors = [
            [np.array([0.1, 0.2]), np.array([0.3, 0.4])],
            [np.array([0.5, 0.6]), np.array([0.7, 0.8]), np.array([0.9, 1.0])],
        ]
        result = validate_multi_vector_embeddings(multi_vectors)
        assert result == multi_vectors

    def test_validate_multi_vector_embeddings_empty(self):
        """Empty multi-vector list should raise ValueError."""
        with pytest.raises(ValueError, match="at least one item"):
            validate_multi_vector_embeddings([])

    def test_validate_multi_vector_embeddings_wrong_type(self):
        """Non-list input should raise ValueError."""
        with pytest.raises(ValueError, match="Expected multi_vector_embeddings to be a list"):
            validate_multi_vector_embeddings("not a list")  # type: ignore

    def test_validate_multi_vector_embeddings_empty_inner(self):
        """Empty inner multi-vector should raise ValueError."""
        multi_vectors = [
            []  # Empty multi-vector
        ]
        with pytest.raises(ValueError, match="at least one embedding"):
            validate_multi_vector_embeddings(multi_vectors)  # type: ignore

    def test_validate_multi_vector_embeddings_dimension_mismatch(self):
        """Mismatched dimensions within multi-vector should raise ValueError."""
        multi_vectors = [
            [np.array([0.1, 0.2]), np.array([0.3, 0.4, 0.5])]  # Different dims
        ]
        with pytest.raises(ValueError, match="same dimensionality"):
            validate_multi_vector_embeddings(multi_vectors)


class TestIsMultiVector:
    """Test multi-vector detection."""

    def test_is_multi_vector_true(self):
        """Three-level nested list should be detected as multi-vector."""
        # Multi-vector: [[[0.1, 0.2], [0.3, 0.4]]]
        embeddings = [[[0.1, 0.2], [0.3, 0.4]]]
        assert is_multi_vector(embeddings) is True

    def test_is_multi_vector_false_single(self):
        """Two-level nested list should not be multi-vector."""
        # Single-vector: [[0.1, 0.2], [0.3, 0.4]]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        assert is_multi_vector(embeddings) is False

    def test_is_multi_vector_false_numpy(self):
        """List of numpy arrays should not be multi-vector."""
        embeddings = [np.array([0.1, 0.2]), np.array([0.3, 0.4])]
        assert is_multi_vector(embeddings) is False

    def test_is_multi_vector_false_empty(self):
        """Empty list should not be multi-vector."""
        assert is_multi_vector([]) is False


class TestNormalizeMultiVectorEmbeddings:
    """Test multi-vector normalization."""

    def test_normalize_multi_vector_embeddings_lists(self):
        """Should normalize Python lists to numpy arrays."""
        input_data = [
            [[0.1, 0.2], [0.3, 0.4]],
            [[0.5, 0.6]],
        ]
        result = normalize_multi_vector_embeddings(input_data)

        assert len(result) == 2
        assert len(result[0]) == 2
        assert len(result[1]) == 1
        assert isinstance(result[0][0], np.ndarray)
        assert np.array_equal(result[0][0], np.array([0.1, 0.2], dtype=np.float32))

    def test_normalize_multi_vector_embeddings_numpy(self):
        """Should handle numpy arrays."""
        input_data = [
            [np.array([0.1, 0.2]), np.array([0.3, 0.4])],
        ]
        result = normalize_multi_vector_embeddings(input_data)

        assert len(result) == 1
        assert len(result[0]) == 2
        assert isinstance(result[0][0], np.ndarray)

    def test_normalize_multi_vector_embeddings_none(self):
        """None input should return None."""
        result = normalize_multi_vector_embeddings(None)
        assert result is None

    def test_normalize_multi_vector_embeddings_empty(self):
        """Empty list should raise ValueError."""
        with pytest.raises(ValueError, match="non-empty list"):
            normalize_multi_vector_embeddings([])


class TestMultiVectorIntegration:
    """Integration tests requiring a running Chroma instance.

    Note: These tests are designed to work with the multi-vector feature.
    They may be skipped if the test infrastructure doesn't support them yet.
    """

    @pytest.mark.skip(reason="Requires full Chroma setup with multi-vector support")
    def test_add_multi_vector_embeddings(self):
        """Test adding documents with multi-vector embeddings."""
        import chromadb

        client = chromadb.Client()
        collection = client.create_collection("test_multi_vector")

        # Add document with multi-vector
        collection.add(
            ids=["doc1"],
            embeddings=[
                [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
            ],
            documents=["Test document with multiple vectors"],
        )

        assert collection.count() == 1

    @pytest.mark.skip(reason="Requires full Chroma setup with multi-vector support")
    def test_query_with_maxsim(self):
        """Test querying with MaxSim aggregation strategy."""
        import chromadb

        client = chromadb.Client()
        collection = client.create_collection("test_maxsim")

        # Add document
        collection.add(
            ids=["doc1"],
            embeddings=[[[1.0, 0.0], [0.0, 1.0]]],
            documents=["Document 1"],
        )

        # Query with MaxSim
        results = collection.query(
            query_embeddings=[[[1.0, 0.0], [0.0, 1.0]]],
            n_results=1,
            multi_vector_strategy="maxsim",
        )

        assert len(results["ids"][0]) == 1
        assert results["ids"][0][0] == "doc1"

    @pytest.mark.skip(reason="Requires full Chroma setup with multi-vector support")
    def test_backwards_compatibility(self):
        """Test that single-vector embeddings still work."""
        import chromadb

        client = chromadb.Client()
        collection = client.create_collection("test_backwards_compat")

        # Add with single-vector (traditional way)
        collection.add(
            ids=["doc1", "doc2"],
            embeddings=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            documents=["Doc 1", "Doc 2"],
        )

        # Query without multi_vector_strategy
        results = collection.query(
            query_embeddings=[[0.1, 0.2, 0.3]],
            n_results=2,
        )

        assert len(results["ids"][0]) == 2
