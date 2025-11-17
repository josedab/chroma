# CHROMA CODEBASE - KEY FILES AND DESIGN PATTERNS

## KEY FILES BY FUNCTION

### Entry Points
- `/home/user/chroma/chromadb/__init__.py` (Lines 165-440)
  - EphemeralClient(), PersistentClient(), RustClient(), HttpClient(), CloudClient()
  - Factory functions for all client types

### API Layer
- `/home/user/chroma/chromadb/api/__init__.py`
  - **BaseAPI**: Core interface with _add, _update, _delete, _get, _query, _count, _peek, _modify
  - **ClientAPI**: Extends BaseAPI with collection management
  - **ServerAPI**: Extends both BaseAPI and AdminAPI, adds tenant/database parameters
  - **AdminAPI**: Database and tenant management

- `/home/user/chroma/chromadb/api/client.py`
  - **Client**: Main client implementation (lines 42-100+)
  - Wraps ServerAPI with tenant/database context
  - Handles embedding function attachment to collections

- `/home/user/chroma/chromadb/api/segment.py`
  - **SegmentAPI**: Python-based ServerAPI implementation
  - Uses SysDB, SegmentManager, Executor, Producer
  - Validates batches, enforces quotas/rate limits, builds query plans

- `/home/user/chroma/chromadb/api/rust.py`
  - **RustBindingsAPI**: Rust-backed ServerAPI implementation
  - PyO3 bindings to chromadb_rust_bindings.Bindings
  - Type conversion between Python and Rust types
  - Default implementation for modern Chroma

- `/home/user/chroma/chromadb/api/fastapi.py`
  - **FastAPI**: HTTP client implementation
  - Connects to remote Chroma server
  - Uses httpx for networking, orjson for serialization

### Configuration & Dependency Injection
- `/home/user/chroma/chromadb/config.py`
  - **Component** (lines 334-370): Base class for all system components
    - require(type): Get dependency with automatic registration
    - start()/stop(): Lifecycle management
    
  - **System** (lines 372-492): DI container and service locator
    - instance(type): Get or create component singleton
    - components(): Topological sort for startup/shutdown
    - settings: Pydantic-based configuration
    
  - **Settings** (lines 120-324): Configuration object
    - chroma_api_impl: Which ServerAPI to use
    - chroma_sysdb_impl: System database implementation
    - chroma_segment_manager_impl: Segment manager strategy
    - is_persistent, persist_directory: Storage configuration
    - Migration and schema settings

### Segment Architecture
- `/home/user/chroma/chromadb/segment/__init__.py`
  - **SegmentType** enum: Vector, metadata, record types
  - **SegmentImplementation**: Abstract base for all segments
  - **MetadataReader**: Interface for metadata segments
  - **VectorReader**: Interface for vector segments
  - **SegmentManager**: Abstract interface for segment lifecycle

- `/home/user/chroma/chromadb/segment/impl/manager/local.py` (lines 50-100+)
  - **LocalSegmentManager**: Single-node segment lifecycle
  - SEGMENT_TYPE_IMPLS: Mapping of segment types to implementations
  - _vector_instances_file_handle_cache: LRU cache for file handles
  - segment_cache: Per-scope segment caching strategy

- `/home/user/chroma/chromadb/segment/impl/vector/local_hnsw.py` (lines 37-100+)
  - **LocalHnswSegment**: In-memory HNSW vector index
  - Uses hnswlib.Index for KNN search
  - Consumer subscription pattern for updates
  - Thread-safe with ReadWriteLock

- `/home/user/chroma/chromadb/segment/impl/vector/local_persistent_hnsw.py`
  - **PersistentLocalHnswSegment**: Disk-persisted HNSW
  - File handle pooling to respect OS limits
  - Lazy loading and caching

- `/home/user/chroma/chromadb/segment/impl/metadata/sqlite.py` (lines 43-100+)
  - **SqliteMetadataSegment**: SQLite-backed metadata storage
  - Uses PyPika for SQL generation
  - Handles where/where_document filters
  - Subscribed to consumer log for updates

### Storage Layer
- `/home/user/chroma/chromadb/db/base.py`
  - **Cursor**: Protocol for database cursor interface
  - **TxWrapper**: Transaction wrapper ensuring DBAPI 2.0 consistency
  - **SqlDB**: Abstract database interface
  - **ParameterValue**: PyPika parameter wrapper for inline values

- `/home/user/chroma/chromadb/db/system.py`
  - **SysDB**: System database interface
  - Methods: create/get/delete collection, database, tenant
  - Segment CRUD operations
  - Collection metadata management

- `/home/user/chroma/chromadb/db/impl/sqlite.py`
  - **SqliteDB**: Concrete SQLite implementation
  - Connection pooling via sqlite_pool
  - Schema migrations support
  - Transaction management

