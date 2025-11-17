#!/usr/bin/env python3
"""
Example: Using Read Replicas for Query Scaling

This example demonstrates how to use read replicas to scale query throughput
in Chroma. It shows:
1. Writing to the primary node
2. Reading from replicas with load balancing
3. Handling replica failover
4. Read-after-write consistency

Prerequisites:
    docker-compose -f docker-compose.replicas.yml up

This starts:
    - Primary (port 8001): Handles writes
    - Replica 1 (port 8002): Handles reads
    - Replica 2 (port 8003): Handles reads
"""

import chromadb
import time
from chromadb.api.load_balancer import ReplicaLoadBalancer, parse_replica_hosts


def main():
    print("=== Chroma Read Replicas Example ===\n")

    # Step 1: Connect to Primary for Writes
    print("1. Connecting to primary (port 8001)...")
    primary_client = chromadb.HttpClient(host="localhost", port=8001)

    # Create or get collection
    print("2. Creating collection 'documents'...")
    collection = primary_client.get_or_create_collection(
        name="documents",
        metadata={"description": "Example document collection"}
    )

    # Add documents to primary
    print("3. Adding documents to primary...")
    collection.add(
        ids=[f"doc{i}" for i in range(100)],
        documents=[f"This is document number {i}" for i in range(100)],
        metadatas=[{"index": i} for i in range(100)]
    )
    print(f"   Added {collection.count()} documents\n")

    # Step 2: Set up Load Balancer for Replicas
    print("4. Setting up load balancer for replicas...")
    replica_hosts = ["http://localhost:8002", "http://localhost:8003"]
    lb = ReplicaLoadBalancer(
        replica_hosts=replica_hosts,
        strategy="round_robin"
    )
    print(f"   Configured with {len(replica_hosts)} replicas\n")

    # Step 3: Query from Replicas
    print("5. Querying from replicas (load balanced)...")

    # Give replicas a moment to sync (eventual consistency)
    time.sleep(0.5)

    for i in range(10):
        # Get next replica from load balancer
        replica_url = lb.get_next_replica()
        replica_host = replica_url.split(":")[-2].replace("//", "")
        replica_port = int(replica_url.split(":")[-1].split("/")[0])

        # Create client for this replica
        replica_client = chromadb.HttpClient(host=replica_host, port=replica_port)

        # Query the collection
        result = replica_client.get_collection("documents").get(limit=5)

        print(f"   Query {i+1} -> {replica_url}: Retrieved {len(result['ids'])} documents")

    print()

    # Step 4: Demonstrate Failover
    print("6. Demonstrating failover...")
    print("   Marking replica 1 as unhealthy...")
    lb.mark_replica_unhealthy("http://localhost:8002")

    print("   Next 5 queries (should only go to replica 2):")
    for i in range(5):
        replica_url = lb.get_next_replica()
        print(f"      Query {i+1} -> {replica_url}")

    print("\n   Marking replica 1 as healthy again...")
    lb.mark_replica_healthy("http://localhost:8002")

    print("   Next 4 queries (should alternate):")
    for i in range(4):
        replica_url = lb.get_next_replica()
        print(f"      Query {i+1} -> {replica_url}")

    print()

    # Step 5: Demonstrate Read-After-Write Pattern
    print("7. Demonstrating read-after-write pattern...")

    # Write a new document
    print("   Writing new document to primary...")
    collection.add(
        ids=["new_doc"],
        documents=["This is a brand new document"],
        metadatas=[{"new": True}]
    )

    # For read-after-write consistency, in a production system you would:
    # 1. Get the log position from the write operation
    # 2. Wait for replicas to sync to that position
    # 3. Then read from replica

    # For this example, we'll just wait a moment
    print("   Waiting for replication...")
    time.sleep(0.5)

    # Read from replica
    replica_url = lb.get_next_replica()
    replica_host = replica_url.split(":")[-2].replace("//", "")
    replica_port = int(replica_url.split(":")[-1].split("/")[0])
    replica_client = chromadb.HttpClient(host=replica_host, port=replica_port)

    try:
        result = replica_client.get_collection("documents").get(ids=["new_doc"])
        if result['ids']:
            print(f"   ✓ Successfully read new document from replica: {replica_url}")
        else:
            print(f"   ✗ Document not yet available on replica (eventual consistency)")
    except Exception as e:
        print(f"   ✗ Error reading from replica: {e}")

    print()

    # Step 6: Performance Comparison
    print("8. Performance comparison...")

    # Query primary directly
    start = time.time()
    for _ in range(100):
        primary_client.get_collection("documents").get(limit=10)
    primary_time = time.time() - start

    print(f"   Primary only (100 queries): {primary_time:.2f}s ({100/primary_time:.1f} QPS)")

    # Query replicas with load balancing
    start = time.time()
    for _ in range(100):
        replica_url = lb.get_next_replica()
        replica_host = replica_url.split(":")[-2].replace("//", "")
        replica_port = int(replica_url.split(":")[-1].split("/")[0])
        replica_client = chromadb.HttpClient(host=replica_host, port=replica_port)
        replica_client.get_collection("documents").get(limit=10)
    replica_time = time.time() - start

    print(f"   Replicas (100 queries, load balanced): {replica_time:.2f}s ({100/replica_time:.1f} QPS)")
    print(f"   Speedup: {primary_time/replica_time:.2f}x")

    print("\n=== Example Complete ===")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExample interrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        print("\nMake sure to start the replica cluster first:")
        print("  docker-compose -f docker-compose.replicas.yml up")
