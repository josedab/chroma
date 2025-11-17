"""
Example usage of the Chroma GraphQL API

This file demonstrates how to use the GraphQL API with various clients.
"""

# Example 1: Using requests library
def example_with_requests():
    """Example using basic requests library"""
    import requests
    import json

    url = "http://localhost:8000/graphql"

    # Query to get collections
    query = """
    query GetCollections {
        collections(limit: 10) {
            id
            name
            metadata
            documentCount
        }
    }
    """

    response = requests.post(url, json={"query": query})
    data = response.json()
    print("Collections:", json.dumps(data, indent=2))


# Example 2: Create collection and add documents
def example_create_and_add():
    """Example creating collection and adding documents"""
    import requests

    url = "http://localhost:8000/graphql"

    # Step 1: Create collection
    create_mutation = """
    mutation CreateCollection {
        createCollection(
            name: "my_documents"
            metadata: {description: "My document collection"}
        ) {
            id
            name
            metadata
        }
    }
    """

    response = requests.post(url, json={"query": create_mutation})
    print("Created collection:", response.json())

    # Step 2: Add documents
    add_mutation = """
    mutation AddDocuments {
        addDocuments(
            collectionName: "my_documents"
            ids: ["doc1", "doc2", "doc3"]
            documents: [
                "Machine learning is a subset of AI"
                "Deep learning uses neural networks"
                "Natural language processing enables computers to understand text"
            ]
            embeddings: [
                [1.0, 0.5, 0.3, 0.2]
                [0.9, 0.6, 0.2, 0.1]
                [0.8, 0.4, 0.7, 0.3]
            ]
            metadatas: [
                {topic: "ML", category: "AI"}
                {topic: "DL", category: "AI"}
                {topic: "NLP", category: "AI"}
            ]
        )
    }
    """

    response = requests.post(url, json={"query": add_mutation})
    print("Added documents:", response.json())


# Example 3: Query similar documents
def example_query_documents():
    """Example querying similar documents"""
    import requests

    url = "http://localhost:8000/graphql"

    query = """
    query QuerySimilar {
        query(
            collectionName: "my_documents"
            queryEmbeddings: [[1.0, 0.5, 0.3, 0.2]]
            nResults: 2
            include: ["documents", "distances", "metadatas"]
        ) {
            ids
            documents
            distances
            metadatas
        }
    }
    """

    response = requests.post(url, json={"query": query})
    print("Query results:", response.json())


# Example 4: Using with Python GQL client
def example_with_gql_client():
    """Example using the gql library for Python"""
    try:
        from gql import gql, Client
        from gql.transport.requests import RequestsHTTPTransport

        # Create transport
        transport = RequestsHTTPTransport(
            url="http://localhost:8000/graphql",
            use_json=True,
        )

        # Create client
        client = Client(
            transport=transport,
            fetch_schema_from_transport=True,
        )

        # Execute query
        query = gql(
            """
            query {
                collections {
                    id
                    name
                    documentCount
                }
            }
        """
        )

        result = client.execute(query)
        print("Collections:", result)

        # Execute mutation
        mutation = gql(
            """
            mutation {
                createCollection(
                    name: "test_collection"
                    metadata: {type: "test"}
                ) {
                    id
                    name
                }
            }
        """
        )

        result = client.execute(mutation)
        print("Created:", result)

    except ImportError:
        print("gql library not installed. Install with: pip install gql[requests]")


# Example 5: Get documents with filters
def example_get_with_filters():
    """Example getting documents with metadata filters"""
    import requests

    url = "http://localhost:8000/graphql"

    query = """
    query GetFiltered {
        get(
            collectionName: "my_documents"
            where: {category: "AI", topic: "ML"}
            include: ["documents", "metadatas"]
        ) {
            ids
            documents
            metadatas
        }
    }
    """

    response = requests.post(url, json={"query": query})
    print("Filtered results:", response.json())


