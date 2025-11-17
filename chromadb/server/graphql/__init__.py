"""
GraphQL API Layer for Chroma

This module provides a GraphQL interface to Chroma's functionality,
enabling type-safe, composable queries with automatic introspection.
"""

import strawberry
from strawberry.fastapi import GraphQLRouter
from typing import List, Optional, Any, cast
from uuid import UUID as PyUUID

from chromadb.api import ServerAPI
from chromadb.config import DEFAULT_DATABASE, DEFAULT_TENANT
from chromadb.types import Collection as CollectionModel
from chromadb.api.types import QueryResult as APIQueryResult, GetResult as APIGetResult
from chromadb.errors import ChromaError
import logging

logger = logging.getLogger(__name__)


# GraphQL Types
@strawberry.type
class Collection:
    """A collection in Chroma"""

    id: str
    name: str
    metadata: Optional[strawberry.scalars.JSON] = None
    dimension: Optional[int] = None
    tenant: str
    database: str

    @strawberry.field
    def document_count(self, info: strawberry.types.Info) -> int:
        """Get the number of documents in this collection"""
        try:
            api: ServerAPI = info.context["api"]
            collection_id = PyUUID(self.id)
            count = api._count(
                collection_id=collection_id, tenant=self.tenant, database=self.database
            )
            return count
        except Exception as e:
            logger.error(f"Error getting document count: {e}")
            return 0


@strawberry.type
class Document:
    """A document with its embedding and metadata"""

    id: str
    content: Optional[str] = None
    metadata: Optional[strawberry.scalars.JSON] = None
    embedding: Optional[List[float]] = None


@strawberry.type
class QueryResult:
    """Result from a query operation"""

    ids: List[List[str]]
    documents: Optional[List[Optional[List[Optional[str]]]]] = None
    metadatas: Optional[List[Optional[List[Optional[strawberry.scalars.JSON]]]]] = None
    embeddings: Optional[List[Optional[List[Optional[List[float]]]]]] = None
    distances: Optional[List[Optional[List[float]]]] = None


@strawberry.type
class GetResult:
    """Result from a get operation"""

    ids: List[str]
    documents: Optional[List[Optional[str]]] = None
    metadatas: Optional[List[Optional[strawberry.scalars.JSON]]] = None
    embeddings: Optional[List[Optional[List[float]]]] = None
    uris: Optional[List[Optional[str]]] = None
    data: Optional[List[Optional[strawberry.scalars.JSON]]] = None


@strawberry.input
class WhereFilter:
    """Filter for querying documents"""

    # This is a simplified version - in production you'd want more structured filters
    filter_json: strawberry.scalars.JSON


