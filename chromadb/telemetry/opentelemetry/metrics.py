"""OpenTelemetry metrics instrumentation for Chroma.

This module provides metrics collection for:
- Query performance (latency, throughput, result sizes)
- Segment health (sizes, counts, compaction status)
- Resource utilization (memory, CPU, disk I/O)
- Error tracking
"""

import os
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

# Module-level meter instance
_meter: Optional[metrics.Meter] = None
_enabled: bool = False

# Query Performance Metrics
_query_duration_histogram: Optional[metrics.Histogram] = None
_query_counter: Optional[metrics.Counter] = None
_query_error_counter: Optional[metrics.Counter] = None
_query_result_size_histogram: Optional[metrics.Histogram] = None

# Segment Health Metrics
_segment_count_gauge: Optional[metrics.UpDownCounter] = None
_segment_size_gauge: Optional[metrics.UpDownCounter] = None
_segment_records_gauge: Optional[metrics.UpDownCounter] = None

# Collection Metrics
_collection_count_gauge: Optional[metrics.UpDownCounter] = None
_documents_per_collection_gauge: Optional[metrics.UpDownCounter] = None


def init_metrics(
    service_name: Optional[str] = None,
    endpoint: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
) -> None:
    """Initialize OpenTelemetry metrics.

    Args:
        service_name: Name of the service for metrics tagging
        endpoint: OTLP endpoint for metrics export (e.g., "http://localhost:4317")
        headers: Optional headers for metrics export
    """
    global _meter, _enabled
    global _query_duration_histogram, _query_counter, _query_error_counter
    global _query_result_size_histogram
    global _segment_count_gauge, _segment_size_gauge, _segment_records_gauge
    global _collection_count_gauge, _documents_per_collection_gauge

    if not service_name or not endpoint:
        _enabled = False
        return

    # Create resource with service name
    resource = Resource(attributes={SERVICE_NAME: service_name})

    # Create OTLP metric exporter
    exporter = OTLPMetricExporter(
        endpoint=endpoint,
        headers=headers or {},
    )

    # Create metric reader with 60-second export interval
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=60000)

    # Create meter provider
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)

    # Get meter instance
    _meter = metrics.get_meter(__name__)
    _enabled = True

    # Initialize query performance metrics
    _query_duration_histogram = _meter.create_histogram(
        name="chroma.query.duration",
        description="Query execution duration in seconds",
        unit="s",
    )

    _query_counter = _meter.create_counter(
        name="chroma.query.total",
        description="Total number of queries",
        unit="1",
    )

    _query_error_counter = _meter.create_counter(
        name="chroma.query.errors",
        description="Total number of query errors",
        unit="1",
    )

    _query_result_size_histogram = _meter.create_histogram(
        name="chroma.query.result_size",
        description="Number of results returned by query",
        unit="1",
    )

    # Initialize segment health metrics
    _segment_count_gauge = _meter.create_up_down_counter(
        name="chroma.segment.count",
        description="Number of segments per collection",
        unit="1",
    )

    _segment_size_gauge = _meter.create_up_down_counter(
        name="chroma.segment.size_bytes",
        description="Segment size in bytes",
        unit="By",
    )

    _segment_records_gauge = _meter.create_up_down_counter(
        name="chroma.segment.records",
        description="Number of records in segment",
        unit="1",
    )

    # Initialize collection metrics
    _collection_count_gauge = _meter.create_up_down_counter(
        name="chroma.collection.count",
        description="Total number of collections",
        unit="1",
    )

    _documents_per_collection_gauge = _meter.create_up_down_counter(
        name="chroma.collection.documents",
        description="Number of documents in collection",
        unit="1",
    )


def is_enabled() -> bool:
    """Check if metrics are enabled."""
    return _enabled


# Query Performance Metrics Functions

def record_query_duration(duration_seconds: float, attributes: Optional[Dict[str, Any]] = None) -> None:
    """Record query execution duration.

    Args:
        duration_seconds: Query duration in seconds
        attributes: Optional attributes (e.g., collection_name, operation_type)
    """
    if not _enabled or not _query_duration_histogram:
        return

    attrs = attributes or {}
    attrs["pod_name"] = os.environ.get("HOSTNAME", "unknown")
    _query_duration_histogram.record(duration_seconds, attributes=attrs)


def increment_query_counter(attributes: Optional[Dict[str, Any]] = None) -> None:
    """Increment query counter.

    Args:
        attributes: Optional attributes (e.g., collection_name, operation_type)
    """
    if not _enabled or not _query_counter:
        return

    attrs = attributes or {}
    attrs["pod_name"] = os.environ.get("HOSTNAME", "unknown")
    _query_counter.add(1, attributes=attrs)


