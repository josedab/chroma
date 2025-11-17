#!/usr/bin/env python3
"""
Example script demonstrating Chroma observability metrics.

This script:
1. Creates a Chroma client with observability enabled
2. Performs various operations (create collection, add documents, query)
3. Metrics are automatically tracked and exported to the OTEL collector
"""

import chromadb
import time
import random
import string

def generate_random_text(length=100):
    """Generate random text for testing."""
    return ''.join(random.choices(string.ascii_lowercase + ' ', k=length))

def main():
    print("Chroma Observability Example")
    print("=" * 50)

    # Create a Chroma client
    # In production, set these via environment variables:
    # CHROMA_OTEL_ENABLED=true
    # CHROMA_OTEL_COLLECTION_ENDPOINT=http://otel-collector:4317
    # CHROMA_OTEL_SERVICE_NAME=chroma
    client = chromadb.Client()

    print("\n1. Creating collection...")
    collection = client.create_collection(
        name="test_collection",
        metadata={"description": "Test collection for observability"}
    )
    print(f"   ✓ Collection created: {collection.name}")

    # Metrics tracked:
    # - chroma_collection_count +1
    # - chroma_segment_count +2 (vector + metadata)

    print("\n2. Adding documents...")
    num_docs = 100
    documents = [generate_random_text() for _ in range(num_docs)]
    ids = [f"doc_{i}" for i in range(num_docs)]
    metadatas = [{"index": i, "type": "test"} for i in range(num_docs)]

    collection.add(
        documents=documents,
        ids=ids,
        metadatas=metadatas
    )
    print(f"   ✓ Added {num_docs} documents")

    # Metrics tracked:
    # - chroma_collection_documents +100
    # - chroma_segment_records +100

    print("\n3. Performing queries...")
    for i in range(10):
        start = time.time()
        results = collection.query(
            query_texts=["sample query text"],
            n_results=5
        )
        duration = time.time() - start
        print(f"   Query {i+1}: {duration:.3f}s - {len(results['ids'][0])} results")
        time.sleep(0.1)

    # Metrics tracked for each query:
    # - chroma_query_total +1
    # - chroma_query_duration (histogram)
    # - chroma_query_result_size (histogram)

    print("\n4. Performing get operations...")
    for i in range(5):
        start = time.time()
        results = collection.get(
            ids=[f"doc_{i}"],
            include=["documents", "metadatas"]
        )
        duration = time.time() - start
        print(f"   Get {i+1}: {duration:.3f}s")
        time.sleep(0.1)

    # Metrics tracked for each get:
    # - chroma_query_total +1
    # - chroma_query_duration (histogram)

    print("\n5. Checking collection stats...")
    count = collection.count()
    print(f"   ✓ Collection has {count} documents")

    print("\n6. Cleaning up...")
    client.delete_collection(name="test_collection")
    print("   ✓ Collection deleted")

    # Metrics tracked:
    # - chroma_collection_count -1
    # - chroma_segment_count -2

    print("\n" + "=" * 50)
    print("Example completed!")
    print("\nTo view metrics:")
    print("1. Ensure the observability stack is running:")
    print("   cd observability && docker-compose up -d")
    print("\n2. Open Grafana: http://localhost:3000")
    print("   - Username: admin")
    print("   - Password: admin")
    print("\n3. Navigate to Dashboards → Chroma → Chroma Overview")
    print("\n4. Or query Prometheus directly: http://localhost:9090")
    print("   Example queries:")
    print("   - chroma_query_total")
    print("   - histogram_quantile(0.95, rate(chroma_query_duration_bucket[5m]))")
    print("   - chroma_segment_count")

if __name__ == "__main__":
    main()
