# Chroma Observability Dashboard

Comprehensive observability stack for Chroma deployments, providing real-time visibility into query performance, segment health, resource utilization, and system diagnostics.

## Overview

This observability solution integrates with Chroma's existing OpenTelemetry instrumentation to provide:

- **Query Performance Monitoring**: Track latency (p50, p95, p99), throughput, and error rates
- **Segment Health**: Monitor segment sizes, counts, and compaction needs
- **Collection Metrics**: Track collection counts and document distribution
- **Alerting**: Automated alerts for performance degradation and system issues

## Architecture

```
┌──────────────────────────────────────────────┐
│  Chroma Application                          │
│  (Instrumented with OpenTelemetry)           │
└────────────┬─────────────────────────────────┘
             │ Metrics & Traces (OTLP)
             ↓
┌──────────────────────────────────────────────┐
│  OpenTelemetry Collector                     │
│  (Receives metrics via OTLP)                 │
└────────────┬─────────────────────────────────┘
             │
             └────→ Prometheus (Metrics Storage)

┌──────────────────────────────────────────────┐
│  Grafana (Visualization)                     │
│  - Chroma Overview Dashboard                 │
│  - Query Performance Dashboard               │
│  - Segment Health Dashboard                  │
└──────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Chroma application (or use the provided Docker Compose setup)

### Deployment

1. **Navigate to the observability directory:**

   ```bash
   cd observability
   ```

2. **Start the observability stack:**

   ```bash
   docker-compose up -d
   ```

   This will start:
   - Chroma (with OpenTelemetry enabled)
   - OpenTelemetry Collector
   - Prometheus
   - Grafana

3. **Access Grafana:**

   Open your browser and navigate to: `http://localhost:3000`

   - **Username**: `admin`
   - **Password**: `admin`

4. **View Dashboards:**

   Navigate to **Dashboards** → **Chroma** folder to access:
   - **Chroma Overview**: High-level metrics and system status
   - **Chroma Query Performance**: Detailed query latency and throughput
   - **Chroma Segment Health**: Segment sizes, counts, and health

### Verify Metrics

1. **Check Prometheus targets:**

   Navigate to `http://localhost:9090/targets` to ensure all services are up and being scraped.

2. **Query metrics directly:**

   Navigate to `http://localhost:9090/graph` and try queries like:
   ```promql
   chroma_query_total
   chroma_segment_count
   histogram_quantile(0.99, rate(chroma_query_duration_bucket[5m]))
   ```

## Configuration

### Chroma Configuration

Enable OpenTelemetry metrics in Chroma by setting these environment variables:

```yaml
environment:
  - CHROMA_OTEL_ENABLED=true
  - CHROMA_OTEL_COLLECTION_ENDPOINT=http://otel-collector:4317
  - CHROMA_OTEL_SERVICE_NAME=chroma
  - CHROMA_OTEL_GRANULARITY=all
```

### Custom Deployment

If you have an existing Chroma deployment, you can use just the monitoring stack:

1. **Start only the monitoring services:**

   ```bash
   docker-compose up -d otel-collector prometheus grafana
   ```

2. **Configure your Chroma instance** to point to the OTEL collector endpoint.

## Available Metrics

### Query Metrics

| Metric Name | Type | Description |
|-------------|------|-------------|
| `chroma_query_duration` | Histogram | Query execution duration in seconds |
| `chroma_query_total` | Counter | Total number of queries by operation type |
| `chroma_query_errors` | Counter | Total number of query errors by type |
| `chroma_query_result_size` | Histogram | Number of results returned by queries |

### Segment Metrics

| Metric Name | Type | Description |
|-------------|------|-------------|
| `chroma_segment_count` | UpDownCounter | Number of segments per collection |
| `chroma_segment_size_bytes` | UpDownCounter | Segment size in bytes |
| `chroma_segment_records` | UpDownCounter | Number of records in segment |

### Collection Metrics

| Metric Name | Type | Description |
|-------------|------|-------------|
| `chroma_collection_count` | UpDownCounter | Total number of collections |
| `chroma_collection_documents` | UpDownCounter | Number of documents per collection |

## Dashboards

### 1. Chroma Overview

High-level system metrics including:
- p99 Query Latency gauge
- Query Throughput (QPS)
- Total Collections
- Error Rate
- Query Latency by Operation
- Storage by Collection
- Documents per Collection

### 2. Chroma Query Performance

Detailed query performance analysis:
- Query Latency Percentiles (p50, p95, p99)
- Query Throughput by operation type
- Query Result Size Distribution
- Query Error Rate over time
- Key performance indicators (gauges)

