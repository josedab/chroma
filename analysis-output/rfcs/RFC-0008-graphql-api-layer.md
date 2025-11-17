# RFC-0008: GraphQL API Layer

**Status:** Draft
**Author:** Claude Code Analysis
**Created:** 2025-11-17
**Commit Base:** 091f8bd5c553f8267c48664e98fb32215055f58e

---

## Summary

Add a GraphQL API layer alongside the existing REST API to provide type-safe, composable queries with automatic introspection for web clients. This enables better developer experience for frontend applications while maintaining REST API for backwards compatibility.

---

## Motivation

### Current State

Chroma uses FastAPI with REST endpoints:

**File:** `/home/user/chroma/chromadb/server/fastapi/__init__.py`

```python
from fastapi import FastAPI

@app.post("/api/v1/collections/{collection_id}/query")
async def query_collection(collection_id: str, request: QueryEmbedding):
    # REST endpoint
```

### Problems with REST API for Web Clients

1. **Over-fetching:** REST returns fixed responses, clients get unwanted fields
2. **Under-fetching:** Need multiple requests to get related data
3. **No Type Safety:** JavaScript clients lose type information
4. **No Introspection:** Can't explore API structure programmatically

### GraphQL Benefits

1. **Precise Queries:** Request only needed fields
2. **Single Request:** Fetch related data in one query
3. **Type Safety:** Auto-generate TypeScript types
4. **Introspection:** GraphQL Playground for exploration
5. **Real-time:** Subscriptions for live updates

---

## Detailed Design

### GraphQL Schema

```graphql
# Core types
type Collection {
  id: ID!
  name: String!
  metadata: JSON
  dimension: Int
  documentCount: Int!
  
  # Relationships
  documents(
    limit: Int = 10
    offset: Int = 0
    where: JSON
  ): [Document!]!
}

type Document {
  id: ID!
  content: String
  metadata: JSON
  embedding: [Float!]
  
  # Belongs to collection
  collection: Collection!
}

type QueryResult {
  ids: [[String!]!]!
  documents: [[String]]
  metadatas: [[JSON]]
  embeddings: [[[Float!]]]
  distances: [[Float!]]
}

# Root queries
type Query {
  # Get single collection
  collection(name: String!): Collection
  
  # List collections
  collections(
    limit: Int = 10
    offset: Int = 0
  ): [Collection!]!
  
  # Query documents
  query(
    collectionName: String!
    queryEmbeddings: [[Float!]!]
    queryTexts: [String!]
    nResults: Int = 10
    where: JSON
    whereDocument: JSON
    include: [String!]
  ): QueryResult!
}

# Root mutations
type Mutation {
  # Create collection
  createCollection(
    name: String!
    metadata: JSON
  ): Collection!
  
  # Add documents
  addDocuments(
    collectionName: String!
    ids: [String!]!
    documents: [String!]
    metadatas: [JSON]
    embeddings: [[Float!]]
  ): Boolean!
  
  # Delete documents
  deleteDocuments(
    collectionName: String!
    ids: [String!]
  ): Boolean!
}

# Real-time subscriptions
type Subscription {
  # Subscribe to collection changes
  collectionUpdated(name: String!): Collection!
}
```

### Technology Stack

**Framework:** Strawberry (Python GraphQL library)

```python
# Install
pip install strawberry-graphql[fastapi]
```

**Why Strawberry:**
- Native FastAPI integration
- Type-safe with Python type hints
- Async/await support
- Good performance

### Implementation

**File:** Create `chromadb/server/graphql/__init__.py`

```python
import strawberry
from strawberry.fastapi import GraphQLRouter
from typing import List, Optional
import chromadb

@strawberry.type
class Collection:
    id: str
    name: str
    metadata: Optional[strawberry.scalars.JSON]
    dimension: Optional[int]

    @strawberry.field
    def document_count(self) -> int:
        # Resolve count dynamically
        return get_collection_count(self.id)

@strawberry.type
class Query:
    @strawberry.field
    def collection(self, name: str) -> Optional[Collection]:
        """Get collection by name"""
        client = chromadb.Client()
        try:
            col = client.get_collection(name)
            return Collection(
                id=str(col.id),
                name=col.name,
                metadata=col.metadata,
                dimension=col.dimension
            )
        except:
            return None

    @strawberry.field
    def collections(
        self,
        limit: int = 10,
        offset: int = 0
    ) -> List[Collection]:
        """List all collections"""
        client = chromadb.Client()
        cols = client.list_collections()
        return [
            Collection(
                id=str(col.id),
                name=col.name,
                metadata=col.metadata,
                dimension=col.dimension
            )
            for col in cols[offset:offset+limit]
        ]

@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_collection(
        self,
        name: str,
        metadata: Optional[strawberry.scalars.JSON] = None
    ) -> Collection:
        """Create new collection"""
        client = chromadb.Client()
        col = client.create_collection(name, metadata=metadata)
        return Collection(
            id=str(col.id),
            name=col.name,
            metadata=col.metadata,
            dimension=col.dimension
        )

schema = strawberry.Schema(query=Query, mutation=Mutation)

# Mount on FastAPI
graphql_app = GraphQLRouter(schema)
```