def increment_query_error_counter(
    error_type: str,
    attributes: Optional[Dict[str, Any]] = None,
) -> None:
    """Increment query error counter.

    Args:
        error_type: Type of error that occurred
        attributes: Optional attributes (e.g., collection_name, operation_type)
    """
    if not _enabled or not _query_error_counter:
        return

    attrs = attributes or {}
    attrs["error_type"] = error_type
    attrs["pod_name"] = os.environ.get("HOSTNAME", "unknown")
    _query_error_counter.add(1, attributes=attrs)


def record_query_result_size(result_count: int, attributes: Optional[Dict[str, Any]] = None) -> None:
    """Record query result size.

    Args:
        result_count: Number of results returned
        attributes: Optional attributes (e.g., collection_name, operation_type)
    """
    if not _enabled or not _query_result_size_histogram:
        return

    attrs = attributes or {}
    attrs["pod_name"] = os.environ.get("HOSTNAME", "unknown")
    _query_result_size_histogram.record(result_count, attributes=attrs)


# Segment Health Metrics Functions

def update_segment_count(collection_name: str, count_delta: int) -> None:
    """Update segment count for a collection.

    Args:
        collection_name: Name of the collection
        count_delta: Change in segment count (positive or negative)
    """
    if not _enabled or not _segment_count_gauge:
        return

    _segment_count_gauge.add(
        count_delta,
        attributes={
            "collection_name": collection_name,
            "pod_name": os.environ.get("HOSTNAME", "unknown"),
        },
    )


def update_segment_size(
    segment_id: str,
    collection_name: str,
    size_bytes: int,
) -> None:
    """Update segment size.

    Args:
        segment_id: Segment identifier
        collection_name: Name of the collection
        size_bytes: Size of segment in bytes
    """
    if not _enabled or not _segment_size_gauge:
        return

    _segment_size_gauge.add(
        size_bytes,
        attributes={
            "segment_id": segment_id,
            "collection_name": collection_name,
            "pod_name": os.environ.get("HOSTNAME", "unknown"),
        },
    )


def update_segment_records(
    segment_id: str,
    collection_name: str,
    records_delta: int,
) -> None:
    """Update segment record count.

    Args:
        segment_id: Segment identifier
        collection_name: Name of the collection
        records_delta: Change in record count (positive or negative)
    """
    if not _enabled or not _segment_records_gauge:
        return

    _segment_records_gauge.add(
        records_delta,
        attributes={
            "segment_id": segment_id,
            "collection_name": collection_name,
            "pod_name": os.environ.get("HOSTNAME", "unknown"),
        },
    )


# Collection Metrics Functions

def update_collection_count(count_delta: int) -> None:
    """Update total collection count.

    Args:
        count_delta: Change in collection count (positive or negative)
    """
    if not _enabled or not _collection_count_gauge:
        return

    _collection_count_gauge.add(
        count_delta,
        attributes={"pod_name": os.environ.get("HOSTNAME", "unknown")},
    )


def update_documents_per_collection(collection_name: str, documents_delta: int) -> None:
    """Update document count for a collection.

    Args:
        collection_name: Name of the collection
        documents_delta: Change in document count (positive or negative)
    """
    if not _enabled or not _documents_per_collection_gauge:
        return

    _documents_per_collection_gauge.add(
        documents_delta,
        attributes={
            "collection_name": collection_name,
            "pod_name": os.environ.get("HOSTNAME", "unknown"),
        },
    )


# Decorator for automatic query metrics

T = TypeVar("T", bound=Callable)  # type: ignore[type-arg]


def track_query_metrics(
    operation_type: str,
    collection_name_param: Optional[str] = None,
) -> Callable[[T], T]:
    """Decorator to automatically track query metrics.

    Args:
        operation_type: Type of operation (e.g., "query", "get", "add")
        collection_name_param: Parameter name containing collection name (optional)

    Returns:
        Decorated function with automatic metrics tracking
    """
    def decorator(f: T) -> T:
        @wraps(f)
        def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            if not _enabled:
                return f(*args, **kwargs)

            # Extract collection name if parameter specified
            collection_name = None
            if collection_name_param and collection_name_param in kwargs:
                collection_name = kwargs[collection_name_param]

            attributes = {"operation_type": operation_type}
            if collection_name:
                attributes["collection_name"] = collection_name

            # Track query execution
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                duration = time.time() - start_time

                # Record metrics
                increment_query_counter(attributes)
                record_query_duration(duration, attributes)

                # Record result size if applicable
                if hasattr(result, "__len__"):
                    try:
                        record_query_result_size(len(result), attributes)
                    except TypeError:
                        pass  # Not all results have len()

                return result
            except Exception as e:
                duration = time.time() - start_time
                record_query_duration(duration, attributes)
                increment_query_error_counter(
                    error_type=type(e).__name__,
                    attributes=attributes,
                )
                raise

        return wrapper  # type: ignore

    return decorator
