# Chroma GraphQL API

This module provides a GraphQL interface to Chroma's functionality, enabling type-safe, composable queries with automatic introspection.

## Installation

The GraphQL API requires the Strawberry GraphQL library. Install it with:

```bash
pip install chromadb[dev]
# or
pip install strawberry-graphql[fastapi]
```

## Features

- **Type-Safe Queries**: Leverage GraphQL's strong typing for better developer experience
- **Single Request**: Fetch related data in one query instead of multiple REST calls
- **Flexible Fields**: Request only the fields you need, reducing over-fetching
- **GraphiQL Playground**: Interactive API exploration at `/graphql`
- **Introspection**: Automatically discover API structure and documentation

## Accessing the API

Once the server is running with GraphQL dependencies installed, the GraphQL endpoint is available at:

```
http://localhost:8000/graphql
```

The GraphiQL playground will open in your browser, allowing you to explore the API interactively.

## Schema Overview

### Types

#### Collection
```graphql
type Collection {
  id: String!
  name: String!
  metadata: JSON
  dimension: Int
  tenant: String!
  database: String!
  documentCount: Int!
}
```

#### QueryResult
```graphql
type QueryResult {
  ids: [[String!]!]!
  documents: [[String]]
  metadatas: [[JSON]]
  embeddings: [[[Float!]]]
  distances: [[Float!]]
}
```

#### GetResult
```graphql
type GetResult {
  ids: [String!]!
  documents: [String]
  metadatas: [JSON]
  embeddings: [[Float!]]
  uris: [String]
  data: [JSON]
}
```

### Queries

#### Get a Collection
```graphql
query GetCollection {
  collection(name: "my_collection") {
    id
    name
    metadata
    documentCount
  }
}
```

#### List Collections
```graphql
query ListCollections {
  collections(limit: 10, offset: 0) {
    id
    name
    metadata
    dimension
  }
}
```

#### Get Documents
```graphql
query GetDocuments {
  get(
    collectionName: "my_collection"
    ids: ["doc1", "doc2"]
    include: ["documents", "metadatas"]
  ) {
    ids
    documents
    metadatas
  }
}
```

#### Query Similar Documents
```graphql
query QueryDocuments {
  query(
    collectionName: "my_collection"
    queryEmbeddings: [[1.0, 2.0, 3.0]]
    nResults: 5
    include: ["documents", "distances", "metadatas"]
  ) {
    ids
    documents
    distances
    metadatas
  }
}
```

#### Query with Filters
```graphql
query QueryWithFilter {
  get(
    collectionName: "my_collection"
    where: {category: "science"}
    limit: 10
    include: ["documents", "metadatas"]
  ) {
    ids
    documents
    metadatas
  }
}
```

### Mutations

#### Create Collection
```graphql
mutation CreateCollection {
  createCollection(
    name: "new_collection"
    metadata: {description: "My new collection"}
  ) {
    id
    name
    metadata
  }
}
```

#### Add Documents
```graphql
mutation AddDocuments {
  addDocuments(
    collectionName: "my_collection"
    ids: ["doc1", "doc2"]
    documents: ["First document", "Second document"]
    embeddings: [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
    metadatas: [{type: "text"}, {type: "text"}]
  )
}
```

#### Update Documents
```graphql
mutation UpdateDocuments {
  updateDocuments(
    collectionName: "my_collection"
    ids: ["doc1"]
    documents: ["Updated document"]
    metadatas: [{updated: true}]
  )
}
```

#### Delete Documents
```graphql
mutation DeleteDocuments {
  deleteDocuments(
    collectionName: "my_collection"
    ids: ["doc1", "doc2"]
  )
}
```

#### Delete Collection
```graphql
mutation DeleteCollection {
  deleteCollection(name: "old_collection")
}
```

## Multi-Tenant Support

All queries and mutations support `tenant` and `database` parameters:

```graphql
query GetCollectionInTenant {
  collection(
    name: "my_collection"
    tenant: "my_tenant"
    database: "my_database"
  ) {
    id
    name
  }
}
```

## Example: Complete Workflow