# Example 6: Update and delete operations
def example_update_and_delete():
    """Example updating and deleting documents"""
    import requests

    url = "http://localhost:8000/graphql"

    # Update documents
    update_mutation = """
    mutation UpdateDocs {
        updateDocuments(
            collectionName: "my_documents"
            ids: ["doc1"]
            documents: ["Updated: Machine learning is a subset of AI"]
            metadatas: [{topic: "ML", category: "AI", updated: true}]
        )
    }
    """

    response = requests.post(url, json={"query": update_mutation})
    print("Update result:", response.json())

    # Delete documents
    delete_mutation = """
    mutation DeleteDocs {
        deleteDocuments(
            collectionName: "my_documents"
            ids: ["doc2"]
        )
    }
    """

    response = requests.post(url, json={"query": delete_mutation})
    print("Delete result:", response.json())


# Example 7: Multi-tenant usage
def example_multi_tenant():
    """Example using multiple tenants and databases"""
    import requests

    url = "http://localhost:8000/graphql"

    # Create collection in specific tenant/database
    mutation = """
    mutation CreateInTenant {
        createCollection(
            name: "tenant_collection"
            tenant: "my_tenant"
            database: "my_database"
            metadata: {owner: "my_tenant"}
        ) {
            id
            name
            tenant
            database
        }
    }
    """

    response = requests.post(url, json={"query": mutation})
    print("Created in tenant:", response.json())

    # Query from specific tenant/database
    query = """
    query GetFromTenant {
        collection(
            name: "tenant_collection"
            tenant: "my_tenant"
            database: "my_database"
        ) {
            id
            name
            tenant
            database
            documentCount
        }
    }
    """

    response = requests.post(url, json={"query": query})
    print("Retrieved from tenant:", response.json())


# Example 8: Complex query with multiple operations
def example_complex_query():
    """Example with multiple operations in one request"""
    import requests

    url = "http://localhost:8000/graphql"

    # Multiple queries in one request
    query = """
    query ComplexQuery {
        allCollections: collections(limit: 5) {
            id
            name
            documentCount
        }

        specificCollection: collection(name: "my_documents") {
            id
            name
            metadata
            dimension
        }

        documents: get(
            collectionName: "my_documents"
            limit: 5
            include: ["documents", "metadatas"]
        ) {
            ids
            documents
            metadatas
        }
    }
    """

    response = requests.post(url, json={"query": query})
    print("Complex query result:", response.json())


# Example 9: Error handling
def example_error_handling():
    """Example showing error handling"""
    import requests

    url = "http://localhost:8000/graphql"

    # Try to get non-existent collection
    query = """
    query GetNonExistent {
        collection(name: "does_not_exist") {
            id
            name
        }
    }
    """

    response = requests.post(url, json={"query": query})
    result = response.json()

    if "errors" in result:
        print("Errors:", result["errors"])
    else:
        print("Data:", result["data"])


# Example 10: Batch operations
def example_batch_operations():
    """Example performing multiple mutations in sequence"""
    import requests

    url = "http://localhost:8000/graphql"

    # Create multiple collections
    for i in range(3):
        mutation = f"""
        mutation {{
            createCollection(
                name: "batch_collection_{i}"
                metadata: {{index: {i}}}
            ) {{
                id
                name
            }}
        }}
        """

        response = requests.post(url, json={"query": mutation})
        print(f"Created collection {i}:", response.json())


if __name__ == "__main__":
    print("Chroma GraphQL API Examples")
    print("=" * 50)
    print()
    print("Uncomment the examples you want to run:")
    print()

    # Uncomment to run examples:
    # example_with_requests()
    # example_create_and_add()
    # example_query_documents()
    # example_with_gql_client()
    # example_get_with_filters()
    # example_update_and_delete()
    # example_multi_tenant()
    # example_complex_query()
    # example_error_handling()
    # example_batch_operations()

    print("Note: Make sure the Chroma server is running with GraphQL support:")
    print("  pip install chromadb[dev]")
    print("  chroma run")
