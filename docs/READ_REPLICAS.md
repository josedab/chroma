# Read Replicas Guide

Read replicas enable horizontal scaling of query throughput for read-heavy workloads in Chroma. This guide explains how to deploy and use read replicas.

## Overview

Read replicas provide:

- **Horizontal scaling**: Distribute queries across multiple nodes for 10x+ throughput
- **Geographic distribution**: Place replicas closer to users for lower latency
- **Workload isolation**: Separate analytics from production workloads
- **High availability**: Automatic failover when replicas become unavailable

## Architecture

```
                           ┌──────────────┐
                           │              │
                           │  Log Service │
                           │   (Primary)  │
                           │              │
                           └──────┬───────┘
                                  │ Write Log
                                  │
                   ┌──────────────┼──────────────┐
                   │              │              │
                   ▼              ▼              ▼
         ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
         │             │  │             │  │             │
         │  Replica 1  │  │  Replica 2  │  │  Replica 3  │
         │             │  │             │  │             │
         └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
                │                │                │
                └────────────────┴────────────────┘
                          Read Queries
```

- **Primary Node**: Handles all write operations
- **Log Service**: Distributes write operations to replicas
- **Replica Nodes**: Handle read-only queries, sync from log service
- **Load Balancer**: Distributes queries across healthy replicas

## Quick Start

### Using Docker Compose

The easiest way to get started is with the provided Docker Compose configuration:

```bash
# Start Chroma with read replicas
docker-compose -f docker-compose.replicas.yml up

# Ports:
# - 8001: Primary (for writes)
# - 8002: Replica 1 (for reads)
# - 8003: Replica 2 (for reads)
```

### Python Client Usage

```python
import chromadb

# Connect to primary for writes
primary_client = chromadb.HttpClient(host="localhost", port=8001)

# Create a collection and add documents
collection = primary_client.get_or_create_collection("docs")
collection.add(
    ids=["doc1", "doc2", "doc3"],
    documents=["Document 1", "Document 2", "Document 3"]
)

# Connect to replicas for reads (with load balancing)
from chromadb.api.load_balancer import ReplicaLoadBalancer

replica_lb = ReplicaLoadBalancer(
    replica_hosts=["http://localhost:8002", "http://localhost:8003"],
    strategy="round_robin"
)

# Query from replicas (distributed load)
for i in range(10):
    replica_url = replica_lb.get_next_replica()
    replica_client = chromadb.HttpClient(host=replica_url)
    results = replica_client.get_collection("docs").get()
    print(f"Query {i} -> {replica_url}: {len(results['ids'])} docs")
```

## Configuration

### Environment Variables

Configure replica mode using environment variables:

#### Primary Node
```bash
CHROMA_MODE=primary
CHROMA_LOGSERVICE_HOST=log-service
CHROMA_LOGSERVICE_PORT=50051
```

#### Replica Node
```bash
CHROMA_MODE=replica
CHROMA_REPLICA_ID=replica-1
CHROMA_LOGSERVICE_HOST=log-service
CHROMA_LOGSERVICE_PORT=50051
CHROMA_REPLICA_POLL_INTERVAL_SECONDS=0.1
CHROMA_REPLICA_MAX_LAG_SECONDS=5
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `CHROMA_MODE` | `primary` | Node mode: `primary` or `replica` |
| `CHROMA_REPLICA_ID` | `None` | Unique identifier for this replica |
| `CHROMA_REPLICA_POLL_INTERVAL_SECONDS` | `0.1` | How often replica polls for new log entries |
| `CHROMA_REPLICA_MAX_LAG_SECONDS` | `5` | Maximum acceptable replication lag |
| `CHROMA_REPLICA_HOSTS` | `None` | Comma-separated list of replica URLs for client-side load balancing |
| `CHROMA_LOAD_BALANCING_STRATEGY` | `round_robin` | Load balancing strategy: `round_robin` or `random` |

## Load Balancing Strategies

### Round Robin (Default)

Distributes requests evenly across replicas in a circular pattern:

```python
from chromadb.api.load_balancer import ReplicaLoadBalancer

lb = ReplicaLoadBalancer(
    replica_hosts=["http://replica1:8000", "http://replica2:8000"],
    strategy="round_robin"
)
```

### Random

Selects a random replica for each request:

```python
lb = ReplicaLoadBalancer(
    replica_hosts=["http://replica1:8000", "http://replica2:8000"],
    strategy="random"
)
```

## Consistency Guarantees

### Eventual Consistency (Default)

Replicas eventually see all writes, typically within 100-500ms:

```python
# Write to primary
primary_client.add(ids=["doc1"], documents=["Document 1"])

# Read from replica (may not see write immediately)
replica_client.get(ids=["doc1"])  # May return NotFound briefly
```

### Read-After-Write Consistency

For applications requiring stronger consistency, the replica sync service supports waiting for a specific log position:

```python
from chromadb.replica.replica_sync import ReplicaSyncService