**File:** Update `chromadb/server/fastapi/__init__.py`

```python
from chromadb.server.graphql import graphql_app

# Add GraphQL endpoint
app.include_router(graphql_app, prefix="/graphql")
```

---

## Implementation Plan

### Milestone 1: Core Schema (3 dev-days)
- [ ] Define GraphQL schema
- [ ] Setup Strawberry
- [ ] Implement Query resolvers
- [ ] Add to FastAPI

### Milestone 2: Mutations (3 dev-days)
- [ ] Implement Mutation resolvers
- [ ] Add validation
- [ ] Error handling
- [ ] Integration tests

### Milestone 3: Advanced Features (2 dev-days)
- [ ] Subscriptions for real-time updates
- [ ] DataLoader for N+1 query optimization
- [ ] Pagination (cursor-based)
- [ ] Field-level authorization

### Milestone 4: Tooling (2 dev-days)
- [ ] GraphQL Playground
- [ ] Auto-generate TypeScript types
- [ ] JavaScript client library
- [ ] Example frontend app

---

## Example Usage

### Query Collections

```graphql
# Get collection with document count
query GetCollection {
  collection(name: "my_docs") {
    id
    name
    metadata
    documentCount
  }
}
```

Response:
```json
{
  "data": {
    "collection": {
      "id": "123",
      "name": "my_docs",
      "metadata": {"description": "My documents"},
      "documentCount": 1000
    }
  }
}
```

### Query Documents

```graphql
query SearchDocuments {
  query(
    collectionName: "my_docs"
    queryTexts: ["machine learning"]
    nResults: 5
    include: ["documents", "metadatas", "distances"]
  ) {
    ids
    documents
    distances
    metadatas
  }
}
```

### Create Collection and Add Documents

```graphql
mutation CreateAndPopulate {
  createCollection(
    name: "new_collection"
    metadata: {description: "Test collection"}
  ) {
    id
    name
  }
  
  addDocuments(
    collectionName: "new_collection"
    ids: ["doc1", "doc2"]
    documents: ["First doc", "Second doc"]
  )
}
```

### TypeScript Client (Auto-Generated)

```typescript
// Generated from GraphQL schema
import { gql, useQuery } from '@apollo/client';

const GET_COLLECTION = gql`
  query GetCollection($name: String!) {
    collection(name: $name) {
      id
      name
      documentCount
    }
  }
`;

function CollectionView({ name }: { name: string }) {
  const { loading, error, data } = useQuery(GET_COLLECTION, {
    variables: { name }
  });

  if (loading) return <p>Loading...</p>;
  if (error) return <p>Error: {error.message}</p>;

  return (
    <div>
      <h1>{data.collection.name}</h1>
      <p>Documents: {data.collection.documentCount}</p>
    </div>
  );
}
```

---

## Backwards Compatibility

- REST API unchanged
- GraphQL is additive (new `/graphql` endpoint)
- Clients choose REST or GraphQL

---

## Alternatives Considered

### Alternative 1: Replace REST with GraphQL
**Rejected:** Breaking change, REST has wide adoption

### Alternative 2: Use tRPC Instead
**Rejected:** TypeScript-only, not language-agnostic like GraphQL

### Alternative 3: Expand REST with JSON:API
**Rejected:** Still requires multiple requests for related data

---

## Success Criteria

- [ ] GraphQL Playground accessible
- [ ] Query, Mutation, Subscription work
- [ ] TypeScript types auto-generated
- [ ] Performance comparable to REST

---

## Effort Estimation

| Phase | Dev-Days |
|-------|----------|
| Core schema | 3 |
| Mutations | 3 |
| Advanced features | 2 |
| Tooling | 2 |
| **Total** | **10** |

---

## References

- [Strawberry GraphQL](https://strawberry.rocks/)
- [GraphQL Best Practices](https://graphql.org/learn/best-practices/)
- [Apollo Client](https://www.apollographql.com/docs/react/)

---

## Revision History

- **v1.0** (2025-11-17): Initial RFC