### 3. Chroma Segment Health

Segment-level health monitoring:
- Segment Count per Collection
- Segment Size by Collection
- Records per Collection
- Total Collection Count
- Segment Details Table
- Summary gauges for total segments and storage

## Alerting

Pre-configured Prometheus alerts are available in `prometheus/alerts.yml`:

### Query Performance Alerts

- **HighQueryLatency**: p99 > 1s for 5 minutes
- **CriticalQueryLatency**: p99 > 5s for 2 minutes
- **HighErrorRate**: Error rate > 1% for 5 minutes
- **CriticalErrorRate**: Error rate > 5% for 2 minutes

### Segment Health Alerts

- **LargeSegmentSize**: Segment > 10GB for 10 minutes
- **HighSegmentCount**: Collection has > 100 segments
- **NoSegments**: No active segments detected

### Collection Alerts

- **LargeCollection**: Collection > 10M documents
- **NoCollections**: No active collections

### Availability Alerts

- **ChromaDown**: Chroma instance unreachable
- **NoQueryTraffic**: No queries for 10 minutes

## Custom Queries

### Query Latency Analysis

```promql
# p95 latency for query operations
histogram_quantile(0.95,
  sum(rate(chroma_query_duration_bucket{operation_type="query"}[5m])) by (le)
)

# Query throughput by collection
sum(rate(chroma_query_total[5m])) by (collection_name)
```

### Segment Health

```promql
# Total storage per collection
sum(chroma_segment_size_bytes) by (collection_name)

# Average segment size
avg(chroma_segment_size_bytes) by (collection_name)

# Segments needing compaction (> 5GB)
chroma_segment_size_bytes > 5368709120
```

### Error Tracking

```promql
# Error rate by operation type
sum(rate(chroma_query_errors[5m])) by (operation_type, error_type)

# Top error types
topk(5, sum(rate(chroma_query_errors[5m])) by (error_type))
```

## Troubleshooting

### No Metrics Appearing

1. **Check OTEL Collector logs:**
   ```bash
   docker-compose logs otel-collector
   ```

2. **Verify Chroma configuration:**
   Ensure `CHROMA_OTEL_COLLECTION_ENDPOINT` points to the collector.

3. **Check Prometheus targets:**
   Navigate to `http://localhost:9090/targets` and ensure targets are "UP".

### Dashboards Show "No Data"

1. **Verify metrics are being exported:**
   ```bash
   curl http://localhost:8889/metrics | grep chroma
   ```

2. **Check Prometheus is scraping:**
   ```promql
   up{job="chroma"}
   ```

3. **Ensure time range is appropriate:**
   Dashboards default to last 1 hour. Adjust if needed.

### High Memory Usage

1. **Adjust OTEL Collector memory limit:**

   Edit `otel-collector/config.yaml`:
   ```yaml
   processors:
     memory_limiter:
       limit_mib: 256  # Reduce from 512
   ```

2. **Reduce Prometheus retention:**

   Edit `docker-compose.yml`:
   ```yaml
   command:
     - '--storage.tsdb.retention.time=7d'
   ```

## Production Deployment

### Security Considerations

1. **Change default Grafana credentials:**
   ```yaml
   environment:
     - GF_SECURITY_ADMIN_PASSWORD=your-secure-password
   ```

2. **Enable authentication on Prometheus:**
   Add basic auth or use a reverse proxy.

3. **Use TLS for OTLP:**
   Configure TLS certificates in OTEL Collector config.

### Scaling

For high-traffic deployments:

1. **Use remote write for Prometheus:**
   Configure Prometheus to write to a long-term storage backend (e.g., Thanos, Cortex).

2. **Distribute OTEL Collectors:**
   Deploy collectors closer to Chroma instances to reduce network latency.

3. **Enable Prometheus federation:**
   Set up a federated Prometheus architecture for multi-cluster deployments.

## Maintenance

### Backup Dashboards

Export dashboards from Grafana UI or backup the JSON files in `grafana/dashboards/`.

### Update Dashboards

1. Edit the JSON files in `grafana/dashboards/`
2. Restart Grafana or wait for auto-reload (10s interval)

### Clear Old Data

```bash
# Stop services
docker-compose down

# Remove old data volumes
docker volume rm observability_prometheus-data

# Restart
docker-compose up -d
```

## References

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [Chroma Observability Docs](https://docs.trychroma.com/deployment/observability)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review OTEL Collector and Prometheus logs
3. Consult Chroma's observability documentation