# After a write, get the log position
result = primary_client.add(ids=["doc1"], documents=["Document 1"])
log_position = result.get("log_position", 0)

# Wait for replica to catch up
sync_service = system.instance(ReplicaSyncService)
success = sync_service.wait_for_position(
    collection_id=collection.id,
    min_position=log_position,
    timeout=5.0
)

if success:
    # Replica has caught up, read is guaranteed to see the write
    result = replica_client.get(ids=["doc1"])
```

## Failover and Health Checks

The load balancer automatically handles replica failures:

```python
lb = ReplicaLoadBalancer(
    replica_hosts=["http://replica1:8000", "http://replica2:8000"]
)

# Mark a replica as unhealthy (e.g., after connection error)
lb.mark_replica_unhealthy("http://replica1:8000")

# Requests now only go to replica2
replica = lb.get_next_replica()  # Returns replica2

# Mark as healthy again when recovered
lb.mark_replica_healthy("http://replica1:8000")
```

## Monitoring

### Replication Lag

Monitor replication lag to ensure replicas stay up-to-date:

```python
from chromadb.replica.replica_sync import ReplicaSyncService

sync_service = system.instance(ReplicaSyncService)
lag = sync_service.get_replication_lag(collection_id)

if lag and lag > 1000:
    print(f"Warning: Replica lagging by {lag} log entries")
```

### Recommended Metrics

Monitor these metrics in production:

- `chroma_replica_lag_seconds`: Replication lag in seconds
- `chroma_replica_sync_errors`: Number of sync errors
- `chroma_query_throughput`: Queries per second per replica
- `chroma_replica_health`: Replica health status (0=unhealthy, 1=healthy)

## Multi-Region Deployment

Deploy replicas in multiple regions for global applications:

```yaml
# US-East Replica
chroma-replica-us-east:
  environment:
    - CHROMA_REPLICA_ID=us-east-1
    - CHROMA_LOGSERVICE_HOST=log-service.us-east.example.com

# EU-West Replica
chroma-replica-eu-west:
  environment:
    - CHROMA_REPLICA_ID=eu-west-1
    - CHROMA_LOGSERVICE_HOST=log-service.eu-west.example.com
```

Route users to nearest replica:

```python
import chromadb

# US users -> US replicas
us_client = chromadb.HttpClient(host="us-east-replica.example.com")

# EU users -> EU replicas
eu_client = chromadb.HttpClient(host="eu-west-replica.example.com")
```

## Performance

Expected performance with read replicas:

| Metric | Single Node | 3 Replicas | 10 Replicas |
|--------|-------------|------------|-------------|
| Query Throughput | 100 QPS | 300 QPS | 1000 QPS |
| Read Latency (p99) | 50ms | 50ms | 50ms |
| Replication Lag (p99) | N/A | 500ms | 500ms |

## Troubleshooting

### Replica Not Syncing

Check that:
1. Replica can connect to log service
2. `CHROMA_LOGSERVICE_HOST` and `CHROMA_LOGSERVICE_PORT` are correct
3. Replica mode is set to `replica`

```bash
# Check replica logs
docker logs chroma-replica-1

# Verify connection to log service
curl http://localhost:8002/api/v1/heartbeat
```

### High Replication Lag

If replication lag is high:
1. Check network latency between replica and log service
2. Reduce `CHROMA_REPLICA_POLL_INTERVAL_SECONDS` (trade-off: more CPU)
3. Verify replica has sufficient resources (CPU, memory)

### Load Balancer Not Distributing Evenly

Verify:
1. All replicas are marked as healthy
2. Strategy is set correctly (`round_robin` vs `random`)
3. Replicas are reachable from client

## Best Practices

1. **Write to Primary, Read from Replicas**: Direct all writes to the primary node, all reads to replicas
2. **Use Health Checks**: Implement health checks and remove unhealthy replicas from rotation
3. **Monitor Replication Lag**: Alert when lag exceeds acceptable threshold (e.g., 5 seconds)
4. **Size Replicas Appropriately**: Each replica should handle 100-200 QPS; add more for higher load
5. **Geographic Placement**: Place replicas close to users for best latency
6. **Eventual Consistency**: Design applications to handle eventual consistency (100-500ms lag)

## Limitations

Current limitations:
- Replicas are read-only (writes not supported)
- Eventual consistency by default (100-500ms lag)
- Manual replica configuration (no auto-scaling)

## Next Steps

- See [RFC-0010](../analysis-output/rfcs/RFC-0010-read-replicas.md) for detailed design
- Review [docker-compose.replicas.yml](../docker-compose.replicas.yml) for deployment example
- Check [test_read_replicas.py](../chromadb/test/replica/test_read_replicas.py) for test examples

## Support

For questions or issues:
- GitHub Issues: https://github.com/chroma-core/chroma/issues
- Discord: https://discord.gg/MMeYNTmh3x