- `/home/user/chroma/chromadb/ingest/__init__.py`
  - **Producer**: Submit embeddings to log stream
  - **Consumer**: Subscribe to collection logs
  - encode_vector/decode_vector: Embedding serialization
  - **ConsumerCallbackFn**: Callback type for log consumption

### Execution Layer
- `/home/user/chroma/chromadb/execution/executor/abstract.py`
  - **Executor**: Abstract query executor interface
  - count(CountPlan): Get collection cardinality
  - get(GetPlan): Filtered retrieval with projections
  - knn(KNNPlan): Vector similarity search

- `/home/user/chroma/chromadb/execution/executor/local.py` (lines 43-100+)
  - **LocalExecutor**: Single-node query execution
  - Combines results from metadata and vector segments
  - Applies projections and cleaning (remove chroma: prefixed keys)

- `/home/user/chroma/chromadb/execution/expression/plan.py`
  - **CountPlan**: Query plan for cardinality (dataclass)
  - **GetPlan**: Query plan for retrieval (Scan + Filter + Limit + Projection)
  - **KNNPlan**: Query plan for vector search (Scan + KNN + Filter + Projection)
  - **Search**: Hybrid search builder with where/rank/limit/select

- `/home/user/chroma/chromadb/execution/expression/operator.py`
  - **Where**: Base class for filter expressions (algebraic data type)
  - **Scan**: Collection context (ids, metadata, vector segments)
  - **Filter**: Where and where_document expressions
  - **Limit**: Limit and offset for pagination
  - **Projection**: Which fields to return
  - **KNN**: K-nearest neighbors search parameters
  - **Rank**: Ranking operators (Knn, Rrf)
  - **Key**: Field accessor for building expressions

### Types & Data Models
- `/home/user/chroma/chromadb/types.py`
  - **Collection**: Collection model (TypedDict with id, name, metadata, etc.)
  - **Database**: Database descriptor
  - **Tenant**: Tenant descriptor
  - **VectorQuery**: Query specification for KNN
  - **VectorQueryResult**: Result of KNN search
  - **MetadataEmbeddingRecord**: Metadata + ID pairing
  - **LogRecord**: Operations in log stream
  - **SegmentScope**: VECTOR, METADATA, RECORD

- `/home/user/chroma/chromadb/api/types.py`
  - **Embeddings**: List[List[float]] for dense vectors
  - **SparseVector**: {indices: List[int], values: List[float]}
  - **Metadata**: Dict[str, Union[str, int, float, bool]]
  - **Where**: User-facing metadata filter
  - **WhereDocument**: User-facing text filter
  - **QueryResult**: Returned from query operations
  - **GetResult**: Returned from get operations
  - **Include**: Field selection flags

- `/home/user/chroma/chromadb/api/models/Collection.py`
  - **Collection**: User-facing collection object
  - Methods: add(), query(), get(), delete(), update(), count(), peek()

### Server
- `/home/user/chroma/chromadb/server/fastapi/__init__.py`
  - FastAPI server setup with middleware
  - Route definitions for all operations
  - OpenAPI schema generation
  - Async/await for concurrent request handling

---

## CRITICAL DESIGN PATTERNS

### 1. Component Dependency Injection
```python
# In config.py (lines 334-460)
class Component:
    def require(self, type: Type[T]) -> T:
        inst = self._system.instance(type)
        self._dependencies.add(inst)
        return inst

class System:
    def instance(self, type: Type[T]) -> T:
        if inspect.isabstract(type):
            fqn = settings.require(_abstract_type_keys[get_fqn(type)])
            type = get_class(fqn, type)
        
        if type not in self._instances:
            impl = type(self)
            self._instances[type] = impl
            if self._running:
                impl.start()
        return self._instances[type]
```

**Usage Example**:
```python
class SegmentAPI(ServerAPI):
    def __init__(self, system: System):
        self._sysdb = self.require(SysDB)
        self._manager = self.require(SegmentManager)
        self._executor = self.require(Executor)
```

### 2. Segment Isolation Pattern
```python
# In segment/__init__.py
class SegmentImplementation(Component):
    @abstractmethod
    def count(self, request_version_context: RequestVersionContext) -> int:
        pass
    @abstractmethod
    def max_seqid(self) -> SeqId:
        pass
    @abstractmethod
    def delete(self) -> None:
        pass

# Separate readers for different data types
class MetadataReader(SegmentImplementation):
    @abstractmethod
    def get_metadata(...) -> Sequence[MetadataEmbeddingRecord]:
        pass

class VectorReader(SegmentImplementation):
    @abstractmethod
    def get_vectors(...) -> Sequence[VectorEmbeddingRecord]:
        pass
    @abstractmethod
    def query_vectors(query: VectorQuery) -> Sequence[Sequence[VectorQueryResult]]:
        pass
```

