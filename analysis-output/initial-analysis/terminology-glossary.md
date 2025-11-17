# Chroma Terminology Glossary

**Analysis Date:** 2025-11-16
**Commit SHA:** [`091f8bd5c553f8267c48664e98fb32215055f58e`](https://github.com/chroma-core/chroma/commit/091f8bd5c553f8267c48664e98fb32215055f58e)

---

## Introduction

This glossary defines Chroma-specific terms, architectural concepts, and technical vocabulary used throughout the codebase. Terms are organized alphabetically with cross-references.

---

## General Concepts

### **Collection**
A named group of embeddings with associated metadata and documents. Collections are the primary organizational unit in Chroma, analogous to tables in traditional databases.

**Code Reference:** [`chromadb/api/types.py:23-45`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/api/types.py#L23-L45)

**Example:**
```python
collection = client.create_collection("my_documents")
```

**Related:** Database, Tenant, Segment

---

### **Database**
A logical namespace within a tenant that contains collections. Enables multi-database support within a single Chroma instance.

**Default:** "default_database"

**Code Reference:** [`chromadb/api/types.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/api/types.py)

**Related:** Tenant, Collection

---

### **Tenant**
The highest-level isolation boundary in Chroma. Each tenant can have multiple databases. Used for multi-tenancy in shared deployments.

**Default:** "default_tenant"

**Code Reference:** [`chromadb/api/types.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/api/types.py)

**Related:** Database, Multi-tenancy

---

### **Embedding**
A vector representation of data (text, images, etc.) as a list of floating-point numbers. Embeddings capture semantic meaning, allowing similarity search.

**Dimensions:** Typically 384, 768, 1536, or higher depending on the embedding model.

**Example:**
```python
embedding = [0.234, -0.891, 0.442, ...]  # 384 dimensions
```

**Related:** Embedding Function, Vector, HNSW

---

### **Embedding Function**
A function that converts raw data (text, images) into embeddings. Chroma supports pluggable embedding functions.

**Built-in Options:**
- `SentenceTransformerEmbeddingFunction` (default)
- `OpenAIEmbeddingFunction`
- `CohereEmbeddingFunction`
- Custom functions

**Code Reference:** [`chromadb/utils/embedding_functions/`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/utils/embedding_functions)

**Related:** Embedding, ONNX Runtime

---

### **Document**
The raw text or content associated with an embedding. Stored alongside embeddings for retrieval.

**Example:**
```python
document = "Chroma is an embedding database"
```

**Related:** Metadata, Embedding

---

### **Metadata**
Key-value pairs associated with each embedding. Used for filtering and organization.

**Example:**
```python
metadata = {"source": "docs", "page": 5, "author": "Alice"}
```

**Supported Types:** `str`, `int`, `float`, `bool`

**Code Reference:** [`chromadb/api/types.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/api/types.py)

**Related:** Where Clause, Filtering

---

### **ID**
A unique string identifier for each embedding within a collection. Must be unique per collection.

**Example:**
```python
id = "doc_12345"
```

**Related:** Collection

---

## Architecture Components

### **ClientAPI**
The user-facing interface for interacting with Chroma. Defines methods like `create_collection()`, `add()`, `query()`, `get()`, and `delete()`.

**Implementations:**
- `SegmentAPI` (in-process, Python)
- `RustBindingsAPI` (in-process, Rust-accelerated)
- `FastAPI` (client-server, HTTP)
- `CloudAPI` (managed cloud)

**Code Reference:** [`chromadb/api/__init__.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/api/__init__.py)

**Related:** ServerAPI, API Layer

---

### **ServerAPI**
The internal API implementation that handles requests from ClientAPI. Coordinates between segments, executors, and storage.

**Code Reference:** [`chromadb/api/segment.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/api/segment.py)

**Related:** ClientAPI, SegmentAPI

---

### **Segment**
An isolated storage unit responsible for a specific aspect of data (vectors, metadata, or records). Segments are the fundamental building blocks of Chroma's storage layer.

**Types:**
1. **VectorSegment:** Stores embeddings in HNSW index
2. **MetadataSegment:** Stores metadata in SQLite
3. **RecordSegment:** Write-ahead log for durability

**Pattern:** Strategy Pattern (pluggable implementations)

**Code Reference:** [`chromadb/segment/`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/segment)

**Related:** VectorSegment, MetadataSegment, RecordSegment, SegmentManager

---

### **VectorSegment**
A segment that stores and retrieves embeddings using an approximate nearest neighbor (ANN) index.

**Implementation:** HNSW (Hierarchical Navigable Small World)

**Code Reference:** [`chromadb/segment/impl/vector/local_hnsw.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/segment/impl/vector/local_hnsw.py)

**Related:** HNSW, Segment, ANN

---

### **MetadataSegment**
A segment that stores metadata and supports filtering operations using SQL queries.

**Implementation:** SQLite with PyPika query builder

**Code Reference:** [`chromadb/segment/impl/metadata/sqlite.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/segment/impl/metadata/sqlite.py)

**Related:** Segment, SQLite, Where Clause

---

### **RecordSegment**
A segment that maintains a write-ahead log (WAL) for durability and crash recovery.

**Implementation:** Log-structured storage

**Code Reference:** [`chromadb/segment/impl/manager/distributed_manager.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/segment/impl/manager/distributed_manager.py)

**Related:** Segment, WAL, Producer-Consumer

---

### **SegmentManager**
Manages the lifecycle of segments: creation, loading, caching (LRU), and eviction.

**Code Reference:** [`chromadb/segment/impl/manager/local.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/segment/impl/manager/local.py)

**Related:** Segment, LRU Cache

---

### **Executor**
The query execution engine that plans and runs queries against segments.

**Types:**
- **LocalExecutor:** Single-node query execution
- **DistributedExecutor:** Multi-node query coordination

**Code Reference:** [`chromadb/execution/executor/local.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/execution/executor/local.py)

**Related:** Query Plan, Execution Engine

---

### **Query Plan**
A description of how to execute a query. Plans are created by the executor and define the sequence of operations.

**Types:**
- `KNNPlan` - K-nearest neighbor search
- `GetPlan` - Retrieve by IDs
- `CountPlan` - Count records
- `FilterPlan` - Metadata filtering

**Code Reference:** [`chromadb/execution/expression/plan.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/execution/expression/plan.py)

**Related:** Executor, KNN

---

### **System**
The dependency injection container that manages component lifecycle and wiring.

**Responsibilities:**
- Component instantiation
- Dependency resolution
- Configuration management
- Topological sorting of dependencies

**Code Reference:** [`chromadb/config.py:270-450`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/config.py#L270-L450)

**Related:** Component, Settings, DI

---

### **Component**
A base class for all Chroma services and modules. Components declare their dependencies and are managed by the System.

**Pattern:** Service Locator + Dependency Injection

**Code Reference:** [`chromadb/config.py:150-220`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/config.py#L150-L220)

**Related:** System, DI

---

### **Settings**
A Pydantic-based configuration class that defines all configurable parameters for Chroma.

**Configuration Sources:**
- Environment variables
- Configuration files (YAML)
- Code defaults

**Code Reference:** [`chromadb/config.py:40-150`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/config.py#L40-L150)

**Related:** System, Configuration

---

## Storage & Indexing

### **HNSW (Hierarchical Navigable Small World)**
An approximate nearest neighbor (ANN) algorithm used for fast vector similarity search. Chroma uses `hnswlib` (C++ library with Python/Rust bindings).

**Complexity:**
- Build: O(n log n)
- Query: O(log n)

**Parameters:**
- `M`: Number of connections per layer (trade-off: memory vs. accuracy)
- `ef_construction`: Size of dynamic candidate list during construction
- `ef_search`: Size of dynamic candidate list during search

**Reference:** Malkov & Yashunin (2018) - "Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs"

**Code Reference:** [`chromadb/segment/impl/vector/local_hnsw.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/segment/impl/vector/local_hnsw.py)

**Related:** VectorSegment, ANN, KNN

---

### **ANN (Approximate Nearest Neighbor)**
A class of algorithms that find approximately nearest neighbors in high-dimensional spaces. Trade accuracy for speed compared to exact search.

**Chroma's Choice:** HNSW (graph-based ANN)

**Related:** HNSW, KNN

---

### **KNN (K-Nearest Neighbors)**
Finding the K most similar vectors to a query vector based on a distance metric.

**Distance Metrics:**
- L2 (Euclidean distance) - default
- Cosine similarity
- Inner product

**Code Reference:** Query operations in VectorSegment

**Related:** ANN, HNSW, Distance Metric

---

### **SQLite**
An embedded relational database used for metadata storage in Chroma.

**Usage:**
- Metadata filtering
- Collection/database/tenant management
- Transaction support (ACID)

**Mode:** WAL (Write-Ahead Logging) for concurrency

**Code Reference:** [`chromadb/db/impl/sqlite.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/db/impl/sqlite.py)

**Related:** MetadataSegment, SysDB

---

### **SysDB**
The system database that stores metadata about collections, segments, databases, and tenants.

**Implementation:** SQLite by default

**Code Reference:** [`chromadb/db/impl/sqlite.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/db/impl/sqlite.py)

**Related:** SQLite, Collection, Database, Tenant

---

### **WAL (Write-Ahead Log)**
A logging technique that ensures durability by writing changes to a log before applying them to the main data structure.

**Chroma's Implementation:** WAL3 (custom Rust-based WAL)

**Benefits:**
- Crash recovery
- No data loss
- Atomic operations

**Code Reference:** [`rust/wal3/`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/rust/wal3)

**Related:** RecordSegment, Durability, Crash Recovery

---

### **WAL3**
Chroma's custom Write-Ahead Log implementation in Rust. Supports snapshots, compaction, and distributed coordination.

**Features:**
- Sequence-based ordering
- Snapshot creation
- S3-backed persistence
- Garbage collection

**Code Reference:** [`rust/wal3/src/lib.rs`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/rust/wal3)

**Related:** WAL, RecordSegment

---

### **Blockstore**
A columnar storage layer in Rust that stores data in Apache Arrow format.

**Features:**
- Efficient columnar layout
- Compression
- S3 backend support
- Block-level caching

**Code Reference:** [`rust/blockstore/`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/rust/blockstore)

**Related:** Arrow, Parquet, Storage

---

### **Arrow**
Apache Arrow - a columnar memory format for efficient data processing. Used in Chroma's Rust storage layer.

**Benefits:**
- Zero-copy reads
- SIMD optimizations
- Interoperability with data tools

**Code Reference:** Rust blockstore and worker modules

**Related:** Blockstore, Parquet

---

### **Parquet**
Apache Parquet - a columnar storage file format. Chroma uses Parquet for persistent block storage.

**Benefits:**
- Efficient compression
- Column pruning
- Predicate pushdown

**Code Reference:** [`rust/blockstore/`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/rust/blockstore)

**Related:** Arrow, Blockstore

---

## Query & Filtering

### **Where Clause**
A filter expression used to narrow results based on metadata. Supports comparison operators and logical combinations.

**Operators:**
- `$eq`, `$ne` - equality/inequality
- `$gt`, `$gte`, `$lt`, `$lte` - comparisons
- `$in`, `$nin` - membership
- `$and`, `$or` - logical combinations

**Example:**
```python
where = {"$and": [
    {"author": "Alice"},
    {"page": {"$gt": 10}}
]}
```

**Code Reference:** [`chromadb/api/types.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/api/types.py)

**Related:** Where Document, Metadata, Filtering

---

### **Where Document**
A filter expression specifically for document text using substring matching or regular expressions.

**Operators:**
- `$contains` - substring search
- `$not_contains` - negation

**Example:**
```python
where_document = {"$contains": "machine learning"}
```

**Code Reference:** [`chromadb/api/types.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/api/types.py)

**Related:** Where Clause, Document

---

### **Distance Metric**
A function that measures similarity/dissimilarity between vectors.

**Supported Metrics:**
- **L2 (Euclidean):** `sqrt(sum((a[i] - b[i])^2))` - default
- **Cosine:** `1 - (a·b / (||a|| ||b||))`
- **Inner Product (IP):** `a·b`

**Configuration:** Set on collection creation

**Code Reference:** [`chromadb/api/types.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/api/types.py)

**Related:** HNSW, KNN, Similarity Search

---

### **SeqID (Sequence ID)**
A monotonically increasing identifier for log entries. Used to order operations in the write-ahead log.

**Purpose:**
- Ordering guarantees
- Deduplication
- Synchronization in distributed mode

**Code Reference:** [`chromadb/ingest/`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/ingest)

**Related:** WAL, Producer-Consumer

---

## Distributed & Networking

### **Multi-tenancy**
The ability to isolate data and operations for multiple customers (tenants) within a single Chroma deployment.

**Hierarchy:** Tenant → Database → Collection

**Code Reference:** [`chromadb/api/types.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/api/types.py)

**Related:** Tenant, Database, RBAC

---

### **Producer-Consumer**
An asynchronous pattern where writes are queued (Producer) and processed in the background (Consumer).

**Benefits:**
- Non-blocking writes
- Batching for efficiency
- Backpressure handling

**Code Reference:** [`chromadb/ingest/`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/ingest)

**Related:** WAL, SeqID, Ingest

---

### **gRPC**
A high-performance RPC framework used for internal communication in distributed Chroma.

**Usage:**
- Service-to-service communication
- Log service RPC
- Worker coordination

**Code Reference:** [`chromadb/proto/`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/proto)

**Related:** Protocol Buffers, Distributed Mode

---

### **Protocol Buffers (Protobuf)**
Google's serialization format used for RPC and cross-language communication.

**Files:** `.proto` definitions in `chromadb/proto/` and `idl/`

**Code Reference:** [`idl/chromadb/proto/`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/idl/chromadb/proto)

**Related:** gRPC

---

### **Kubernetes (K8s)**
Container orchestration platform. Chroma supports distributed deployment on Kubernetes.

**Tools:**
- Helm charts for deployment
- Tilt for local development

**Code Reference:** [`k8s/`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/k8s)

**Related:** Distributed Mode, Helm, Tilt

---

### **Tilt**
A development tool for Kubernetes that provides hot reloading and integrated logging.

**Usage:** `tilt up` starts a local K8s cluster for Chroma development

**Code Reference:** [`Tiltfile`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/Tiltfile)

**Related:** Kubernetes, Development Environment

---

## Authentication & Security

### **RBAC (Role-Based Access Control)**
A security model that restricts access based on user roles and permissions.

**Roles:** Defined per-tenant or globally

**Code Reference:** [`chromadb/auth/simple_rbac_authz/`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/auth/simple_rbac_authz)

**Related:** Authentication, Authorization, Multi-tenancy

---

### **Token Authentication**
Bearer token-based authentication for API access.

**Flow:**
1. Client obtains token (external auth)
2. Token passed in `Authorization: Bearer <token>` header
3. Server validates token

**Code Reference:** [`chromadb/auth/token_authn/`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/auth/token_authn)

**Related:** RBAC, Authentication

---

### **Basic Authentication**
HTTP Basic Auth (username/password) for API access.

**Format:** `Authorization: Basic <base64(username:password)>`

**Code Reference:** [`chromadb/auth/basic_authn/`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/auth/basic_authn)

**Related:** Authentication

---

### **Quota**
Limits on resource usage (storage, requests, etc.) enforced per tenant or globally.

**Code Reference:** [`chromadb/quota/`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/quota)

**Related:** Rate Limiting, Multi-tenancy

---

### **Rate Limiting**
Throttling of API requests to prevent abuse and ensure fair resource allocation.

**Implementation:** Token bucket algorithm

**Code Reference:** [`chromadb/rate_limit/`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/rate_limit)

**Related:** Quota, API

---

## Observability

### **OpenTelemetry (OTel)**
An observability framework for distributed tracing, metrics, and logging.

**Exporters:** OTLP (gRPC), Honeycomb, Jaeger

**Granularity Levels:**
- `NONE` - No tracing
- `OPERATION` - Top-level operations
- `OPERATION_AND_SEGMENT` - Include segment calls
- `ALL` - Detailed tracing

**Code Reference:** [`chromadb/telemetry/opentelemetry/`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/telemetry/opentelemetry)

**Related:** Tracing, Observability

---

### **Tracing**
Recording execution paths through distributed systems for debugging and performance analysis.

**Implementation:** OpenTelemetry with decorator pattern

**Code Reference:** [`chromadb/telemetry/opentelemetry/__init__.py:106-161`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/telemetry/opentelemetry/__init__.py#L106-L161)

**Related:** OpenTelemetry

---

### **PostHog**
Product analytics platform used for usage tracking and telemetry.

**Events:** User actions, feature usage, errors

**Code Reference:** [`chromadb/telemetry/product/posthog.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/telemetry/product/posthog.py)

**Related:** Telemetry, Analytics

---

## Python-Specific

### **Pydantic**
A data validation library using Python type hints. Used extensively in Chroma for settings and type validation.

**Usage:**
- Settings class validation
- API request/response models
- Configuration management

**Code Reference:** [`chromadb/config.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/config.py), [`chromadb/api/types.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/api/types.py)

**Related:** Settings, Type Safety

---

### **FastAPI**
A modern Python web framework used for Chroma's HTTP server.

**Features:**
- Automatic OpenAPI documentation
- Type validation
- Async support
- Middleware support

**Code Reference:** [`chromadb/server/fastapi/`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/server/fastapi)

**Related:** HTTP Server, API

---

### **Uvicorn**
An ASGI server that runs FastAPI applications.

**Usage:** `uvicorn chromadb.app:app`

**Code Reference:** [`chromadb/app.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/app.py)

**Related:** FastAPI, ASGI

---

### **ONNX Runtime**
An inference engine for running ONNX (Open Neural Network Exchange) models. Used for the default embedding function.

**Default Model:** `all-MiniLM-L6-v2` (384 dimensions)

**Code Reference:** [`chromadb/utils/embedding_functions/onnx_mini_lm_l6_v2.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/utils/embedding_functions/onnx_mini_lm_l6_v2.py)

**Related:** Embedding Function, Default Embedding

---

### **PyPika**
A SQL query builder for Python. Used to construct SQLite queries programmatically.

**Benefits:**
- Type-safe query construction
- Prevents SQL injection
- Composable queries

**Code Reference:** [`chromadb/segment/impl/metadata/sqlite.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/segment/impl/metadata/sqlite.py)

**Related:** SQLite, MetadataSegment

---

## Rust-Specific

### **PyO3**
A Rust library for creating Python bindings. Enables Chroma to call Rust code from Python with low overhead.

**Usage:**
- RustBindingsAPI implementation
- High-performance operations from Python
- Zero-copy data sharing

**Code Reference:** [`rust/python_bindings/`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/rust/python_bindings)

**Related:** RustBindingsAPI, Python-Rust Bridge

---

### **Tokio**
An asynchronous runtime for Rust. Used throughout Chroma's Rust codebase for async I/O.

**Features:**
- Multi-threaded scheduler
- Async I/O
- Timers and utilities

**Code Reference:** All Rust modules

**Related:** Async, Rust

---

### **Tantivy**
A full-text search library in Rust (similar to Apache Lucene).

**Usage:** Full-text search on document content

**Code Reference:** [`rust/index/`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/rust/index)

**Related:** Full-Text Search, Indexing

---

### **Axum**
A web framework for Rust, used for building HTTP services.

**Usage:** Rust-based HTTP server components

**Code Reference:** [`rust/frontend/`](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/rust/frontend)

**Related:** HTTP Server, Rust

---

### **Maturin**
A build tool for Rust-Python projects. Compiles Rust code into Python wheels.

**Usage:** `maturin dev` for development builds

**Code Reference:** [`pyproject.toml:54-59`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/pyproject.toml#L54-L59)

**Related:** PyO3, Build System

---

## Design Patterns & Concepts

### **Dependency Injection (DI)**
A design pattern where dependencies are provided to components rather than created internally.

**Chroma's Implementation:** System class acts as a service locator

**Benefits:**
- Testability (mock dependencies)
- Flexibility (swap implementations)
- Clear dependency graph

**Code Reference:** [`chromadb/config.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/config.py)

**Related:** System, Component

---

### **Strategy Pattern**
A design pattern where algorithms are encapsulated and made interchangeable.

**Chroma's Usage:**
- Segment implementations (vector, metadata, record)
- Embedding functions
- Storage backends

**Related:** Segment, Embedding Function

---

### **Service Locator**
A design pattern that provides a centralized registry for looking up services.

**Chroma's Implementation:** System.instance(Type[T])

**Code Reference:** [`chromadb/config.py:270-450`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/config.py#L270-L450)

**Related:** DI, System

---

### **Lazy Initialization**
Delaying creation of objects until they're first accessed.

**Chroma's Usage:** Components are instantiated only when required

**Code Reference:** [`chromadb/config.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/config.py)

**Related:** Component, System

---

### **LRU Cache (Least Recently Used)**
A caching strategy that evicts the least recently used items when capacity is reached.

**Chroma's Usage:** SegmentManager caches loaded segments

**Code Reference:** [`chromadb/segment/impl/manager/local.py`](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/segment/impl/manager/local.py)

**Related:** SegmentManager, Caching

---

## Acronyms & Abbreviations

| Acronym | Full Term | Description |
|---------|-----------|-------------|
| **ANN** | Approximate Nearest Neighbor | Fast similarity search with accuracy trade-off |
| **API** | Application Programming Interface | User-facing interface |
| **ASGI** | Asynchronous Server Gateway Interface | Python async web server standard |
| **DI** | Dependency Injection | Design pattern for managing dependencies |
| **gRPC** | gRPC Remote Procedure Call | High-performance RPC framework |
| **HNSW** | Hierarchical Navigable Small World | Graph-based ANN algorithm |
| **HTTP** | Hypertext Transfer Protocol | Web communication protocol |
| **K8s** | Kubernetes | Container orchestration platform |
| **KNN** | K-Nearest Neighbors | Finding K most similar items |
| **LOC** | Lines of Code | Code size metric |
| **LRU** | Least Recently Used | Caching eviction strategy |
| **ONNX** | Open Neural Network Exchange | Model interchange format |
| **OTel** | OpenTelemetry | Observability framework |
| **OTLP** | OpenTelemetry Protocol | Telemetry data transfer protocol |
| **RBAC** | Role-Based Access Control | Security model |
| **RPC** | Remote Procedure Call | Inter-service communication |
| **SIMD** | Single Instruction, Multiple Data | CPU parallelism |
| **SQL** | Structured Query Language | Database query language |
| **WAL** | Write-Ahead Log | Durability technique |

---

## Cross-References

### By Domain

**Storage & Indexing:** HNSW, ANN, KNN, SQLite, WAL, WAL3, Blockstore, Arrow, Parquet, SysDB

**Architecture:** ClientAPI, ServerAPI, Segment, VectorSegment, MetadataSegment, RecordSegment, SegmentManager, Executor, System, Component, Settings

**Query & Data:** Collection, Database, Tenant, Embedding, Document, Metadata, ID, Where Clause, Where Document, Distance Metric, SeqID

**Distributed:** Multi-tenancy, Producer-Consumer, gRPC, Protocol Buffers, Kubernetes, Tilt

**Security:** RBAC, Token Authentication, Basic Authentication, Quota, Rate Limiting

**Observability:** OpenTelemetry, Tracing, PostHog

**Frameworks:** FastAPI, Uvicorn, PyO3, Tokio, Tantivy, Axum, Maturin, Pydantic

**Patterns:** DI, Strategy Pattern, Service Locator, Lazy Initialization, LRU Cache

---

## Further Reading

### Internal Documentation
- [Architecture Analysis](/home/user/chroma/ARCHITECTURE_ANALYSIS.md)
- [Repository Structure](/home/user/chroma/analysis-output/initial-analysis/repository-structure.md)
- [Blog Series](/home/user/chroma/analysis-output/blog-series/)

### External References
- **HNSW Paper:** Malkov & Yashunin (2018) - [arXiv:1603.09320](https://arxiv.org/abs/1603.09320)
- **Apache Arrow:** [arrow.apache.org](https://arrow.apache.org/)
- **OpenTelemetry:** [opentelemetry.io](https://opentelemetry.io/)
- **FastAPI:** [fastapi.tiangolo.com](https://fastapi.tiangolo.com/)
- **Pydantic:** [docs.pydantic.dev](https://docs.pydantic.dev/)

---

*This glossary is based on commit [`091f8bd`](https://github.com/chroma-core/chroma/commit/091f8bd5c553f8267c48664e98fb32215055f58e). For the latest terminology, refer to the [official Chroma documentation](https://docs.trychroma.com/).*