# Query Root
@strawberry.type
class Query:
    """Root query type for GraphQL API"""

    @strawberry.field
    def collection(
        self,
        info: strawberry.types.Info,
        name: str,
        tenant: str = DEFAULT_TENANT,
        database: str = DEFAULT_DATABASE,
    ) -> Optional[Collection]:
        """Get a collection by name"""
        try:
            api: ServerAPI = info.context["api"]
            col = api.get_collection(name=name, tenant=tenant, database=database)
            return Collection(
                id=str(col.id),
                name=col.name,
                metadata=col.metadata,
                dimension=col.dimension,
                tenant=col.tenant,
                database=col.database,
            )
        except ChromaError as e:
            logger.error(f"Error getting collection: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting collection: {e}")
            return None

    @strawberry.field
    def collections(
        self,
        info: strawberry.types.Info,
        limit: int = 10,
        offset: int = 0,
        tenant: str = DEFAULT_TENANT,
        database: str = DEFAULT_DATABASE,
    ) -> List[Collection]:
        """List all collections"""
        try:
            api: ServerAPI = info.context["api"]
            cols = api.list_collections(
                limit=limit, offset=offset, tenant=tenant, database=database
            )
            return [
                Collection(
                    id=str(col.id),
                    name=col.name,
                    metadata=col.metadata,
                    dimension=col.dimension,
                    tenant=col.tenant,
                    database=col.database,
                )
                for col in cols
            ]
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return []

    @strawberry.field
    def query(
        self,
        info: strawberry.types.Info,
        collection_name: str,
        query_embeddings: Optional[List[List[float]]] = None,
        query_texts: Optional[List[str]] = None,
        n_results: int = 10,
        where: Optional[strawberry.scalars.JSON] = None,
        where_document: Optional[strawberry.scalars.JSON] = None,
        include: Optional[List[str]] = None,
        tenant: str = DEFAULT_TENANT,
        database: str = DEFAULT_DATABASE,
    ) -> Optional[QueryResult]:
        """Query documents from a collection"""
        try:
            api: ServerAPI = info.context["api"]

            # Get collection first
            col = api.get_collection(
                name=collection_name, tenant=tenant, database=database
            )

            # Note: query_texts would require embedding function which is not available
            # in the server API directly. In a real implementation, you'd need to
            # handle this differently or require embeddings to be passed.
            if query_texts and not query_embeddings:
                raise ValueError(
                    "query_texts requires an embedding function. Please provide query_embeddings instead."
                )

            # Convert embeddings to numpy array format expected by API
            import numpy as np

            np_embeddings = (
                np.array(query_embeddings) if query_embeddings else None
            )

            # Include defaults
            if include is None:
                include = ["metadatas", "documents", "distances"]

            result: APIQueryResult = api._query(
                collection_id=col.id,
                query_embeddings=np_embeddings,
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=include,
                tenant=tenant,
                database=database,
            )

            # Convert numpy arrays to lists for JSON serialization
            return QueryResult(
                ids=result["ids"],
                documents=result.get("documents"),
                metadatas=result.get("metadatas"),
                embeddings=[
                    [embedding.tolist() if embedding is not None else None for embedding in result_row]
                    if result_row is not None
                    else None
                    for result_row in result["embeddings"]
                ]
                if result.get("embeddings")
                else None,
                distances=result.get("distances"),
            )
        except Exception as e:
            logger.error(f"Error querying collection: {e}")
            raise

    @strawberry.field
    def get(
        self,
        info: strawberry.types.Info,
        collection_name: str,
        ids: Optional[List[str]] = None,
        where: Optional[strawberry.scalars.JSON] = None,
        where_document: Optional[strawberry.scalars.JSON] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        include: Optional[List[str]] = None,
        tenant: str = DEFAULT_TENANT,
        database: str = DEFAULT_DATABASE,
    ) -> Optional[GetResult]:
        """Get documents from a collection"""
        try:
            api: ServerAPI = info.context["api"]

            # Get collection first
            col = api.get_collection(
                name=collection_name, tenant=tenant, database=database
            )

            # Include defaults
            if include is None:
                include = ["metadatas", "documents"]

            result: APIGetResult = api._get(
                collection_id=col.id,
                ids=ids,
                where=where,
                limit=limit,
                offset=offset,
                where_document=where_document,
                include=include,
                tenant=tenant,
                database=database,
            )

            # Convert numpy arrays to lists for JSON serialization
            return GetResult(
                ids=result["ids"],
                documents=result.get("documents"),
                metadatas=result.get("metadatas"),
                embeddings=[
                    embedding.tolist() if embedding is not None else None
                    for embedding in result["embeddings"]
                ]
                if result.get("embeddings")
                else None,
                uris=result.get("uris"),
                data=result.get("data"),
            )
        except Exception as e:
            logger.error(f"Error getting documents: {e}")
            raise


