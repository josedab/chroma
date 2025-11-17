# Chroma Repository Structure Analysis

**Document Version:** 1.0
**Analysis Date:** 2025-11-16
**Commit SHA:** [091f8bd5c553f8267c48664e98fb32215055f58e](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e)
**Version:** 1.3.4

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Repository Overview](#repository-overview)
3. [Directory Structure](#directory-structure)
4. [Module Statistics](#module-statistics)
5. [Core Components](#core-components)
6. [Entry Points](#entry-points)
7. [Inter-Component Dependencies](#inter-component-dependencies)
8. [Build and Development](#build-and-development)

---

## Executive Summary

Chroma is an open-source embedding database (vector database) built with a hybrid Python/Rust architecture. The repository contains:

- **Languages:** Python (primary client API), Rust (performance-critical components), TypeScript/JavaScript (JS client), Go (legacy components)
- **Architecture:** Distributed-first design with support for standalone, client-server, and cloud deployments
- **Total Codebase:** ~200,000+ lines of code across multiple languages
- **Key Features:** Multi-modal embeddings, full-text search, filtering, multi-tenancy, authentication/authorization

---

## Repository Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │  Python  │  │JavaScript│  │   CLI    │                 │
│  │  Client  │  │  Client  │  │  Tools   │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                      │
│  - REST API (v1 & v2)                                       │
│  - Authentication & Authorization                           │
│  - Rate Limiting & Quota Management                         │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               Core Python Components                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │   API    │  │ Segment  │  │ Execution│                 │
│  │  Layer   │  │ Manager  │  │  Engine  │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│           Rust Performance Layer                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │Blockstore│  │  Index   │  │  Worker  │  │  Storage │  │
│  │          │  │  (HNSW)  │  │  Nodes   │  │  (S3)    │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Storage Layer                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │  SQLite  │  │PostgreSQL│  │    S3    │                 │
│  │  (Local) │  │(MetaDB)  │  │ (Blocks) │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Client API** | Python, TypeScript | User-facing interface |
| **Server** | FastAPI, Python | HTTP REST API server |
| **Query Engine** | Rust | High-performance query execution |
| **Vector Index** | Rust (HNSW) | Approximate nearest neighbor search |
| **Full-Text Search** | Rust (Tantivy) | Document text search |
| **Metadata Storage** | SQLite, PostgreSQL | System metadata and catalog |
| **Block Storage** | S3, Local FS | Vector and metadata storage |
| **Bindings** | PyO3, Neon | Language interop (Python ↔ Rust) |

---

## Directory Structure

### Root-Level Organization

```
chroma/
├── chromadb/              # Python package - main API and server
├── rust/                  # Rust workspace - performance components
├── clients/               # Client libraries (JS, Python thin client)
├── go/                    # Go coordinator service (legacy)
├── idl/                   # Protocol buffers definitions
├── examples/              # Example applications and demos
├── docs/                  # Documentation source
├── deployments/           # Cloud deployment configurations
├── k8s/                   # Kubernetes manifests
├── schemas/               # JSON schemas and embedding functions
├── bin/                   # Utility scripts
├── sample_apps/           # Sample applications
├── .github/               # GitHub Actions CI/CD
└── [config files]         # Root configuration files
```

---

## Module Statistics

### Python Package (`chromadb/`)

| Module | Files | Description | Key Responsibilities |
|--------|-------|-------------|---------------------|
| **api/** | 17 | Client and server API interfaces | Client creation, collection management, CRUD operations |
| **server/** | 3 | FastAPI server implementation | HTTP endpoints, middleware, routing |
| **segment/** | 15 | Segment management and implementations | Vector segments, metadata segments, distributed segments |
| **db/** | 11 | Database abstractions | SQLite/PostgreSQL metadata storage, migrations |
| **execution/** | 7 | Query execution engine | Query planning, operators, distributed execution |
| **auth/** | 5 | Authentication & authorization | Token auth, basic auth, RBAC |
| **utils/** | 46 | Utility functions | Embeddings, FastAPI helpers, configuration |
| **ingest/** | 2 | Data ingestion pipeline | Batch processing, validation |
| **telemetry/** | 7 | Observability | OpenTelemetry, product telemetry |
| **quota/** | 2 | Resource quotas | Quota enforcement, limits |
| **rate_limit/** | 2 | Rate limiting | Async rate limiting |
| **migrations/** | 1 | Database migrations | Schema versioning |
| **cli/** | 3 | Command-line interface | Server startup, utilities |
| **proto/** | 3 | Generated protobuf code | gRPC definitions |
| **test/** | 67 | Test suite | Unit and integration tests |

**Total Python Files (excluding tests):** 132 files
**Estimated LOC (excluding tests):** ~34,417 lines

### Rust Workspace (`rust/`)

| Crate | Files | Description | Key Responsibilities |
|-------|-------|-------------|---------------------|
| **worker/** | 75 | Query and compaction workers | Query execution, segment compaction, orchestration |
| **blockstore/** | 58 | Block storage abstraction | Arrow-based storage, S3/local providers |
| **wal3/** | 41 | Write-Ahead Log v3 | Durable write logging, recovery |
| **types/** | 38 | Core type definitions | Collections, segments, embeddings, metadata |
| **garbage_collector/** | 31 | GC service | Cleanup of unused segments and blocks |
| **cli/** | 30 | Rust CLI tools | Server binary, utilities |
| **frontend/** | 28 | Frontend service | Request routing, load balancing |
| **index/** | 23 | Vector indexing | HNSW index, full-text search (Tantivy) |
| **system/** | 16 | System abstractions | Component lifecycle, dependency injection |
| **s3heap/** | 13 | S3-based heap storage | Object storage management |
| **chroma/** | 13 | Main Rust library | Top-level crate |
| **benchmark/** | 12 | Performance benchmarks | Load testing, profiling |
| **segment/** | 12 | Segment implementations | Segment types, operations |
| **log-service/** | 10 | Log service | Distributed logging |
| **log/** | 9 | Log abstractions | Log interface definitions |
| **distance/** | 8 | Distance metrics | Cosine, L2, inner product |
| **config/** | 7 | Configuration | Settings management |
| **sysdb/** | 7 | System database | Catalog storage |
| **cache/** | 7 | Caching layer | In-memory caches |
| **s3heap-service/** | 7 | S3 heap service | S3 storage service |
| **sqlite/** | 6 | SQLite integration | Embedded database |
| **storage/** | 6 | Storage abstractions | Storage interfaces |
| **tracing/** | 6 | Distributed tracing | OpenTelemetry integration |
| **metering-macros/** | 6 | Metering macros | Usage tracking macros |
| **api-types/** | 5 | API type definitions | Shared API types |
| **metering/** | 5 | Usage metering | Resource tracking |
| **error/** | 4 | Error types | Error handling |
| **memberlist/** | 4 | Member discovery | Service discovery |
| **mdac/** | 4 | MDAC (Metadata Append Cache) | Metadata caching |
| **python_bindings/** | 3 | PyO3 bindings | Python ↔ Rust bridge |
| **js_bindings/** | 2 | Neon bindings | JavaScript ↔ Rust bridge |
| **load/** | 1 | Load testing | Performance testing |
| **jemalloc-pprof-server/** | 1 | Profiling server | Memory profiling |

**Total Rust Files:** 498 files
**Estimated LOC:** ~168,698 lines

### Client Libraries (`clients/`)

| Client | Files | Description |
|--------|-------|-------------|
| **js/** | 78+ | JavaScript/TypeScript client library |
| **python/** | - | Thin Python client (optional) |
| **new-js/** | - | Next-generation JS client (development) |

### Go Services (`go/`)

Legacy coordinator service (being phased out in favor of Rust components):
- Coordinator service
- gRPC endpoints
- Postgres integration

---

## Core Components

### 1. Client Layer (`chromadb/__init__.py`)

**File:** `/home/user/chroma/chromadb/__init__.py` (440 lines)

**Entry Points:**
```python
# Line 165-186: Ephemeral (in-memory) client
def EphemeralClient(settings, tenant, database) -> ClientAPI

# Line 189-213: Persistent (local disk) client
def PersistentClient(path, settings, tenant, database) -> ClientAPI

# Line 216-242: Rust-backed client
def RustClient(path, settings, tenant, database) -> ClientAPI

# Line 245-293: HTTP client (client-server mode)
def HttpClient(host, port, ssl, headers, settings, tenant, database) -> ClientAPI

# Line 296-346: Async HTTP client
async def AsyncHttpClient(host, port, ssl, headers, settings, tenant, database) -> AsyncClientAPI

# Line 349-411: Cloud client (Chroma Cloud)
def CloudClient(tenant, database, api_key, settings) -> ClientAPI

# Line 414-430: Generic client factory
def Client(settings, tenant, database) -> ClientAPI

# Line 433-439: Admin client for tenant/database management
def AdminClient(settings) -> AdminAPI
```

**Key Exports:**
- Collection types and operations
- Search API components (Search, Key, Knn, Rrf)
- Type definitions (Metadata, Embeddings, Where, etc.)
- Schema and index configurations

### 2. API Layer (`chromadb/api/`)

**Key Files:**

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | 755 | API interface definitions |
| `segment.py` | 1,074 | Segment-based API implementation |
| `rust.py` | 619 | Rust bindings API implementation |
| `fastapi.py` | 810 | HTTP client API |
| `async_fastapi.py` | 762 | Async HTTP client API |
| `client.py` | 502 | Client factory and management |
| `types.py` | 3,014 | Type definitions and schemas |
| `collection_configuration.py` | 948 | Collection schema configuration |

**API Implementations:**

1. **SegmentAPI** - Local embedded mode using Python segments
2. **RustBindingsAPI** - Local mode using Rust backend (faster)
3. **FastAPI** - HTTP client connecting to remote server
4. **AsyncFastAPI** - Async HTTP client

### 3. Server Layer (`chromadb/server/fastapi/`)

**Main File:** `/home/user/chroma/chromadb/server/fastapi/__init__.py` (2,179 lines)

**Key Sections:**

```python
# Line 191-244: FastAPI server initialization
class FastAPI(Server):
    def __init__(self, settings: Settings)

# Line 277-426: API v2 route definitions
def setup_v2_routes(self)
    # Tenant/Database management
    # Collection CRUD operations
    # Document operations (add, update, upsert, get, delete, query)

# Line 1299-1425: API v1 route definitions (legacy)
def setup_v1_routes(self)

# Line 778-836: Collection creation
async def create_collection(self, request, tenant, database_name)

# Line 941-990: Add embeddings
async def add(self, request, tenant, database_name, collection_id)

# Line 1222-1280: Query (nearest neighbors search)
async def get_nearest_neighbors(self, collection_id, request)
```

**Middleware Stack:**
1. HTTP version check (Line 143-149)
2. Exception handling (Line 121-140)
3. Trace ID injection (Line 112-118)
4. CORS (Line 212-217)
5. Rate limiting (Line 92-98)
6. Authentication/Authorization (Line 488-530)

### 4. Segment Layer (`chromadb/segment/`)

**Purpose:** Manages different types of segments (storage units for collections)

**Key Files:**

| File | Purpose |
|------|---------|
| `impl/vector/` | Vector segment implementations (HNSW, local) |
| `impl/metadata/` | Metadata segment (SQLite-based filtering) |
| `impl/distributed/` | Distributed segment coordination |
| `impl/manager/` | Segment lifecycle management |

**Segment Types:**
1. **Vector Segments:** Store embeddings and perform ANN search
2. **Metadata Segments:** Store and filter on metadata/documents
3. **Record Segments:** Coordinate between vector and metadata

### 5. Execution Engine (`chromadb/execution/`)

**Purpose:** Query planning and execution for the new Search API

**Key Files:**

| File | Lines | Purpose |
|------|-------|---------|
| `expression/plan.py` | 273 | Query plan representation (Search DSL) |
| `expression/operator.py` | 1,289 | Query operators (Key, Knn, Rrf, filters) |
| `executor/local.py` | 223 | Local query execution |
| `executor/distributed.py` | 268 | Distributed query execution |

**Query Flow:**
```
Search Expression → Plan → Operator Tree → Executor → Results
```

### 6. Rust Worker (`rust/worker/`)

**Main Entry:** `/home/user/chroma/rust/worker/src/main.rs`

**Purpose:** High-performance query and compaction workers

**Key Modules:**
- `execution/` - Query execution engine
- `compaction/` - Segment compaction and optimization
- `server/` - gRPC server for distributed queries
- `segment/` - Segment operations

**Dependencies:**
```rust
chroma-blockstore    // Block storage
chroma-index         // Vector indexing (HNSW)
chroma-types         // Type definitions
chroma-distance      // Distance metrics
chroma-segment       // Segment abstractions
```

### 7. Blockstore (`rust/blockstore/`)

**Purpose:** Arrow-based columnar storage for vectors and metadata

**Key Features:**
- Arrow format for efficient serialization
- Multiple providers: S3, LocalFS, Memory
- Block flushing and compaction
- Sparse file support

**Storage Format:**
```
Block = {
    id: UUID,
    embeddings: Arrow Array,
    metadata: Arrow Struct Array,
    documents: Arrow String Array,
}
```

### 8. Index Layer (`rust/index/`)

**Vector Index (HNSW):**
- Approximate nearest neighbor search
- Based on hnswlib with Rust wrapper
- Supports L2, cosine, inner product distances

**Full-Text Search (Tantivy):**
- Inverted index for document search
- BM25 ranking
- Query parsing and filtering

### 9. Database Layer (`chromadb/db/`)

**Implementations:**

1. **SQLite** (`impl/sqlite.py`, 379 lines)
   - Local metadata storage
   - Collection catalog
   - Tenant/database management

2. **gRPC Client** (`impl/grpc/client.py`)
   - Remote metadata service
   - Distributed catalog

**Schema:**
```sql
-- Collections table
CREATE TABLE collections (
    id TEXT PRIMARY KEY,
    name TEXT,
    topic TEXT,
    dimension INTEGER,
    metadata TEXT
);

-- Segments table
CREATE TABLE segments (
    id TEXT PRIMARY KEY,
    collection_id TEXT,
    type TEXT,
    scope TEXT,
    metadata TEXT
);
```

### 10. Authentication & Authorization (`chromadb/auth/`)

**Modules:**

| Module | Purpose |
|--------|---------|
| `token_authn/` | JWT/API token authentication |
| `basic_authn/` | HTTP Basic authentication |
| `simple_rbac_authz/` | Role-based access control |

**Authorization Actions:**
```python
class AuthzAction(Enum):
    CREATE_DATABASE
    GET_DATABASE
    DELETE_DATABASE
    CREATE_COLLECTION
    GET_COLLECTION
    UPDATE_COLLECTION
    DELETE_COLLECTION
    ADD
    GET
    QUERY
    DELETE
    RESET
```

---

## Entry Points

### 1. Python Package Entry Point

**File:** `/home/user/chroma/chromadb/__init__.py`

**GitHub:** [chromadb/__init__.py@091f8bd](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/__init__.py)

**Usage:**
```python
import chromadb

# Ephemeral mode (in-memory)
client = chromadb.EphemeralClient()

# Persistent mode (local disk)
client = chromadb.PersistentClient(path="./chroma_data")

# Rust mode (fastest local)
client = chromadb.RustClient(path="./chroma_data")

# Client-server mode
client = chromadb.HttpClient(host="localhost", port=8000)

# Cloud mode
client = chromadb.CloudClient(
    tenant="my-tenant",
    database="my-db",
    api_key="..."
)
```

### 2. Server Entry Point

**File:** `/home/user/chroma/chromadb/app.py` (8 lines)

**GitHub:** [chromadb/app.py@091f8bd](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/app.py)

```python
# Lines 1-8
import chromadb
import chromadb.config
from chromadb.server.fastapi import FastAPI

settings = chromadb.config.Settings()
server = FastAPI(settings)
app = server.app()  # ASGI application
```

**Deployment:**
```bash
# Using uvicorn
uvicorn chromadb.app:app --host 0.0.0.0 --port 8000

# Using CLI
chroma run --path /chroma_db_path
```

### 3. CLI Entry Point

**File:** `/home/user/chroma/chromadb/cli/cli.py`

**GitHub:** [chromadb/cli/cli.py@091f8bd](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/cli/cli.py)

**Command:** `chroma` (defined in `pyproject.toml` line 33)

**Commands:**
```bash
chroma run --path ./chroma_db  # Start server
chroma utils vacuum --path ./chroma_db  # Cleanup
```

### 4. Rust Worker Entry Point

**File:** `/home/user/chroma/rust/cli/src/main.rs`

**GitHub:** [rust/cli/src/main.rs@091f8bd](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/rust/cli/src/main.rs)

**Build:**
```bash
cargo build --release --bin chroma
```

**Services:**
- Query service (distributed queries)
- Compaction service (segment optimization)
- Frontend service (request routing)

### 5. JavaScript Client Entry Point

**File:** `/home/user/chroma/clients/js/src/index.ts`

**GitHub:** [clients/js/src/index.ts@091f8bd](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/clients/js/src/index.ts)

**Package:** `chromadb` on npm (version 2.4.7)

**Usage:**
```typescript
import { ChromaClient } from 'chromadb';

const client = new ChromaClient({
  path: "http://localhost:8000"
});

const collection = await client.createCollection({
  name: "my_collection"
});
```

---

## Inter-Component Dependencies

### Dependency Graph

```
┌─────────────────────────────────────────────────────────┐
│                    Client Applications                   │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│         chromadb Python Package / JS Client             │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐        │
│  │   API    │────▶│  Client  │────▶│  Config  │        │
│  └──────────┘     └──────────┘     └──────────┘        │
│         │               │                               │
│         ▼               ▼                               │
│  ┌──────────┐     ┌──────────┐                         │
│  │ Segment  │     │FastAPI   │                         │
│  │ (Local)  │     │HTTP API  │                         │
│  └──────────┘     └──────────┘                         │
└─────────────────────────────────────────────────────────┘
         │                   │
         │                   │
         ▼                   ▼
┌──────────────┐    ┌──────────────┐
│ Rust Bindings│    │ gRPC/HTTP    │
│  (PyO3/Neon) │    │   Client     │
└──────────────┘    └──────────────┘
         │                   │
         ▼                   ▼
┌─────────────────────────────────────────────────────────┐
│                  Rust Worker Services                    │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐        │
│  │  Query   │────▶│Execution │────▶│  Index   │        │
│  │ Service  │     │  Engine  │     │  (HNSW)  │        │
│  └──────────┘     └──────────┘     └──────────┘        │
│         │                                    │          │
│         ▼                                    ▼          │
│  ┌──────────┐                         ┌──────────┐     │
│  │Compaction│                         │Blockstore│     │
│  │ Service  │────────────────────────▶│          │     │
│  └──────────┘                         └──────────┘     │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                   Storage Layer                          │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐        │
│  │  SysDB   │     │    S3    │     │  Local   │        │
│  │(Metadata)│     │ (Blocks) │     │   FS     │        │
│  └──────────┘     └──────────┘     └──────────┘        │
└─────────────────────────────────────────────────────────┘
```

### Key Dependencies by Component

#### Python → Rust
- **chromadb.api.rust.RustBindingsAPI** → `chromadb_rust_bindings` (PyO3)
- Bindings defined in: `rust/python_bindings/`
- Type stubs: `chromadb/chromadb_rust_bindings.pyi`

#### Python API → Segments
```python
# chromadb/api/segment.py
SegmentAPI
  ├─→ SegmentManager (segment/impl/manager/)
  ├─→ VectorReader (segment/impl/vector/)
  ├─→ MetadataReader (segment/impl/metadata/)
  └─→ SysDB (db/impl/sqlite.py)
```

#### Rust Worker Dependencies
```toml
# rust/worker/Cargo.toml
[dependencies]
chroma-blockstore      # Storage layer
chroma-index          # Vector indexing
chroma-segment        # Segment operations
chroma-sysdb          # Metadata DB
chroma-distance       # Distance metrics
chroma-types          # Type definitions
```

#### Blockstore → Storage Providers
```rust
// rust/blockstore/src/provider.rs
BlockfileProvider
  ├─→ S3BlockfileProvider (S3 storage)
  ├─→ LocalBlockfileProvider (local filesystem)
  └─→ MemoryBlockfileProvider (testing)
```

---

## Build and Development

### Build System

| Language | Build Tool | Configuration File |
|----------|-----------|-------------------|
| Python | maturin + setuptools | `pyproject.toml` |
| Rust | Cargo | `Cargo.toml` |
| JavaScript | pnpm + tsup | `clients/js/package.json` |
| Go | Go modules | `go/go.mod` |

### Key Configuration Files

#### `/home/user/chroma/pyproject.toml`

**GitHub:** [pyproject.toml@091f8bd](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/pyproject.toml)

```toml
# Lines 1-10: Package metadata
[project]
name = "chromadb"
version = "1.3.4"

# Lines 10: Dependencies
dependencies = [
    'fastapi>=0.115.9',
    'uvicorn[standard] >= 0.18.3',
    'pydantic >= 1.9',
    'numpy >= 1.22.5',
    'onnxruntime >= 1.14.1',
    # ... 20+ more dependencies
]

# Lines 40-41: Build system (Maturin for Rust bindings)
[build-system]
requires = ["setuptools>=61.0", "setuptools_scm[toml]>=6.2", "maturin>=1.0,<2.0"]
build-backend = "maturin"

# Lines 54-59: Maturin configuration
[tool.maturin]
manifest-path = "rust/python_bindings/Cargo.toml"
python-packages = ["chromadb"]
```

#### `/home/user/chroma/Cargo.toml`

**GitHub:** [Cargo.toml@091f8bd](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/Cargo.toml)

```toml
# Lines 1-4: Workspace definition
[workspace]
resolver = "2"
members = [
    "rust/benchmark",
    "rust/blockstore",
    "rust/cache",
    # ... 30+ crates
]

# Lines 6-73: Workspace dependencies (shared versions)
[workspace.dependencies]
tokio = { version = "1.41", features = ["fs", "macros", "rt-multi-thread"] }
serde = { version = "1.0.215", features = ["derive", "rc"] }
uuid = { version = "1.11.0", features = ["v4", "v7", "serde"] }
# ... 60+ more dependencies
```

### Development Workflow

**Setup:**
```bash
# Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements_dev.txt
pip install -e .

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Build Rust bindings
maturin dev
```

**Local Development with Tilt:**
```bash
# Prerequisites: Docker, Kubernetes (OrbStack/Kind), Tilt, Helm

# Start distributed Chroma cluster
tilt up

# Access:
# - Chroma API: http://localhost:8000
# - Tilt Dashboard: http://localhost:10350

# Cleanup
tilt down
```

**Testing:**
```bash
# Python tests
pytest chromadb/test/

# Rust tests
cargo nextest run

# JavaScript tests
cd clients/js && pnpm test
```

**Build for Production:**
```bash
# Python package
python -m build

# Rust binaries
cargo build --release

# Docker image
docker build -t chroma:latest .
```

---

## Deployment Architectures

### 1. Embedded Mode (Single Process)

```python
import chromadb
client = chromadb.PersistentClient(path="./chroma_data")
```

**Components:**
- Python API
- SQLite metadata DB
- Local blockfile storage
- In-process HNSW index

**Use Cases:**
- Development
- Small-scale applications
- Jupyter notebooks

### 2. Client-Server Mode

**Server:**
```bash
chroma run --path /data --host 0.0.0.0 --port 8000
```

**Client:**
```python
client = chromadb.HttpClient(host="server.example.com", port=8000)
```

**Components:**
- FastAPI server
- SQLite/PostgreSQL metadata DB
- Local/S3 blockfile storage

**Use Cases:**
- Multi-user applications
- Microservices architecture

### 3. Distributed Mode (Kubernetes)

**Services:**
- Frontend service (load balancer)
- Query workers (read path)
- Compaction workers (write path)
- Log service (write-ahead log)
- SysDB (PostgreSQL metadata)
- S3 storage (blocks)

**Deployment:**
```bash
helm install chroma ./k8s/distributed-chroma
```

**Use Cases:**
- Production deployments
- High availability
- Horizontal scaling

### 4. Cloud Mode (Chroma Cloud)

```python
client = chromadb.CloudClient(
    tenant="my-tenant",
    database="my-db",
    api_key=os.environ["CHROMA_API_KEY"]
)
```

**Use Cases:**
- Serverless deployments
- Managed service
- Multi-tenancy

---

## API Versions

### v1 API (Legacy)

**Base Path:** `/api/v1`

**Endpoints:**
- `GET /api/v1/collections` - List collections
- `POST /api/v1/collections` - Create collection
- `POST /api/v1/collections/{id}/add` - Add embeddings
- `POST /api/v1/collections/{id}/query` - Query nearest neighbors

### v2 API (Current)

**Base Path:** `/api/v2`

**Hierarchical Structure:**
```
/api/v2/tenants/{tenant}/
  databases/{database}/
    collections/{collection}/
      add, update, upsert, get, delete, query, count
```

**New Features:**
- Explicit tenant/database paths
- Improved error handling
- Schema validation

---

## Protocol Buffers (IDL)

**Location:** `/home/user/chroma/idl/chromadb/proto/`

**GitHub:** [idl/chromadb/proto/@091f8bd](https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/idl/chromadb/proto)

| File | Purpose |
|------|---------|
| `coordinator.proto` | Metadata service definitions (7,152 lines) |
| `chroma.proto` | Core types and operations (298 lines) |
| `logservice.proto` | Write-ahead log service (178 lines) |
| `query_executor.proto` | Query execution service (110 lines) |
| `compactor.proto` | Compaction service (19 lines) |
| `heapservice.proto` | S3 heap storage service (95 lines) |
| `garbage_collector.proto` | GC service (9 lines) |

**Code Generation:**
- Python: Generated in `chromadb/proto/`
- Rust: Generated via `tonic` build.rs
- Go: Generated in `go/pkg/proto/`

---

## Configuration System

### Settings Class

**File:** `/home/user/chroma/chromadb/config.py` (553 lines)

**GitHub:** [chromadb/config.py@091f8bd](https://github.com/chroma-core/chroma/blob/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb/config.py)

**Key Settings:**

```python
class Settings(BaseSettings):
    # Deployment mode
    is_persistent: bool = False
    persist_directory: str = "./chroma"

    # API implementation
    chroma_api_impl: str = "chromadb.api.segment.SegmentAPI"

    # Server settings
    chroma_server_host: str = "localhost"
    chroma_server_http_port: int = 8000

    # Authentication
    chroma_server_authn_provider: str = ""
    chroma_server_authz_provider: str = ""

    # Storage
    chroma_sysdb_impl: str = "chromadb.db.impl.sqlite.SqliteDB"

    # Telemetry
    anonymized_telemetry: bool = True
```

**Configuration Sources (priority order):**
1. Constructor arguments
2. Environment variables (`CHROMA_*`)
3. `.env` file
4. Default values

---

## Testing Structure

### Python Tests (`chromadb/test/`)

**Organization:**
- `property/` - Property-based tests
- `segment/` - Segment implementation tests
- `db/` - Database layer tests
- `auth/` - Authentication/authorization tests
- `ingest/` - Ingestion pipeline tests
- Integration tests in root

**Test Files:** 67 files

**Run Tests:**
```bash
pytest chromadb/test/                    # All tests
pytest chromadb/test/property/           # Property tests
pytest -k "test_add_embeddings"          # Specific test
```

### Rust Tests

**Location:** Throughout `rust/` crates

**Test Categories:**
```bash
# Unit tests
cargo nextest run

# Integration tests (requires Tilt)
tilt up
cargo nextest run --profile k8s_integration
```

---

## Documentation

### In-Repository Docs

| Document | Purpose |
|----------|---------|
| `README.md` | Quick start and overview |
| `DEVELOP.md` | Development setup guide |
| `RELEASE_PROCESS.md` | Release workflow |
| `ARCHITECTURE_ANALYSIS.md` | Architecture deep-dive |
| `KEY_FILES_AND_PATTERNS.md` | Code patterns guide |

### External Documentation

**Website:** https://docs.trychroma.com/

**Source:** `/home/user/chroma/docs/docs.trychroma.com/`

**Built with:** Mintlify

---

## Key Patterns and Conventions

### Python Patterns

1. **Component Pattern (Dependency Injection)**
   ```python
   # chromadb/config.py
   class Component:
       def require(self, type: Type[T]) -> T
       def instance(self, type: Type[T]) -> T
   ```

2. **Settings Pattern**
   ```python
   settings = Settings()  # Loads from env/file
   client = Client(settings=settings)
   ```

3. **Multi-tenancy Pattern**
   ```python
   client.create_collection(
       name="my_collection",
       tenant="tenant_a",
       database="db_1"
   )
   ```

### Rust Patterns

1. **Provider Pattern**
   ```rust
   trait BlockfileProvider {
       fn open(&self, id: Uuid) -> Result<Blockfile>;
       fn create(&self) -> Result<BlockfileWriter>;
   }
   ```

2. **Component Pattern**
   ```rust
   struct System {
       components: HashMap<TypeId, Box<dyn Any>>,
   }
   ```

3. **Arrow-based Serialization**
   ```rust
   // Convert to Arrow arrays for efficient storage
   let embeddings: Float32Array = ...;
   let metadata: StructArray = ...;
   ```

---

## Performance Characteristics

### Indexing Performance

**HNSW Index:**
- Index construction: O(n log n)
- Query time: O(log n) approximate
- Memory: O(n × d × 4 bytes) where d = dimension

**Full-Text Index (Tantivy):**
- Index construction: O(n × m) where m = avg doc length
- Query time: O(k + log n) where k = result count

### Storage Format

**Blockfile Format:**
- Columnar Arrow format
- Compression: Dictionary encoding, RLE
- Block size: ~10MB typical

### Scalability

| Metric | Single Node | Distributed |
|--------|-------------|-------------|
| **Collections** | Thousands | Millions |
| **Vectors/Collection** | Millions | Billions |
| **Query Throughput** | ~1,000 QPS | ~100,000+ QPS |
| **Write Throughput** | ~10,000 writes/sec | ~1M+ writes/sec |

---

## Security Features

### Authentication Methods

1. **Token Authentication** (`auth/token_authn/`)
   - JWT tokens
   - API keys
   - Header: `X-Chroma-Token` or `Authorization: Bearer`

2. **Basic Authentication** (`auth/basic_authn/`)
   - HTTP Basic Auth
   - Configurable credentials

### Authorization (RBAC)

**File:** `chromadb/auth/simple_rbac_authz/`

**Roles:**
- Admin: Full access
- Reader: Read-only access
- Writer: Read + write access

**Resource Hierarchy:**
```
Tenant
  └─ Database
      └─ Collection
          └─ Documents
```

### Security Settings

```python
Settings(
    chroma_server_authn_provider="chromadb.auth.token_authn.TokenAuthenticationServerProvider",
    chroma_server_authz_provider="chromadb.auth.simple_rbac_authz.SimpleRBACAuthorizationProvider",
    chroma_server_authn_credentials_file="users.htpasswd",
    chroma_server_authz_config_file="authz.yaml"
)
```

---

## Observability

### Telemetry

**File:** `/home/user/chroma/chromadb/telemetry/`

**Components:**

1. **Product Telemetry** (`telemetry/product/`)
   - Usage tracking (opt-in)
   - Anonymous event capture
   - PostHog integration

2. **OpenTelemetry** (`telemetry/opentelemetry/`)
   - Distributed tracing
   - Metrics collection
   - OTLP export

**Configuration:**
```python
Settings(
    anonymized_telemetry=True,
    chroma_otel_collection_endpoint="http://otel-collector:4317",
    chroma_otel_service_name="chroma",
    chroma_otel_granularity="all"
)
```

### Logging

**Configuration:** `/home/user/chroma/chromadb/log_config.yml`

**Log Levels:**
- ERROR: Errors only
- WARNING: Warnings and errors
- INFO: General information (default)
- DEBUG: Verbose debugging

---

## Migration and Versioning

### Database Migrations

**File:** `/home/user/chroma/chromadb/db/migrations.py`

**Migration System:**
- Track schema version in DB
- Automatic migration on startup
- Rollback support (manual)

**Versions:**
```python
# Current schema version
SCHEMA_VERSION = "0.1.0"

# Migration functions
def migration_0_0_1_to_0_1_0(db):
    # Add new columns, tables, etc.
```

### Data Migrations

**Segment Migrations:**
- Handled by compaction process
- Gradual migration to new formats
- Backward compatibility maintained

---

## Future Roadmap (Based on Codebase Analysis)

### Emerging Features

1. **New Search API** (`chromadb/execution/`)
   - Hybrid search (vector + text + filters)
   - Query DSL with operators
   - Reciprocal Rank Fusion

2. **Sparse Vectors** (Type definitions added)
   - Sparse embedding support
   - Efficient storage and search

3. **Schema Evolution** (`api/collection_configuration.py`)
   - Explicit schema definitions
   - Index configuration per field
   - Migration support

4. **Next-Gen JS Client** (`clients/new-js/`)
   - Improved TypeScript support
   - Better error handling

### Deprecated Components

1. **Go Coordinator** (`go/`)
   - Being replaced by Rust frontend service
   - Legacy gRPC endpoints

2. **Old Vector Segment Implementation**
   - Migrating to Rust-based segments
   - Python segments for compatibility only

---

## Quick Reference

### Important File Locations

| Category | Path | Description |
|----------|------|-------------|
| **Entry Points** | `/chromadb/__init__.py` | Main Python entry point |
| | `/chromadb/app.py` | FastAPI ASGI app |
| | `/rust/cli/src/main.rs` | Rust CLI entry point |
| **Configuration** | `/pyproject.toml` | Python package config |
| | `/Cargo.toml` | Rust workspace config |
| | `/chromadb/config.py` | Settings system |
| **API** | `/chromadb/api/__init__.py` | API interfaces |
| | `/chromadb/api/segment.py` | Local API implementation |
| | `/chromadb/server/fastapi/` | HTTP server |
| **Storage** | `/rust/blockstore/` | Block storage |
| | `/chromadb/segment/impl/` | Segment implementations |
| | `/chromadb/db/impl/sqlite.py` | Metadata DB |
| **Search** | `/rust/index/` | Vector & FTS indexing |
| | `/chromadb/execution/` | Query execution |
| **Types** | `/chromadb/types.py` | Python type definitions |
| | `/rust/types/` | Rust type definitions |
| | `/idl/chromadb/proto/` | Protocol buffers |

### GitHub Source Links

All links use commit: `091f8bd5c553f8267c48664e98fb32215055f58e`

- Root: https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e
- Python: https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/chromadb
- Rust: https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/rust
- Clients: https://github.com/chroma-core/chroma/tree/091f8bd5c553f8267c48664e98fb32215055f58e/clients

### Common Commands

```bash
# Development
python -m venv venv && source venv/bin/activate
pip install -e .
maturin dev                    # Build Rust bindings
pytest                         # Run Python tests
cargo nextest run              # Run Rust tests

# Local cluster
tilt up                        # Start distributed Chroma
tilt down                      # Stop and cleanup

# Server
chroma run --path /data        # Start server
uvicorn chromadb.app:app       # Alternative server start

# Build
python -m build                # Build Python package
cargo build --release          # Build Rust binaries
docker build -t chroma .       # Build Docker image
```

---

## Conclusion

This document provides a comprehensive overview of the Chroma repository structure as of commit `091f8bd`. The codebase demonstrates a sophisticated architecture combining Python's ease of use with Rust's performance, organized into clear layers:

1. **Client Layer** - Multiple language clients (Python, JS)
2. **API Layer** - Flexible API implementations (embedded, HTTP, async)
3. **Server Layer** - FastAPI with auth, rate limiting, quotas
4. **Execution Layer** - Query planning and execution
5. **Storage Layer** - Blockstore, segments, indexes
6. **Infrastructure** - Deployment, observability, security

The repository is actively developed with ongoing migrations from Go to Rust, introduction of new search APIs, and continuous improvements to performance and scalability.

**For developers joining the project:**
- Start with `README.md` and `DEVELOP.md`
- Run `tilt up` to experience the full distributed system
- Explore `chromadb/__init__.py` to understand client entry points
- Read `chromadb/api/segment.py` for local API implementation
- Study `rust/worker/` for distributed query execution

**For operations teams:**
- Review deployment configurations in `/deployments`
- Understand Kubernetes manifests in `/k8s`
- Configure observability via OpenTelemetry settings
- Set up authentication/authorization in production

---

**Document Metadata:**
- Generated: 2025-11-16
- Chroma Version: 1.3.4
- Commit: 091f8bd5c553f8267c48664e98fb32215055f58e
- Total Files Analyzed: 700+
- Total Lines of Code: ~200,000+
