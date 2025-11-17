# RFC-0010: Read Replicas for Query Scaling

**Status:** Draft
**Author:** Claude Code Analysis
**Created:** 2025-11-17
**Commit Base:** 091f8bd5c553f8267c48664e98fb32215055f58e

---

## Summary

Implement read replicas to horizontally scale query throughput for read-heavy workloads. Primary node handles writes, replicas handle queries. Achieves 10x+ query throughput by distributing load across multiple nodes while maintaining consistency via log-based replication.

---

## Motivation

### Current State

Chroma distributed architecture exists:

**File:** `/home/user/chroma/k8s/distributed-chroma/`

Kubernetes deployment with:
- Query service (frontends)
- Log service (write path)
- Compaction service

**Problem:** All queries hit same set of nodes. No horizontal scaling for read-heavy workloads.

### Use Cases

#### Use Case 1: High Query Volume

```
Scenario: RAG application with 1M users
- 1000 queries/second
- Single node: 100 QPS max
- Need: 10+ query nodes
```

#### Use Case 2: Multi-Region Deployment

```
Scenario: Global application
- US users → US replica
- EU users → EU replica
- Asia users → Asia replica
- Reduced latency, improved availability
```

#### Use Case 3: Read-Write Separation

```
Scenario: Analytics + Production
- Production writes → Primary
- Analytics queries → Replica
- Isolate workloads, prevent interference
```

### Problems Without Read Replicas

1. **Query Bottleneck:** Single node saturates at 100-200 QPS
2. **No Geographic Distribution:** All queries to one region (high latency)
3. **Write Interference:** Heavy writes slow down queries
4. **Single Point of Failure:** Node failure = total outage

---

## Detailed Design

### Architecture

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
         │ (US-East)   │  │ (US-West)   │  │  (EU-West)  │
         │             │  │             │  │             │
         └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
                │                │                │
                └────────────────┴────────────────┘
                          Read Queries
                                │
                                ▼
                        ┌──────────────┐
                        │ Load Balancer│
                        └──────────────┘
```

### Key Components

#### 1. Log-Based Replication

**Primary logs all writes:**

```python
# Primary receives write
def add_documents(collection_id, documents):
    # 1. Append to write-ahead log
    log_entry = {
        "operation": "add",
        "collection_id": collection_id,
        "documents": documents,
        "timestamp": time.time()
    }
    log_service.append(log_entry)
    
    # 2. Apply to primary
    primary_segment.add(documents)
    
    # 3. Replicas pull log asynchronously
    return {"status": "ok"}
```

**Replicas consume log:**

```python
# Replica continuously polls log
def replica_sync_loop():
    last_position = 0
    
    while True:
        # Fetch new log entries
        entries = log_service.fetch(start=last_position, limit=100)
        
        for entry in entries:
            # Apply operation to replica
            if entry["operation"] == "add":
                replica_segment.add(entry["documents"])
            elif entry["operation"] == "delete":
                replica_segment.delete(entry["ids"])
            
            last_position = entry["position"]
        
        time.sleep(0.1)  # Poll interval
```

#### 2. Consistency Guarantees

**Eventual Consistency:**
- Writes visible on primary immediately
- Replicas lag by ~100-500ms
- Acceptable for most use cases

**Read-After-Write Consistency (Optional):**
```python
# Client tracks write position
result = collection.add(documents=["doc1"])
write_position = result["log_position"]

# Query replica, wait until it catches up
results = collection.query(
    query_texts=["query"],
    consistency={
        "level": "read_after_write",
        "min_log_position": write_position
    }
)
```

#### 3. Replica Discovery

**Service Discovery via Kubernetes:**

```yaml
# k8s/replica-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: chroma-replica
spec:
  selector:
    app: chroma-replica
  ports:
    - port: 8000
  type: LoadBalancer
```

**Client-side load balancing:**

```python
class ChromaClient:
    def __init__(self, replicas: List[str]):
        self.replicas = replicas
        self.current_replica = 0
    
    def query(self, ...):
        # Round-robin load balancing
        replica = self.replicas[self.current_replica]
        self.current_replica = (self.current_replica + 1) % len(self.replicas)
        
        return requests.post(f"{replica}/query", ...)
```

#### 4. Replication Lag Monitoring

**Track lag per replica:**

```python
# Metrics
chroma_replica_lag_seconds{replica="replica-1"} 0.12
chroma_replica_lag_seconds{replica="replica-2"} 0.35

# Alert if lag > 5 seconds
ALERT ReplicaLagging
  IF chroma_replica_lag_seconds > 5
  FOR 1m
  LABELS { severity="warning" }
  ANNOTATIONS {
    summary="Replica lagging behind primary"
  }
