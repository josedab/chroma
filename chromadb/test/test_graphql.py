"""
Tests for the GraphQL API layer
"""

import pytest
from typing import Any, Dict
import numpy as np

try:
    import strawberry
    from chromadb.server.graphql import (
        schema,
        Query,
        Mutation,
        Collection,
        QueryResult,
        GetResult,
    )

    GRAPHQL_AVAILABLE = True
except ImportError:
    GRAPHQL_AVAILABLE = False

import chromadb
from chromadb.config import Settings, DEFAULT_TENANT, DEFAULT_DATABASE
from chromadb.api import ServerAPI


@pytest.fixture
def api():
    """Create a test API instance"""
    settings = Settings(
        chroma_api_impl="chromadb.api.segment.SegmentAPI",
        chroma_sysdb_impl="chromadb.db.impl.sqlite.SqliteDB",
        chroma_producer_impl="chromadb.db.impl.sqlite.SqliteDB",
        chroma_consumer_impl="chromadb.db.impl.sqlite.SqliteDB",
        chroma_segment_manager_impl="chromadb.segment.impl.manager.local.LocalSegmentManager",
        allow_reset=True,
        is_persistent=False,
    )
    system = chromadb.config.System(settings)
    api = system.instance(ServerAPI)
    system.start()

    yield api

    system.stop()


@pytest.fixture
def graphql_context(api):
    """Create a GraphQL context with the API"""
    return {"api": api}


