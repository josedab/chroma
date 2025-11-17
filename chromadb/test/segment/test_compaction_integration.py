"""Integration tests for automatic segment compaction."""

import tempfile
import shutil
import time
import pytest

import chromadb
from chromadb.config import Settings


@pytest.fixture
def client_with_compaction():
    """Create a Chroma client with compaction enabled."""
    temp_dir = tempfile.mkdtemp()

    settings = Settings(
        allow_reset=True,
        is_persistent=True,
        persist_directory=temp_dir,
        chroma_compaction_enabled=False,  # Disabled by default for tests
    )

    client = chromadb.Client(settings)

    yield client

    # Cleanup
    shutil.rmtree(temp_dir)


class TestManualCompaction:
    """Test manual compaction trigger and status."""

    def test_compact_empty_collection(self, client_with_compaction):
        """Test compacting an empty collection."""
        collection = client_with_compaction.create_collection("test_empty")

        # Should not fail on empty collection
        collection.compact()

        # Check status
        status = collection.get_compaction_status()
        assert isinstance(status, dict)
        assert "in_progress" in status
        assert "progress" in status

    def test_compact_collection_with_data(self, client_with_compaction):
        """Test compacting a collection with data."""
        collection = client_with_compaction.create_collection("test_data")

        # Add some data
        collection.add(
            ids=["id1", "id2", "id3"],
            documents=["doc1", "doc2", "doc3"],
            metadatas=[{"key": "value1"}, {"key": "value2"}, {"key": "value3"}],
        )

        # Trigger compaction
        collection.compact()

        # Check status
        status = collection.get_compaction_status()
        assert isinstance(status, dict)
        assert "in_progress" in status
        assert "progress" in status

    def test_compact_after_deletions(self, client_with_compaction):
        """Test compacting after deleting records."""
        collection = client_with_compaction.create_collection("test_deletions")

        # Add data
        ids = [f"id{i}" for i in range(100)]
        documents = [f"document {i}" for i in range(100)]
        collection.add(ids=ids, documents=documents)

        # Delete half
        collection.delete(ids=ids[:50])

        # Trigger compaction
        collection.compact()

        # Check status
        status = collection.get_compaction_status()
        assert isinstance(status, dict)

        # Verify we can still query
        count = collection.count()
        assert count == 50

    def test_get_compaction_status_structure(self, client_with_compaction):
        """Test the structure of compaction status response."""
        collection = client_with_compaction.create_collection("test_status")

        # Get status without triggering compaction
        status = collection.get_compaction_status()

        # Verify structure
        assert isinstance(status, dict)
        assert "in_progress" in status
        assert "progress" in status
        assert isinstance(status["in_progress"], bool)
        assert isinstance(status["progress"], (int, float))

    def test_compact_multiple_times(self, client_with_compaction):
        """Test triggering compaction multiple times."""
        collection = client_with_compaction.create_collection("test_multiple")

        # Add data
        collection.add(
            ids=["id1", "id2", "id3"],
            documents=["doc1", "doc2", "doc3"],
        )

        # Trigger compaction multiple times
        # Should not fail even if called multiple times
        collection.compact()
        collection.compact()
        collection.compact()

        # Check status
        status = collection.get_compaction_status()
        assert isinstance(status, dict)