```graphql
# 1. Create a collection
mutation {
  createCollection(
    name: "documents"
    metadata: {description: "Document collection"}
  ) {
    id
    name
  }
}

# 2. Add documents
mutation {
  addDocuments(
    collectionName: "documents"
    ids: ["doc1", "doc2", "doc3"]
    documents: [
      "Machine learning is fascinating"
      "Deep learning uses neural networks"
      "Natural language processing"
    ]
    embeddings: [
      [1.0, 0.5, 0.3]
      [1.0, 0.6, 0.2]
      [0.8, 0.4, 0.7]
    ]
    metadatas: [
      {topic: "ML"}
      {topic: "DL"}
      {topic: "NLP"}
    ]
  )
}

# 3. Query similar documents
query {
  query(
    collectionName: "documents"
    queryEmbeddings: [[1.0, 0.5, 0.3]]
    nResults: 2
    include: ["documents", "distances", "metadatas"]
  ) {
    ids
    documents
    distances
    metadatas
  }
}

# 4. Get specific documents with filter
query {
  get(
    collectionName: "documents"
    where: {topic: "ML"}
    include: ["documents", "metadatas"]
  ) {
    ids
    documents
    metadatas
  }
}
```

## TypeScript Client Example

You can use Apollo Client or any GraphQL client to connect:

```typescript
import { ApolloClient, InMemoryCache, gql } from '@apollo/client';

const client = new ApolloClient({
  uri: 'http://localhost:8000/graphql',
  cache: new InMemoryCache()
});

// Query collections
const GET_COLLECTIONS = gql`
  query GetCollections {
    collections {
      id
      name
      documentCount
    }
  }
`;

const { data } = await client.query({ query: GET_COLLECTIONS });
console.log(data.collections);
```

## Python Client Example

Using `gql` library:

```python
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

transport = RequestsHTTPTransport(url='http://localhost:8000/graphql')
client = Client(transport=transport, fetch_schema_from_transport=True)

# Query collections
query = gql('''
    query {
        collections {
            id
            name
            documentCount
        }
    }
''')

result = client.execute(query)
print(result)
```

## Limitations and Notes

1. **Embedding Functions**: The GraphQL API requires embeddings to be provided directly. It does not support automatic embedding generation via `query_texts`. Use `query_embeddings` instead.

2. **Authentication**: The GraphQL endpoint currently uses the same authentication mechanisms as the REST API. Ensure proper authentication headers are included in requests.

3. **Rate Limiting**: The same rate limits apply to GraphQL as to REST endpoints.

4. **Subscriptions**: Real-time subscriptions are not yet implemented but are planned for future releases.

## Architecture

The GraphQL layer is built on top of the existing Chroma ServerAPI:

```
GraphQL Request
    ↓
Strawberry Resolvers
    ↓
ServerAPI (chromadb.api.ServerAPI)
    ↓
Segment API / Storage
```

This ensures:
- All business logic remains in the core API
- GraphQL is a thin presentation layer
- REST and GraphQL APIs have consistent behavior
- Easy maintenance and testing

## Error Handling

Errors are returned as GraphQL errors with descriptive messages:

```json
{
  "errors": [
    {
      "message": "Collection 'nonexistent' not found",
      "path": ["collection"],
      "locations": [{"line": 2, "column": 3}]
    }
  ],
  "data": {
    "collection": null
  }
}
```

## Performance Considerations

1. **Field Selection**: Only request fields you need to minimize data transfer
2. **Batching**: Use a single query with multiple operations instead of separate requests
3. **Caching**: GraphQL responses can be cached based on query structure
4. **N+1 Prevention**: The `documentCount` field is resolved efficiently per collection

## Future Enhancements

- **Subscriptions**: Real-time updates when collections or documents change
- **DataLoader**: Batch and cache operations to prevent N+1 queries
- **Cursor-based Pagination**: More efficient pagination for large result sets
- **Field-level Authorization**: Fine-grained access control
- **Generated TypeScript Types**: Automatic client type generation
- **Federation**: Support for GraphQL Federation in distributed deployments

## Contributing

To add new fields or operations:

1. Define the GraphQL type in `chromadb/server/graphql/__init__.py`
2. Add resolver methods with `@strawberry.field` or `@strawberry.mutation`
3. Access the API via `info.context["api"]`
4. Add tests in `chromadb/test/test_graphql.py`
5. Update this documentation

## References

- [Strawberry GraphQL Documentation](https://strawberry.rocks/)
- [GraphQL Specification](https://spec.graphql.org/)
- [GraphQL Best Practices](https://graphql.org/learn/best-practices/)
- [RFC-0008: GraphQL API Layer](../../analysis-output/rfcs/RFC-0008-graphql-api-layer.md)
