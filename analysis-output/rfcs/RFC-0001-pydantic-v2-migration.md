# RFC-0001: Pydantic V2 Migration

**Status:** Draft
**Author:** Claude Code Analysis
**Created:** 2025-11-17
**Commit Base:** 091f8bd5c553f8267c48664e98fb32215055f58e

---

## Summary

Migrate Chroma from Pydantic V1 to Pydantic V2 to achieve 5-10x faster validation, improved type safety, better error messages, and modern Python typing features. This migration affects all models, API types, and configuration classes across the codebase.

---

## Motivation

### Current State

Chroma currently uses `pydantic>=1.9` as specified in:
- `/home/user/chroma/requirements.txt:18` - `pydantic>=1.9`
- `/home/user/chroma/pyproject.toml:10` - `'pydantic >= 1.9'`

The codebase already has compatibility shims for Pydantic V2:
```python
# chromadb/config.py:15-24
in_pydantic_v2 = False
try:
    from pydantic import BaseSettings
except ImportError:
    in_pydantic_v2 = True
    from pydantic.v1 import BaseSettings
    from pydantic.v1 import validator

if not in_pydantic_v2:
    from pydantic import validator  # type: ignore # noqa
```

### Problems with Current Approach

1. **Performance Bottleneck:** Pydantic V1 validation is 5-10x slower than V2 (Rust-based core)
2. **Type Safety Gaps:** Limited support for modern Python typing (TypedDict, Literal, etc.)
3. **Error Messages:** V1 error messages are less actionable than V2's detailed validation errors
4. **Maintenance Burden:** Supporting both V1 and V2 via shims adds complexity
5. **Missing Features:** Can't use V2's strict mode, custom validators with better typing, or performance optimizations

### User Impact

- **API Latency:** Collection creation, query validation, and metadata parsing are slower
- **Developer Experience:** Type hints don't catch errors that V2 would prevent
- **Error Debugging:** Less helpful validation errors when schemas are violated

### Key Files Affected

```
chromadb/types.py:11          - from pydantic import BaseModel
chromadb/api/types.py:24      - from pydantic import BaseModel
chromadb/config.py:15-24      - Compatibility shims
chromadb/server/fastapi/types.py:32 - from pydantic import BaseModel
chromadb/auth/__init__.py     - Authentication models
```

---

## Detailed Design

### Phase 1: Dependency Update & Compatibility Layer

#### 1.1 Update Requirements

**File:** `/home/user/chroma/requirements.txt`
```diff
-pydantic>=1.9
+pydantic>=2.0,<3.0
```

**File:** `/home/user/chroma/pyproject.toml`
```diff
-'pydantic >= 1.9',
+'pydantic >= 2.0, < 3.0',
```

#### 1.2 Remove V1 Compatibility Shims

**File:** `chromadb/config.py:15-24`

Current code:
```python
in_pydantic_v2 = False
try:
    from pydantic import BaseSettings
except ImportError:
    in_pydantic_v2 = True
    from pydantic.v1 import BaseSettings
    from pydantic.v1 import validator

if not in_pydantic_v2:
    from pydantic import validator  # type: ignore # noqa
```

New code:
```python
from pydantic_settings import BaseSettings
from pydantic import field_validator
```

Note: Pydantic V2 moved `BaseSettings` to a separate package `pydantic-settings`.

#### 1.3 Add New Dependency

Add to requirements:
```
pydantic-settings>=2.0.0
```

---

### Phase 2: Model Migration

#### 2.1 BaseModel Changes

**File:** `chromadb/types.py:70-90`

Current Collection model:
```python
class Collection(
    BaseModel,
    BaseModelJSONSerializable["Collection"],
):
    """A model of a collection used for transport, serialization, and storage"""

    id: UUID
    name: str
    configuration_json: Dict[str, Any]
    serialized_schema: Optional[Dict[str, Any]]
    metadata: Optional[
        Dict[str, Any]
    ]  # Dict[str, Any] needed by pydantic 1.x as it doesn't work well Union types and converts all types to str
    dimension: Optional[int]
    tenant: str
    database: str
    version: int
    log_position: int
```

Updated for V2:
```python
from pydantic import ConfigDict

class Collection(
    BaseModel,
    BaseModelJSONSerializable["Collection"],
):
    """A model of a collection used for transport, serialization, and storage"""

    model_config = ConfigDict(
        strict=False,  # Allow type coercion for backwards compatibility
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    id: UUID
    name: str
    configuration_json: Dict[str, Any]
    serialized_schema: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None  # V2 handles Union types properly
    dimension: Optional[int] = None
    tenant: str
    database: str
    version: int = 0
    log_position: int = 0
```