### 3. Producer-Consumer Pattern
```python
# In ingest/__init__.py
class Producer(Component):
    def submit_embedding(collection_id: UUID, embedding: OperationRecord) -> SeqId:
        pass
    def submit_embeddings(collection_id: UUID, embeddings: Sequence[OperationRecord]) -> Sequence[SeqId]:
        pass

class Consumer(Component):
    def subscribe(collection_id: UUID, consume_fn: ConsumerCallbackFn, start: Optional[SeqId]) -> UUID:
        pass
    def unsubscribe(subscription_id: UUID) -> None:
        pass

# Usage in LocalHnswSegment
def start(self) -> None:
    seq_id = self.max_seqid()
    self._subscription = self._consumer.subscribe(
        self._collection, 
        self._write_records,  # Callback to index vectors
        start=seq_id
    )
```

### 4. Query Planning and Execution
```python
# In execution/executor/local.py
class LocalExecutor(Executor):
    def get(self, plan: GetPlan) -> GetResult:
        # Get metadata first
        records = self._metadata_segment(plan.scan.collection).get_metadata(
            where=plan.filter.where,
            where_document=plan.filter.where_document,
            ids=plan.filter.user_ids,
            limit=plan.limit.limit,
            offset=plan.limit.offset,
        )
        
        # Conditionally get vectors if requested
        if plan.projection.embedding:
            vectors = self._vector_segment(plan.scan.collection).get_vectors(
                ids=[r["id"] for r in records],
                request_version_context=plan.scan.version
            )
        
        # Apply transformations and return
        return GetResult(ids=ids, embeddings=embeddings, ...)
```

### 5. Where Expression Algebra
```python
# In execution/expression/operator.py
@dataclass
class Where:
    def __and__(self, other: 'Where') -> 'Where':
        return And(self, other)
    
    def __or__(self, other: 'Where') -> 'Where':
        return Or(self, other)

# Usage
where1 = Key("status") == "active"      # Eq expression
where2 = Key("score") > 0.5              # Gt expression
combined = where1 & where2               # And expression

# Evaluation in SqliteMetadataSegment converts to SQL
# SELECT * FROM embeddings 
# WHERE metadata->>'status' = 'active' AND metadata->>'score' > 0.5
```

### 6. Rust Type Conversion (Adapter Pattern)
```python
# In api/rust.py
class RustBindingsAPI(ServerAPI):
    def _query(self, collection_id: UUID, ...) -> QueryResult:
        # Convert Python types to Rust via bindings
        rust_result = self.bindings.query(
            collection_id=str(collection_id),
            vectors=query_embeddings,  # List[List[float]]
            k=n_results,
            where=where,  # Python Where -> JSON dict
            where_document=where_document,
        )
        
        # Convert Rust results back to Python types
        return QueryResult(
            ids=rust_result.ids,
            embeddings=deserialize_embeddings(rust_result.embeddings),
            distances=rust_result.distances,
            ...
        )
```

### 7. Lazy Initialization with Caching
```python
# In segment/impl/manager/local.py
class LocalSegmentManager(SegmentManager):
    def __init__(self, system: System):
        self._instances: Dict[UUID, SegmentImplementation] = {}
        self.segment_cache: Dict[SegmentScope, SegmentCache] = {
            SegmentScope.METADATA: BasicCache(),
            SegmentScope.VECTOR: SegmentLRUCache(...)  # With memory limits
        }
    
    def _get_segment(self, segment_id: UUID) -> SegmentImplementation:
        if segment_id not in self._instances:
            segment = self._sysdb.get_segments(id=segment_id)[0]
            impl_class = get_class(SEGMENT_TYPE_IMPLS[segment["type"]])
            self._instances[segment_id] = impl_class(self._system, segment)
        return self._instances[segment_id]
```

### 8. Settings-Based Implementation Selection
```python
# In config.py (lines 65-89)
_abstract_type_keys = {
    "chromadb.api.ServerAPI": "chroma_api_impl",
    "chromadb.db.system.SysDB": "chroma_sysdb_impl",
    "chromadb.segment.SegmentManager": "chroma_segment_manager_impl",
    "chromadb.execution.executor.abstract.Executor": "chroma_executor_impl",
}

# When instantiating abstract type:
fqn = settings.require(_abstract_type_keys[get_fqn(ServerAPI)])
# fqn could be:
#  - "chromadb.api.rust.RustBindingsAPI"
#  - "chromadb.api.segment.SegmentAPI"
#  - "chromadb.api.fastapi.FastAPI"
impl_class = get_class(fqn, ServerAPI)
```

---

## DATA STRUCTURE MAPPINGS