# Mutation Root
@strawberry.type
class Mutation:
    """Root mutation type for GraphQL API"""

    @strawberry.mutation
    def create_collection(
        self,
        info: strawberry.types.Info,
        name: str,
        metadata: Optional[strawberry.scalars.JSON] = None,
        tenant: str = DEFAULT_TENANT,
        database: str = DEFAULT_DATABASE,
    ) -> Collection:
        """Create a new collection"""
        try:
            api: ServerAPI = info.context["api"]
            col = api.create_collection(
                name=name,
                metadata=metadata,
                tenant=tenant,
                database=database,
            )
            return Collection(
                id=str(col.id),
                name=col.name,
                metadata=col.metadata,
                dimension=col.dimension,
                tenant=col.tenant,
                database=col.database,
            )
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            raise

    @strawberry.mutation
    def delete_collection(
        self,
        info: strawberry.types.Info,
        name: str,
        tenant: str = DEFAULT_TENANT,
        database: str = DEFAULT_DATABASE,
    ) -> bool:
        """Delete a collection"""
        try:
            api: ServerAPI = info.context["api"]
            api.delete_collection(name=name, tenant=tenant, database=database)
            return True
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            return False

    @strawberry.mutation
    def add_documents(
        self,
        info: strawberry.types.Info,
        collection_name: str,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Optional[strawberry.scalars.JSON]]] = None,
        embeddings: Optional[List[List[float]]] = None,
        tenant: str = DEFAULT_TENANT,
        database: str = DEFAULT_DATABASE,
    ) -> bool:
        """Add documents to a collection"""
        try:
            api: ServerAPI = info.context["api"]

            # Get collection first
            col = api.get_collection(
                name=collection_name, tenant=tenant, database=database
            )

            # Convert embeddings to numpy array format
            import numpy as np

            np_embeddings = np.array(embeddings) if embeddings else None

            api._add(
                collection_id=col.id,
                ids=ids,
                embeddings=np_embeddings,
                metadatas=metadatas,
                documents=documents,
                tenant=tenant,
                database=database,
            )
            return True
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            return False

    @strawberry.mutation
    def update_documents(
        self,
        info: strawberry.types.Info,
        collection_name: str,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Optional[strawberry.scalars.JSON]]] = None,
        embeddings: Optional[List[List[float]]] = None,
        tenant: str = DEFAULT_TENANT,
        database: str = DEFAULT_DATABASE,
    ) -> bool:
        """Update documents in a collection"""
        try:
            api: ServerAPI = info.context["api"]

            # Get collection first
            col = api.get_collection(
                name=collection_name, tenant=tenant, database=database
            )

            # Convert embeddings to numpy array format
            import numpy as np

            np_embeddings = np.array(embeddings) if embeddings else None

            api._update(
                collection_id=col.id,
                ids=ids,
                embeddings=np_embeddings,
                metadatas=metadatas,
                documents=documents,
                tenant=tenant,
                database=database,
            )
            return True
        except Exception as e:
            logger.error(f"Error updating documents: {e}")
            return False

    @strawberry.mutation
    def delete_documents(
        self,
        info: strawberry.types.Info,
        collection_name: str,
        ids: Optional[List[str]] = None,
        where: Optional[strawberry.scalars.JSON] = None,
        where_document: Optional[strawberry.scalars.JSON] = None,
        tenant: str = DEFAULT_TENANT,
        database: str = DEFAULT_DATABASE,
    ) -> bool:
        """Delete documents from a collection"""
        try:
            api: ServerAPI = info.context["api"]

            # Get collection first
            col = api.get_collection(
                name=collection_name, tenant=tenant, database=database
            )

            api._delete(
                collection_id=col.id,
                ids=ids,
                where=where,
                where_document=where_document,
                tenant=tenant,
                database=database,
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return False


# Create the schema
schema = strawberry.Schema(query=Query, mutation=Mutation)


# Create GraphQL router factory
def create_graphql_router(api: ServerAPI) -> GraphQLRouter:
    """
    Create a GraphQL router with the given API instance.

    Args:
        api: The ServerAPI instance to use for GraphQL operations

    Returns:
        A configured GraphQLRouter instance
    """

    async def get_context():
        return {"api": api}

    return GraphQLRouter(
        schema,
        context_getter=get_context,
        graphiql=True,  # Enable GraphiQL playground
    )