#### 2.2 Validator Migration

Pydantic V2 replaces `@validator` with `@field_validator` and `@model_validator`.

**File:** `chromadb/config.py:130-134`

Current code:
```python
@validator("chroma_server_nofile", pre=True, always=True, allow_reuse=True)
def empty_str_to_none(cls, v: str) -> Optional[str]:
    if type(v) is str and v.strip() == "":
        return None
    return v
```

Updated for V2:
```python
from pydantic import field_validator

@field_validator("chroma_server_nofile", mode='before')
@classmethod
def empty_str_to_none(cls, v: str) -> Optional[str]:
    if isinstance(v, str) and v.strip() == "":
        return None
    return v
```

Key changes:
- `@validator` → `@field_validator`
- `pre=True` → `mode='before'`
- Remove `allow_reuse=True` (no longer needed)
- Add `@classmethod` decorator explicitly

#### 2.3 Settings Migration

**File:** `chromadb/config.py:120-150`

Current Settings class inherits from `BaseSettings`. In V2, move to `pydantic-settings`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',  # Ignore unknown fields from environment
    )

    environment: str = ""
    chroma_api_impl: str = "chromadb.api.rust.RustBindingsAPI"
    # ... rest of settings
```

---

### Phase 3: API Type Updates

#### 3.1 FastAPI Integration

**File:** `chromadb/server/fastapi/types.py`

Pydantic V2 has better FastAPI integration. Update response models:

```python
from pydantic import BaseModel, Field, ConfigDict

class CreateCollection(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "my_collection",
            "metadata": {"description": "My first collection"},
            "configuration": {"hnsw:space": "cosine"}
        }
    })

    name: str = Field(..., min_length=1, max_length=256)
    metadata: Optional[Dict[str, Any]] = None
    configuration: Optional[Dict[str, Any]] = None
```

#### 3.2 Type Validation Improvements

**File:** `chromadb/api/types.py:24`

Add stricter validation with V2 features:

```python
from pydantic import field_validator, model_validator
from typing import Annotated
from pydantic import Field

# Use Annotated for constraints
IDs = Annotated[List[str], Field(min_length=1, max_length=41666)]  # Max batch size

class QueryResult(BaseModel):
    ids: List[List[ID]]
    embeddings: Optional[List[List[Embedding]]] = None
    documents: Optional[List[List[Document]]] = None
    metadatas: Optional[List[List[Metadata]]] = None
    distances: Optional[List[List[float]]] = None

    @model_validator(mode='after')
    def validate_consistent_lengths(self) -> 'QueryResult':
        """Ensure all non-None fields have consistent lengths"""
        lengths = {
            'ids': len(self.ids),
        }
        if self.embeddings is not None:
            lengths['embeddings'] = len(self.embeddings)
        if self.documents is not None:
            lengths['documents'] = len(self.documents)

        if len(set(lengths.values())) > 1:
            raise ValueError(f"Inconsistent lengths: {lengths}")
        return self
```

---

## Example Usage

### Before (Pydantic V1)

```python
from pydantic import BaseModel, validator

class MyModel(BaseModel):
    name: str
    age: int

    @validator('age')
    def age_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('age must be positive')
        return v

    class Config:
        validate_assignment = True
```

### After (Pydantic V2)

```python
from pydantic import BaseModel, field_validator, ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    name: str
    age: int

    @field_validator('age')
    @classmethod
    def age_must_be_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError('age must be positive')
        return v
```

---

## Implementation Plan

### Milestone 1: Foundation (2 dev-days)
- [ ] Update `pydantic` dependency to `>=2.0,<3.0`
- [ ] Add `pydantic-settings>=2.0.0`
- [ ] Remove V1 compatibility shims in `config.py`
- [ ] Update Settings class to use `pydantic-settings`
- [ ] Run test suite, document breaking changes

### Milestone 2: Core Models (3 dev-days)
- [ ] Migrate `chromadb/types.py` models
- [ ] Migrate `chromadb/api/types.py` models
- [ ] Update all `@validator` to `@field_validator`
- [ ] Add `model_config` to all BaseModel classes
- [ ] Fix type hints and Optional defaults

### Milestone 3: Server & API (2 dev-days)
- [ ] Migrate FastAPI types (`chromadb/server/fastapi/types.py`)
- [ ] Update authentication models (`chromadb/auth/__init__.py`)
- [ ] Test FastAPI OpenAPI schema generation
- [ ] Verify JSON serialization compatibility

### Milestone 4: Testing & Documentation (3 dev-days)
- [ ] Update all test fixtures
- [ ] Add migration guide for custom embedding functions
- [ ] Performance benchmark (validation speed)
- [ ] Update API documentation
- [ ] Add changelog entry

---

## Backwards Compatibility

### Breaking Changes

1. **Validator Signatures:** Custom validators must be updated to V2 syntax
2. **Config Classes:** `class Config` → `model_config = ConfigDict(...)`
3. **Parsing Methods:** `parse_obj()` → `model_validate()`, `parse_raw()` → `model_validate_json()`
4. **Dict Methods:** `.dict()` → `.model_dump()`, `.json()` → `.model_dump_json()`

### Migration Path

#### For End Users
- **No Breaking Changes** for standard API usage
- Collection creation, queries, and get operations work identically
- Error messages may have slightly different formats (improvement)

#### For Custom Embedding Functions
Provide migration guide:

```python
# OLD (V1)
class MyEmbedding(EmbeddingFunction):
    @validator('config')
    def validate_config(cls, v):
        return v

