# RFC-0005: Enhanced Observability Dashboard

**Status:** Draft
**Author:** Claude Code Analysis  
**Created:** 2025-11-17
**Commit Base:** 091f8bd5c553f8267c48664e98fb32215055f58e

---

## Summary

Build a comprehensive observability dashboard for Chroma deployments, providing real-time visibility into query performance, segment health, resource utilization, and system diagnostics. Integrates with existing OpenTelemetry infrastructure to surface actionable metrics for production operations.

---

## Motivation

### Current State

Chroma has OpenTelemetry instrumentation:

**File:** `/home/user/chroma/chromadb/telemetry/opentelemetry/__init__.py`
**File:** `/home/user/chroma/chromadb/telemetry/opentelemetry/fastapi.py`

```python
from chromadb.telemetry.opentelemetry import (
    OpenTelemetryClient,
    OpenTelemetryGranularity,
    trace_method,
)
```

**Problem:** Metrics are exported but there's no built-in dashboard to visualize them.

### Pain Points

1. **No Visibility:** Operators don't know query latency distributions
2. **Debug Difficulty:** When queries slow down, no way to identify bottleneck
3. **Capacity Planning:** Unknown resource utilization trends
4. **Segment Health:** No visibility into segment sizes, compaction needs

### User Impact

Production teams report:
- "Queries suddenly slow, don't know why"
- "Collection became large, should we compact?"
- "Is HNSW index loaded into memory?"
- "Which queries are most expensive?"

---

## Detailed Design

### Architecture

```
┌──────────────────────────────────────────────┐
│  Chroma Application                          │
│  (Instrumented with OpenTelemetry)           │
└────────────┬─────────────────────────────────┘
             │ Metrics & Traces
             ↓
┌──────────────────────────────────────────────┐
│  OpenTelemetry Collector                     │
│  (Receives metrics via OTLP)                 │
└────────────┬─────────────────────────────────┘
             │
             ├────→ Prometheus (Metrics)
             ├────→ Jaeger (Traces)
             └────→ Loki (Logs)
             
┌──────────────────────────────────────────────┐
│  Chroma Dashboard (Grafana)                  │
│  - Query Performance Panel                   │
│  - Segment Health Panel                      │
│  - Resource Utilization Panel                │
│  - Error Tracking Panel                      │
└──────────────────────────────────────────────┘
```

### Dashboard Components

#### Panel 1: Query Performance

**Metrics:**
- Query latency (p50, p95, p99)
- Query throughput (queries/sec)
- Query result size distribution
- Embedding generation time

**Alerts:**
- p99 latency > 1 second
- Error rate > 1%

#### Panel 2: Segment Health

**Metrics:**
- Segment count per collection
- Segment size (bytes)
- Records per segment
- Compaction backlog

**Visualization:**
```
Collection: my_docs
├── Vector Segment (HNSW)
│   Size: 2.3 GB
│   Records: 1.2M
│   Last Compaction: 3 days ago
├── Metadata Segment (SQLite)
│   Size: 450 MB
│   Records: 1.2M
```

#### Panel 3: Resource Utilization

**Metrics:**
- Memory usage (RSS, heap)
- CPU utilization
- Disk I/O (reads/writes per sec)
- Network bandwidth

#### Panel 4: Collection Statistics

**Metrics:**
- Collection count
- Documents per collection
- Average embedding dimension
- Storage by collection

---

## Implementation Plan

### Milestone 1: Metrics Schema (3 dev-days)
- [ ] Define metric names and labels
- [ ] Add instrumentation to query path
- [ ] Add segment metrics collection
- [ ] Export via OTLP

### Milestone 2: Grafana Dashboards (4 dev-days)
- [ ] Create dashboard JSON templates
- [ ] Build query performance panel
- [ ] Build segment health panel
- [ ] Build resource panel

### Milestone 3: Alerting Rules (2 dev-days)
- [ ] Define alert conditions
- [ ] Configure Prometheus alerts
- [ ] Add alert notification channels
- [ ] Document alert playbooks

### Milestone 4: Deployment (3 dev-days)
- [ ] Docker Compose with Grafana
- [ ] Kubernetes Helm chart updates
- [ ] Auto-provisioning dashboards
- [ ] Documentation

---

## Example Usage

### Deployment

```yaml
# docker-compose.yml
version: '3.8'
services:
  chroma:
    image: chromadb/chroma:latest
    environment:
      - CHROMA_OTEL_ENABLED=true
      - CHROMA_OTEL_ENDPOINT=http://otel-collector:4317

  otel-collector:
    image: otel/opentelemetry-collector:latest
    volumes:
      - ./otel-config.yaml:/etc/otel/config.yaml

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - ./dashboards:/etc/grafana/provisioning/dashboards
```

### Accessing Dashboard

```bash
# Start stack
docker-compose up -d

# Open Grafana
open http://localhost:3000

# View Chroma dashboard
# Navigate to: Dashboards → Chroma Overview
```

### Custom Queries

```promql
# Query latency p95
histogram_quantile(0.95, 
  rate(chroma_query_duration_seconds_bucket[5m])
)

# Segment size by collection
sum by (collection_name) (chroma_segment_size_bytes)

# Error rate
rate(chroma_query_errors_total[5m])
```

---

## Backwards Compatibility

No breaking changes - purely additive observability features.

---

## Success Criteria

- [ ] Dashboard shows real-time query metrics
- [ ] Segment health visible per collection
- [ ] Alerts fire on performance degradation
- [ ] Deployment via Docker Compose works

---

## Effort Estimation

| Phase | Dev-Days |
|-------|----------|
| Metrics schema | 3 |
| Dashboards | 4 |
| Alerting | 2 |
| Deployment | 3 |
| **Total** | **12** |

---

## References

- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