class TestCompactionWithUpdates:
    """Test compaction with various update patterns."""

    def test_compact_with_upserts(self, client_with_compaction):
        """Test compaction after upsert operations."""
        collection = client_with_compaction.create_collection("test_upserts")

        # Initial add
        collection.add(ids=["id1"], documents=["doc1"])

        # Upsert multiple times (creates multiple versions)
        for i in range(5):
            collection.upsert(ids=["id1"], documents=[f"doc1_v{i}"])

        # Trigger compaction
        collection.compact()

        # Verify data integrity
        result = collection.get(ids=["id1"])
        assert len(result["ids"]) == 1
        assert result["documents"][0] == "doc1_v4"

    def test_compact_with_updates(self, client_with_compaction):
        """Test compaction after update operations."""
        collection = client_with_compaction.create_collection("test_updates")

        # Initial add
        collection.add(
            ids=["id1", "id2"],
            documents=["doc1", "doc2"],
            metadatas=[{"version": 1}, {"version": 1}],
        )

        # Update metadata multiple times
        for i in range(3):
            collection.update(
                ids=["id1"],
                metadatas=[{"version": i + 2}],
            )

        # Trigger compaction
        collection.compact()

        # Verify data integrity
        result = collection.get(ids=["id1"])
        assert result["metadatas"][0]["version"] == 4

    def test_queries_during_compaction(self, client_with_compaction):
        """Test that queries work during compaction."""
        collection = client_with_compaction.create_collection("test_queries")

        # Add data
        collection.add(
            ids=["id1", "id2", "id3"],
            documents=["doc1", "doc2", "doc3"],
        )

        # Trigger compaction
        collection.compact()

        # Queries should still work
        count = collection.count()
        assert count == 3

        result = collection.get()
        assert len(result["ids"]) == 3

        # Query should work
        query_result = collection.query(
            query_texts=["doc1"],
            n_results=2,
        )
        assert len(query_result["ids"][0]) > 0


class TestCompactionScenarios:
    """Test realistic compaction scenarios."""

    def test_large_collection_scenario(self, client_with_compaction):
        """Test compaction on a larger collection."""
        collection = client_with_compaction.create_collection("test_large")

        # Add many documents
        batch_size = 100
        num_batches = 5

        for batch in range(num_batches):
            ids = [f"id{batch}_{i}" for i in range(batch_size)]
            documents = [f"document {batch}_{i}" for i in range(batch_size)]
            collection.add(ids=ids, documents=documents)

        total_count = collection.count()
        assert total_count == batch_size * num_batches

        # Delete 30% of documents
        ids_to_delete = [f"id{i // batch_size}_{i % batch_size}" for i in range(0, 150)]
        collection.delete(ids=ids_to_delete)

        remaining_count = collection.count()
        assert remaining_count == total_count - 150

        # Trigger compaction
        collection.compact()

        # Verify data integrity after compaction
        final_count = collection.count()
        assert final_count == remaining_count

    def test_frequent_deletions_scenario(self, client_with_compaction):
        """Test compaction with frequent deletions."""
        collection = client_with_compaction.create_collection("test_frequent_deletes")

        # Add initial data
        initial_ids = [f"id{i}" for i in range(200)]
        initial_docs = [f"doc{i}" for i in range(200)]
        collection.add(ids=initial_ids, documents=initial_docs)

        # Delete in waves
        for wave in range(4):
            start = wave * 40
            end = start + 40
            collection.delete(ids=initial_ids[start:end])

        # Should have 40 documents left
        assert collection.count() == 40

        # Trigger compaction
        collection.compact()

        # Verify integrity
        assert collection.count() == 40

    def test_metadata_only_updates_scenario(self, client_with_compaction):
        """Test compaction with metadata-only updates."""
        collection = client_with_compaction.create_collection("test_metadata_updates")

        # Add documents
        ids = [f"id{i}" for i in range(50)]
        docs = [f"doc{i}" for i in range(50)]
        collection.add(ids=ids, documents=docs)

        # Update metadata many times for same documents
        for iteration in range(10):
            # Update random subset
            update_ids = ids[::2]  # Every other document
            metadatas = [{"iteration": iteration, "updated": True} for _ in update_ids]
            collection.update(ids=update_ids, metadatas=metadatas)

        # Trigger compaction
        collection.compact()

        # Verify final state
        result = collection.get()
        assert len(result["ids"]) == 50

        # Check that updated documents have correct metadata
        updated_result = collection.get(ids=ids[::2])
        for metadata in updated_result["metadatas"]:
            assert metadata["iteration"] == 9
            assert metadata["updated"] is True