# NEW (V2)
class MyEmbedding(EmbeddingFunction):
    @field_validator('config')
    @classmethod
    def validate_config(cls, v: dict) -> dict:
        return v
```

#### For Plugin Developers
- Update documentation: https://docs.trychroma.com/migrations/pydantic-v2
- Provide compatibility checker script:

```bash
python scripts/check_pydantic_v2_compat.py /path/to/plugin
```

---

## Alternatives Considered

### Alternative 1: Stay on Pydantic V1
**Rejected:** Misses performance gains, V1 will be deprecated

### Alternative 2: Support Both V1 and V2 Indefinitely
**Rejected:** Maintenance burden, can't use V2-specific features

### Alternative 3: Gradual Migration with Feature Flags
**Rejected:** Adds complexity, delays benefits

### Alternative 4: Fork and Maintain V1 Internally
**Rejected:** Unsustainable, misses security patches

---

## Security Considerations

### Strict Mode
Pydantic V2 offers strict mode for zero type coercion:
```python
model_config = ConfigDict(strict=True)
```

**Decision:** Start with `strict=False` for backwards compatibility, consider enabling per-model in future.

### Validation Bypasses
V2 has `model_construct()` to bypass validation (faster but dangerous).

**Mitigation:**
- Code review to prevent misuse
- Lint rule to flag `model_construct()` usage

---

## Performance Impact

### Expected Improvements

1. **Validation Speed:** 5-10x faster (Rust core)
   - Collection creation: ~100ms → ~10-20ms (small collections)
   - Query validation: ~50ms → ~5-10ms (100 queries)

2. **Memory:** 10-20% reduction in model memory footprint

3. **Startup Time:** Negligible change (both compile validators at import)

### Benchmarking Plan

```python
# Benchmark script: benchmarks/pydantic_v2_migration.py
import timeit
from chromadb.api.types import Collection

def benchmark_collection_parse():
    data = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "test_collection",
        "metadata": {"key": "value"},
        # ... full collection data
    }
    Collection(**data)

# Run 10,000 iterations
v1_time = timeit.timeit(benchmark_collection_parse, number=10000)
v2_time = timeit.timeit(benchmark_collection_parse, number=10000)
print(f"V1: {v1_time:.4f}s, V2: {v2_time:.4f}s, Speedup: {v1_time/v2_time:.2f}x")
```

---

## Testing Strategy

### Unit Tests
- [ ] All existing tests pass with V2
- [ ] Add tests for V2-specific features (strict mode, custom validators)
- [ ] Test error message format changes

### Integration Tests
- [ ] FastAPI integration tests
- [ ] Client-server serialization tests
- [ ] Distributed mode tests

### Property Tests
```python
from hypothesis import given, strategies as st

@given(st.from_type(Collection))
def test_collection_roundtrip_v2(collection):
    """Property test: Collection serialization is lossless"""
    json_str = collection.model_dump_json()
    restored = Collection.model_validate_json(json_str)
    assert restored == collection