@pytest.mark.skipif(not GRAPHQL_AVAILABLE, reason="GraphQL dependencies not available")
class TestGraphQLQueries:
    """Test GraphQL query operations"""

    async def test_create_and_get_collection(self, api, graphql_context):
        """Test creating and getting a collection via GraphQL"""
        # Create collection using mutation
        mutation = Mutation()
        collection = mutation.create_collection(
            info=self._make_info(graphql_context),
            name="test_collection",
            metadata={"description": "Test collection"},
        )

        assert collection is not None
        assert collection.name == "test_collection"
        assert collection.metadata == {"description": "Test collection"}

        # Get collection using query
        query = Query()
        retrieved = query.collection(
            info=self._make_info(graphql_context),
            name="test_collection",
        )

        assert retrieved is not None
        assert retrieved.name == "test_collection"
        assert retrieved.id == collection.id

    async def test_list_collections(self, api, graphql_context):
        """Test listing collections"""
        # Create some collections
        mutation = Mutation()
        mutation.create_collection(
            info=self._make_info(graphql_context),
            name="collection1",
        )
        mutation.create_collection(
            info=self._make_info(graphql_context),
            name="collection2",
        )

        # List collections
        query = Query()
        collections = query.collections(
            info=self._make_info(graphql_context),
            limit=10,
            offset=0,
        )

        assert len(collections) >= 2
        names = [c.name for c in collections]
        assert "collection1" in names
        assert "collection2" in names

    async def test_add_and_get_documents(self, api, graphql_context):
        """Test adding and retrieving documents"""
        # Create collection
        mutation = Mutation()
        collection = mutation.create_collection(
            info=self._make_info(graphql_context),
            name="doc_collection",
        )

        # Add documents with embeddings
        embeddings = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        success = mutation.add_documents(
            info=self._make_info(graphql_context),
            collection_name="doc_collection",
            ids=["doc1", "doc2"],
            documents=["First document", "Second document"],
            embeddings=embeddings,
            metadatas=[{"type": "test"}, {"type": "test"}],
        )

        assert success is True

        # Get documents
        query = Query()
        result = query.get(
            info=self._make_info(graphql_context),
            collection_name="doc_collection",
            ids=["doc1", "doc2"],
            include=["documents", "metadatas", "embeddings"],
        )

        assert result is not None
        assert len(result.ids) == 2
        assert "doc1" in result.ids
        assert "doc2" in result.ids
        assert result.documents is not None
        assert "First document" in result.documents

    async def test_query_documents(self, api, graphql_context):
        """Test querying documents by embeddings"""
        # Create collection and add documents
        mutation = Mutation()
        mutation.create_collection(
            info=self._make_info(graphql_context),
            name="query_collection",
        )

        # Add documents with embeddings
        embeddings = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
        mutation.add_documents(
            info=self._make_info(graphql_context),
            collection_name="query_collection",
            ids=["doc1", "doc2", "doc3"],
            documents=["First", "Second", "Third"],
            embeddings=embeddings,
        )

        # Query for similar documents
        query = Query()
        result = query.query(
            info=self._make_info(graphql_context),
            collection_name="query_collection",
            query_embeddings=[[1.0, 0.0, 0.0]],
            n_results=2,
            include=["documents", "distances"],
        )

        assert result is not None
        assert len(result.ids) == 1  # One query
        assert len(result.ids[0]) <= 2  # Up to 2 results
        assert result.documents is not None

    async def test_update_documents(self, api, graphql_context):
        """Test updating documents"""
        # Create collection and add documents
        mutation = Mutation()
        mutation.create_collection(
            info=self._make_info(graphql_context),
            name="update_collection",
        )

        mutation.add_documents(
            info=self._make_info(graphql_context),
            collection_name="update_collection",
            ids=["doc1"],
            documents=["Original document"],
            embeddings=[[1.0, 2.0, 3.0]],
        )

        # Update document
        success = mutation.update_documents(
            info=self._make_info(graphql_context),
            collection_name="update_collection",
            ids=["doc1"],
            documents=["Updated document"],
            metadatas=[{"updated": True}],
        )

        assert success is True

        # Verify update
        query = Query()
        result = query.get(
            info=self._make_info(graphql_context),
            collection_name="update_collection",
            ids=["doc1"],
            include=["documents", "metadatas"],
        )

        assert result is not None
        assert result.documents is not None
        assert "Updated document" in result.documents

    async def test_delete_documents(self, api, graphql_context):
        """Test deleting documents"""
        # Create collection and add documents
        mutation = Mutation()
        mutation.create_collection(
            info=self._make_info(graphql_context),
            name="delete_collection",
        )

        mutation.add_documents(
            info=self._make_info(graphql_context),
            collection_name="delete_collection",
            ids=["doc1", "doc2"],
            documents=["First", "Second"],
            embeddings=[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
        )

        # Delete one document
        success = mutation.delete_documents(
            info=self._make_info(graphql_context),
            collection_name="delete_collection",
            ids=["doc1"],
        )

        assert success is True

        # Verify deletion
        query = Query()
        result = query.get(
            info=self._make_info(graphql_context),
            collection_name="delete_collection",
        )

        assert result is not None
        assert len(result.ids) == 1
        assert "doc2" in result.ids
        assert "doc1" not in result.ids

    async def test_delete_collection(self, api, graphql_context):
        """Test deleting a collection"""
        # Create collection
        mutation = Mutation()
        mutation.create_collection(
            info=self._make_info(graphql_context),
            name="to_delete",
        )

        # Delete collection
        success = mutation.delete_collection(
            info=self._make_info(graphql_context),
            name="to_delete",
        )

        assert success is True

        # Verify deletion
        query = Query()
        result = query.collection(
            info=self._make_info(graphql_context),
            name="to_delete",
        )

        assert result is None

    async def test_document_count(self, api, graphql_context):
        """Test getting document count"""
        # Create collection and add documents
        mutation = Mutation()
        collection = mutation.create_collection(
            info=self._make_info(graphql_context),
            name="count_collection",
        )

        mutation.add_documents(
            info=self._make_info(graphql_context),
            collection_name="count_collection",
            ids=["doc1", "doc2", "doc3"],
            documents=["First", "Second", "Third"],
            embeddings=[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]],
        )

        # Get document count
        count = collection.document_count(info=self._make_info(graphql_context))
        assert count == 3

    async def test_collection_not_found(self, api, graphql_context):
        """Test handling of non-existent collection"""
        query = Query()
        result = query.collection(
            info=self._make_info(graphql_context),
            name="nonexistent",
        )

        assert result is None

    async def test_query_with_where_filter(self, api, graphql_context):
        """Test querying with metadata filters"""
        # Create collection and add documents with metadata
        mutation = Mutation()
        mutation.create_collection(
            info=self._make_info(graphql_context),
            name="filter_collection",
        )

        mutation.add_documents(
            info=self._make_info(graphql_context),
            collection_name="filter_collection",
            ids=["doc1", "doc2", "doc3"],
            documents=["First", "Second", "Third"],
            embeddings=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            metadatas=[
                {"category": "A"},
                {"category": "B"},
                {"category": "A"},
            ],
        )

        # Query with filter
        query = Query()
        result = query.get(
            info=self._make_info(graphql_context),
            collection_name="filter_collection",
            where={"category": "A"},
            include=["documents", "metadatas"],
        )

        assert result is not None
        assert len(result.ids) == 2  # Should get doc1 and doc3

    def _make_info(self, context: Dict[str, Any]):
        """Helper to create a mock Info object for testing"""

        class MockInfo:
            def __init__(self, context):
                self.context = context

        return MockInfo(context)


@pytest.mark.skipif(not GRAPHQL_AVAILABLE, reason="GraphQL dependencies not available")
class TestGraphQLSchema:
    """Test GraphQL schema structure"""

    def test_schema_has_query_type(self):
        """Test that schema has Query type"""
        assert schema.query_type is not None

    def test_schema_has_mutation_type(self):
        """Test that schema has Mutation type"""
        assert schema.mutation_type is not None

    def test_query_has_collection_field(self):
        """Test that Query has collection field"""
        query_type = schema.query_type
        assert hasattr(Query, "collection")

    def test_query_has_collections_field(self):
        """Test that Query has collections field"""
        query_type = schema.query_type
        assert hasattr(Query, "collections")

    def test_mutation_has_create_collection(self):
        """Test that Mutation has create_collection"""
        assert hasattr(Mutation, "create_collection")

    def test_mutation_has_add_documents(self):
        """Test that Mutation has add_documents"""
        assert hasattr(Mutation, "add_documents")