```

---

## Implementation Plan

### Milestone 1: Log Replication (10 dev-days)
- [ ] Implement log consumption in query service
- [ ] Add replica sync loop
- [ ] Handle log compaction
- [ ] Test with 3-node cluster

### Milestone 2: Consistency (8 dev-days)
- [ ] Implement eventual consistency
- [ ] Add read-after-write consistency
- [ ] Handle replica failure/recovery
- [ ] Test consistency guarantees

### Milestone 3: Load Balancing (5 dev-days)
- [ ] Client-side load balancing
- [ ] Health checks
- [ ] Failover logic
- [ ] Integration tests

### Milestone 4: Operations (7 dev-days)
- [ ] Replica deployment scripts
- [ ] Monitoring & alerting
- [ ] Replica promotion (failover)
- [ ] Documentation
- [ ] Capacity planning guide

---

## Example Usage

### Deployment

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Primary (writes)
  chroma-primary:
    image: chromadb/chroma:latest
    environment:
      - CHROMA_MODE=primary
      - CHROMA_LOG_SERVICE_URL=http://log-service:50051
    ports:
      - "8001:8000"

  # Replica 1 (reads)
  chroma-replica-1:
    image: chromadb/chroma:latest
    environment:
      - CHROMA_MODE=replica
      - CHROMA_LOG_SERVICE_URL=http://log-service:50051
      - CHROMA_REPLICA_ID=replica-1
    ports:
      - "8002:8000"

  # Replica 2 (reads)
  chroma-replica-2:
    image: chromadb/chroma:latest
    environment:
      - CHROMA_MODE=replica
      - CHROMA_LOG_SERVICE_URL=http://log-service:50051
      - CHROMA_REPLICA_ID=replica-2
    ports:
      - "8003:8000"

  # Log service
  log-service:
    image: chromadb/log-service:latest
    ports:
      - "50051:50051"
```

### Client Usage

```python
import chromadb

# Connect to primary for writes
primary_client = chromadb.HttpClient(host="chroma-primary", port=8001)

# Connect to replicas for reads
replica_client = chromadb.HttpClient(
    hosts=["http://chroma-replica-1:8002", "http://chroma-replica-2:8003"],
    load_balancing="round_robin"
)

# Write to primary
collection = primary_client.get_or_create_collection("docs")
collection.add(ids=["doc1"], documents=["Important document"])

# Read from replicas (10x throughput)
results = replica_client.get_collection("docs").query(
    query_texts=["important"],
    n_results=10
)
```

### Multi-Region Deployment

```python
# US client routes to US replicas
us_client = chromadb.HttpClient(
    hosts=["us-east-replica:8000", "us-west-replica:8000"]
)

# EU client routes to EU replicas
eu_client = chromadb.HttpClient(
    hosts=["eu-west-replica:8000", "eu-central-replica:8000"]
)

# Both read from same data (eventually consistent)
us_results = us_client.get_collection("docs").query(...)
eu_results = eu_client.get_collection("docs").query(...)
```

---

## Backwards Compatibility

- Single-node deployments unchanged
- Replicas opt-in via configuration
- Existing clients work without changes

---

## Alternatives Considered

### Alternative 1: Master-Slave Replication
**Rejected:** Complex failover, single write node bottleneck

### Alternative 2: Multi-Master Replication
**Rejected:** Conflict resolution complexity, not needed for read-heavy

### Alternative 3: Cache Layer (Redis)
**Rejected:** Stale data issues, cache invalidation complexity

---

## Performance Impact

### Expected Improvements

| Metric | Single Node | 3 Replicas | 10 Replicas |
|--------|-------------|------------|-------------|
| Query Throughput | 100 QPS | 300 QPS | 1000 QPS |
| Read Latency (p99) | 50ms | 50ms | 50ms |
| Write Latency | 20ms | 25ms | 30ms |
| Availability | 99% | 99.9% | 99.99% |

**Replication lag:** Typically 100-500ms, depends on write volume.

---

## Testing Strategy

### Consistency Tests

```python
def test_eventual_consistency():
    """Test replica eventually sees write"""
    # Write to primary
    primary.add(ids=["doc1"], documents=["test"])
    
    # Read from replica
    for attempt in range(100):
        try:
            result = replica.get(ids=["doc1"])
            assert result is not None
            break
        except NotFoundError:
            time.sleep(0.1)  # Wait for replication
    else:
        pytest.fail("Replica never caught up")

def test_read_after_write():
    """Test read-after-write consistency"""
    # Write to primary
    result = primary.add(ids=["doc1"], documents=["test"])
    log_pos = result["log_position"]
    
    # Read from replica with consistency level
    result = replica.get(
        ids=["doc1"],
        consistency={"min_log_position": log_pos}
    )
    assert result is not None  # Should block until replicated
```

### Failover Tests

```python
def test_replica_failure():
    """Test query continues with replica failure"""
    client = chromadb.HttpClient(
        hosts=["replica1:8000", "replica2:8000"]
    )
    
    # Kill replica1
    kill_replica("replica1")
    
    # Queries should still work (failover to replica2)
    result = client.query(...)
    assert result is not None
```

---

## Success Criteria

- [ ] 10x query throughput with 10 replicas
- [ ] Replication lag < 500ms at p99
- [ ] Zero downtime during replica failure
- [ ] Automatic failover working

---

## Effort Estimation

| Phase | Dev-Days |
|-------|----------|
| Log replication | 10 |
| Consistency | 8 |
| Load balancing | 5 |
| Operations | 7 |
| **Total** | **30** |

---

## References

- [PostgreSQL Replication](https://www.postgresql.org/docs/current/warm-standby.html)
- [MongoDB Replica Sets](https://www.mongodb.com/docs/manual/replication/)
- [Elasticsearch Replication](https://www.elastic.co/guide/en/elasticsearch/reference/current/index-modules.html)

---

## Revision History

- **v1.0** (2025-11-17): Initial RFC