```

### Migration Tests
- [ ] Test V1 serialized data can be loaded in V2
- [ ] Test V2 data is backwards compatible (where possible)

---

## Documentation Requirements

### User-Facing Docs
1. **Migration Guide:** `docs/migrations/pydantic-v2.md`
   - What changed for end users (minimal)
   - How to migrate custom embedding functions
   - Error message format changes

2. **API Documentation:** Update all examples using `.dict()` → `.model_dump()`

3. **Changelog:** Add to `CHANGELOG.md` under "Breaking Changes"

### Internal Docs
1. **Developer Guide:** How to write models in V2
2. **Validator Patterns:** Common V2 validator examples
3. **Performance Benchmarks:** Document improvements

---

## Open Questions

1. **Strict Mode Strategy:** When/where to enable strict validation?
   - **Proposal:** Start with non-strict, enable per-endpoint in future

2. **Custom Types:** Should we use V2's custom types for UUIDs, URIs?
   - **Proposal:** Use Annotated types for better error messages

3. **Serialization Aliases:** Should we use V2 alias features for field renaming?
   - **Proposal:** No, keep field names consistent with V1

4. **Validation Performance:** Should we cache validators for hot paths?
   - **Proposal:** Yes, use `model_validate` with reuse for repeated validations

---

## Success Criteria

### Must Have
- [ ] All tests pass with Pydantic V2
- [ ] Zero runtime errors in staging environment (1 week soak)
- [ ] API contracts unchanged (same JSON in/out)
- [ ] Performance improvement ≥ 3x for validation operations

### Should Have
- [ ] Migration guide published
- [ ] Performance benchmarks documented
- [ ] Improved error messages demonstrated
- [ ] Zero user-reported issues related to migration (first 2 weeks)

### Nice to Have
- [ ] Type hints validated with mypy strict mode
- [ ] Strict mode enabled for internal APIs
- [ ] Custom Pydantic types for domain models

---

## Effort Estimation

| Phase | Task | Dev-Days |
|-------|------|----------|
| 1 | Dependency update, remove shims | 2 |
| 2 | Core models migration | 3 |
| 3 | Server & API types | 2 |
| 4 | Testing & documentation | 3 |
| **Total** | | **10 dev-days** |

**Assumptions:**
- Developer familiar with both Pydantic versions
- Test suite already comprehensive
- Parallel work possible (e.g., docs while testing)

---

## Stakeholder Approvals

| Stakeholder | Role | Status | Date | Notes |
|-------------|------|--------|------|-------|
| Engineering Lead | Approval | Pending | - | - |
| API Team Lead | Review | Pending | - | - |
| DevOps Lead | Deployment | Pending | - | Infrastructure impact |

---

## Rollback/Migration Strategy

### Rollback Plan
If critical issues found in production:

1. **Immediate Rollback:**
   ```bash
   pip install pydantic==1.10.13
   git revert <migration-commit>
   ```

2. **Monitoring:** Track error rates in first 48 hours
   - Alert on validation errors > baseline
   - Monitor API latency changes

3. **Feature Flag (Future):**
   ```python
   if settings.use_pydantic_v2:
       from chromadb.types_v2 import Collection
   else:
       from chromadb.types import Collection
   ```

### Data Migration
- **Not Required:** Pydantic V2 reads V1 serialized data
- **Verification:** Run tests with prod data snapshots

---

## References

### Documentation
- [Pydantic V2 Migration Guide](https://docs.pydantic.dev/latest/migration/)
- [Pydantic V2 Performance](https://docs.pydantic.dev/latest/concepts/performance/)
- [FastAPI + Pydantic V2](https://fastapi.tiangolo.com/release-notes/#0100)

### Related Issues
- GitHub Issue #123: Slow collection creation (example)
- GitHub Issue #456: Type validation inconsistencies (example)

### Similar Migrations
- [Qdrant Pydantic V2 Migration](https://github.com/qdrant/qdrant/pull/1234) (example reference)
- [LangChain Pydantic V2 Migration](https://github.com/langchain-ai/langchain/pull/5678) (example reference)

### Prior Art
- FastAPI's migration to V2 (2023)
- SQLModel's V2 support strategy

---

## Appendix A: Complete File Checklist

Files requiring updates (in migration order):

### Critical Path (Must Update)
- [ ] `chromadb/config.py` - Settings and validators
- [ ] `chromadb/types.py` - Core types
- [ ] `chromadb/api/types.py` - API types
- [ ] `chromadb/server/fastapi/types.py` - FastAPI models

### Important (Update Early)
- [ ] `chromadb/auth/__init__.py` - Auth models
- [ ] `chromadb/auth/basic_authn/__init__.py`
- [ ] `chromadb/auth/token_authn/__init__.py`
- [ ] `chromadb/server/fastapi/__init__.py`

### Testing (Update After Core)
- [ ] `chromadb/test/api/test_types.py`
- [ ] `chromadb/test/api/test_schema.py`

---

## Appendix B: Validation Performance Benchmark

Expected results:

| Operation | V1 Time | V2 Time | Speedup |
|-----------|---------|---------|---------|
| Parse Collection (simple) | 100µs | 15µs | 6.7x |
| Parse Collection (complex) | 500µs | 60µs | 8.3x |
| Validate QueryResult | 200µs | 25µs | 8.0x |
| Settings initialization | 1ms | 150µs | 6.7x |

**Total validation overhead reduction:** ~85% for typical workloads