### Collection Creation Flow
```
CreateCollectionConfiguration
    ├─ metadata: Dict[str, Any]           # Collection-level metadata
    ├─ hnsw_space: str = "l2"             # Vector distance metric
    ├─ hnsw_batch_size: int = 100
    ├─ hnsw_sync: bool = False
    └─ [Future] blockfile_config: ...

↓ (in SegmentManager.prepare_segments_for_new_collection)

Segment[] = [
    {
        'id': UUID,
        'type': "urn:chroma:segment/metadata/sqlite",
        'scope': SegmentScope.METADATA,
        'collection': collection_id,
        'metadata': {}
    },
    {
        'id': UUID,
        'type': "urn:chroma:segment/vector/hnsw-local-persisted",
        'scope': SegmentScope.VECTOR,
        'collection': collection_id,
        'metadata': {
            'hnsw:space': 'l2',
            'hnsw:M': 4,
            'hnsw:ef_construction': 200,
        }
    },
    {
        'id': UUID,
        'type': "urn:chroma:segment/record/blockfile",
        'scope': SegmentScope.RECORD,
        'collection': collection_id,
        'metadata': {}
    }
]

↓ (stored in SysDB.segments table)
```

### Write Operation Flow
```
OperationRecord = {
    'id': str,
    'embedding': Vector | None,
    'encoding': ScalarEncoding,
    'metadata': Optional[UpdateMetadata],
    'document': Optional[str],
    'uri': Optional[str],
    'operation': Operation,  # ADD, UPDATE, UPSERT, DELETE
}

↓ (Producer.submit_embeddings)

LogRecord = {
    'id': str,
    'embedding': bytes,  # encode_vector(embedding, ScalarEncoding.FLOAT32)
    'seq_id': SeqId,     # Returned from producer
    'collection_id': UUID,
    'operation': Operation,
    'metadata': dict,
}

↓ (Consumer.subscribe callback)

SqliteMetadataSegment._write_metadata:
    - INSERT/UPDATE embeddings table
    - UPDATE max_seq_id

LocalHnswSegment._write_records:
    - hnswlib_index.add_items(ids, vectors)
    - _label_to_id, _id_to_label maps
    - UPDATE max_seq_id
```

---

## IMPORTANT FILE RELATIONSHIPS

```
User Code
    ↓
chromadb.EphemeralClient / PersistentClient / HttpClient
    ↓ (instantiates)
ClientCreator (client.py)
    ↓ (embeds)
ServerAPI (abstract interface)
    ├─ SegmentAPI (segment.py)         [Python implementation]
    │   ├─ requires: SysDB
    │   ├─ requires: SegmentManager
    │   ├─ requires: Executor
    │   └─ requires: Producer/Consumer
    │
    ├─ RustBindingsAPI (rust.py)       [Rust implementation - default]
    │   └─ embeds: chromadb_rust_bindings.Bindings
    │
    └─ FastAPI (fastapi.py)            [HTTP client]
        └─ connects to: remote RustBindingsAPI

SysDB (abstract)
    └─ SqliteDB (db/impl/sqlite.py)

SegmentManager (abstract)
    └─ LocalSegmentManager (segment/impl/manager/local.py)
        └─ creates: VectorReader + MetadataReader instances

VectorReader (abstract)
    ├─ LocalHnswSegment
    └─ PersistentLocalHnswSegment

MetadataReader (abstract)
    └─ SqliteMetadataSegment

Executor (abstract)
    └─ LocalExecutor (execution/executor/local.py)

Producer/Consumer (abstract)
    └─ SqliteDB (double duty: storage + ingest)

Collection (user-facing)
    └─ _client: ServerAPI
        ├─ _collection_id: UUID
        ├─ _embedding_function: EmbeddingFunction
        └─ methods call _client._add, _client._query, etc.
```

---

## CONFIGURATION PATHS

**Default RustClient**:
- chroma_api_impl = "chromadb.api.rust.RustBindingsAPI"
- chroma_sysdb_impl = "chromadb.db.impl.sqlite.SqliteDB"
- is_persistent = True
- persist_directory = ./chroma

**EphemeralClient**:
- chroma_api_impl = "chromadb.api.rust.RustBindingsAPI"
- is_persistent = False (in-memory)

**HttpClient**:
- chroma_api_impl = "chromadb.api.fastapi.FastAPI"
- chroma_server_host = "localhost"
- chroma_server_http_port = 8000
- chroma_server_ssl_enabled = False

**SegmentAPI (Python)** (legacy):
- chroma_api_impl = "chromadb.api.segment.SegmentAPI"
- chroma_segment_manager_impl = "chromadb.segment.impl.manager.local.LocalSegmentManager"
- chroma_executor_impl = "chromadb.execution.executor.local.LocalExecutor"

