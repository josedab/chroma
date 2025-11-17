# RFC-0006: Automatic Segment Compaction

**Status:** Draft
**Author:** Claude Code Analysis
**Created:** 2025-11-17
**Commit Base:** 091f8bd5c553f8267c48664e98fb32215055f58e

---

## Summary

Implement automatic background compaction for vector and metadata segments to prevent unbounded growth and performance degradation. Compaction merges fragmented segments, reclaims deleted space, and optimizes index structures without manual intervention.

---

## Motivation

### Current State

Segments grow unbounded as operations accumulate:

**File:** `/home/user/chroma/chromadb/segment/impl/manager/local.py`

Segment manager loads segments but doesn't compact them automatically.

### Problems

1. **Performance Degradation:** Query latency increases with segment fragmentation
2. **Wasted Space:** Deleted records aren't reclaimed
3. **Memory Bloat:** Multiple segment versions consume memory
4. **Manual Compaction:** Users must manually trigger compaction

### User Pain Points

- Collections with 10M+ documents slow down over time
- Disk usage doesn't decrease after deletions
- No guidance on when to compact

---

## Detailed Design

### Compaction Triggers

**Trigger 1: Size Threshold**
- Compact when segment > 1GB and fragmentation > 20%

**Trigger 2: Time-Based**
- Compact segments idle for > 7 days

**Trigger 3: Deleted Records**
- Compact when deleted records > 30% of total

### Compaction Algorithm

```python
def compact_segment(segment_id: UUID):
    """
    Compact a single segment by:
    1. Load all live records
    2. Rebuild index from scratch
    3. Write new segment
    4. Atomically swap old → new
    5. Delete old segment
    """
    old_segment = load_segment(segment_id)
    
    # Extract live records (skip deleted)
    live_records = [
        r for r in old_segment.records() 
        if not r.is_deleted()
    ]
    
    # Build new segment
    new_segment = build_optimized_segment(live_records)
    
    # Atomic swap
    atomically_replace_segment(old_segment, new_segment)
    
    # Cleanup
    delete_segment(old_segment)
```

### Distributed Compaction

**File:** `k8s/distributed-chroma/templates/compaction-service.yaml`

Compaction service already exists! Just needs automatic triggering:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compaction-service
spec:
  # Add automatic scheduling
  env:
    - name: COMPACTION_SCHEDULE
      value: "0 2 * * *"  # Daily at 2 AM
    - name: COMPACTION_SIZE_THRESHOLD_GB
      value: "1"
    - name: COMPACTION_FRAGMENTATION_THRESHOLD
      value: "0.2"
```

---

## Implementation Plan

### Milestone 1: Compaction Logic (8 dev-days)
- [ ] Implement segment compaction algorithm
- [ ] Add fragmentation detection
- [ ] Atomic segment swap
- [ ] Crash recovery

### Milestone 2: Scheduling (5 dev-days)
- [ ] Background compaction service
- [ ] Trigger conditions
- [ ] Rate limiting
- [ ] Distributed coordination

### Milestone 3: Safety (4 dev-days)
- [ ] Snapshot-based compaction
- [ ] Rollback on failure
- [ ] Data integrity checks
- [ ] Lock-free reads during compaction

### Milestone 4: Monitoring (3 dev-days)
- [ ] Compaction metrics
- [ ] Progress tracking
- [ ] Alerting on failures
- [ ] Performance impact monitoring

---

## Example Usage

### Automatic (Default)

```python
# Compaction happens automatically in background
client = chromadb.Client()
collection = client.create_collection("docs")

# Add 1M documents
for i in range(1_000_000):
    collection.add(...)

# Delete 500K documents
collection.delete(ids=[...])

# Automatic compaction triggered after threshold
# - Runs in background
# - No query interruption
# - Space reclaimed
```

### Manual Trigger

```python
# Force compaction
collection.compact()

# Check compaction status
status = collection.get_compaction_status()
print(status)
# {
#   "in_progress": True,
#   "progress": 0.45,
#   "estimated_completion": "2025-11-17T10:30:00Z"
# }
```

---

## Backwards Compatibility

- Automatic compaction is opt-in via configuration
- Manual compaction API is new (additive)
- Existing segments work without changes

---

## Success Criteria

- [ ] Compaction reduces segment size by 30%+ after 30% deletions
- [ ] Query latency unchanged during compaction
- [ ] Zero data loss or corruption
- [ ] Automatic compaction in distributed mode

---

## Effort Estimation

| Phase | Dev-Days |
|-------|----------|
| Compaction logic | 8 |
| Scheduling | 5 |
| Safety | 4 |
| Monitoring | 3 |
| **Total** | **20** |

---

## References

- [RocksDB Compaction](https://github.com/facebook/rocksdb/wiki/Compaction)
- [Elasticsearch Segment Merging](https://www.elastic.co/guide/en/elasticsearch/reference/current/index-modules-merge.html)
- [DuckDB Vacuum](https://duckdb.org/docs/sql/statements/vacuum.html)

---

## Revision History

- **v1.0** (2025-11-17): Initial RFC
