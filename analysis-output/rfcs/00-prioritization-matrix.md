# RFC Prioritization Matrix

**Generated:** 2025-11-17
**Commit Base:** 091f8bd5c553f8267c48664e98fb32215055f58e

## Executive Summary

This matrix prioritizes 10 proposed RFCs for the Chroma codebase based on Impact vs Effort analysis. Each RFC is scored on business impact (1-10) and development effort (in dev-days), then categorized into strategic buckets.

## Scoring Methodology

### Impact Score (1-10)
- **1-3:** Minor improvement, affects edge cases
- **4-6:** Moderate improvement, affects common workflows
- **7-8:** Significant improvement, enables new use cases or major performance gains
- **9-10:** Critical improvement, addresses major pain points or unlocks strategic initiatives

### Effort Estimation (Dev-Days)
- Includes design, implementation, testing, and documentation
- Assumes experienced developer familiar with codebase
- Does not include code review or deployment time

### Categories
- **Quick Wins:** High impact, low effort (< 10 dev-days)
- **Strategic:** High impact, moderate-high effort (10-25 dev-days)
- **Long-term:** High impact, very high effort (> 25 dev-days)
- **Consider:** Lower impact initiatives to evaluate

---

## Impact vs Effort Matrix

```
Impact
  10 │                                    RFC-0010 (Read Replicas)
   9 │              RFC-0006 (Compaction) RFC-0007 (Multi-Vector)
   8 │   RFC-0002
   7 │   (Lazy ONNX) RFC-0003 (Streaming)  RFC-0001 (Pydantic V2)
   6 │              RFC-0004 (Distance)
   5 │   RFC-0009   RFC-0008 (GraphQL)    RFC-0005 (Observability)
   4 │   (Benchmarks)
   3 │
   2 │
   1 │
   0 └─────────────────────────────────────────────────────────→
     0   5        10        15        20        25        30    Effort (dev-days)
```

---

## RFC Rankings by Priority

### 🟢 TIER 1: Quick Wins (Ship in Sprint 1)

#### 1. RFC-0002: Lazy Loading for ONNX Runtime
- **Impact:** 8/10
- **Effort:** 3 dev-days
- **ROI:** 2.67x
- **Why Now:** Immediate developer experience win, minimal risk, reduces import time by 2-3 seconds
- **Stakeholders:** All Python SDK users

#### 2. RFC-0009: Benchmark Suite & Performance Regression Testing
- **Impact:** 5/10
- **Effort:** 7 dev-days
- **ROI:** 0.71x
- **Why Now:** Prevents regressions before more complex work begins, establishes baseline metrics
- **Stakeholders:** Core team, CI/CD pipeline

---

### 🟡 TIER 2: Strategic Investments (Ship in Q1)

#### 3. RFC-0001: Pydantic V2 Migration
- **Impact:** 7/10
- **Effort:** 10 dev-days
- **ROI:** 0.70x
- **Why Now:** Foundation for future type safety improvements, 5-10x validation speedup
- **Dependencies:** None
- **Risk:** Medium (breaking changes in validation behavior)

#### 4. RFC-0003: Streaming Query Results API
- **Impact:** 7/10
- **Effort:** 15 dev-days
- **ROI:** 0.47x
- **Why Now:** User-reported pain point, enables large-scale use cases
- **Dependencies:** None
- **Risk:** Low (additive API)

#### 5. RFC-0004: Pluggable Distance Metrics System
- **Impact:** 6/10
- **Effort:** 8 dev-days
- **ROI:** 0.75x
- **Why Now:** Frequently requested, enables research use cases (Hamming, Jaccard, custom metrics)
- **Dependencies:** None
- **Risk:** Low (extension system)

#### 6. RFC-0005: Enhanced Observability Dashboard
- **Impact:** 5/10
- **Effort:** 12 dev-days
- **ROI:** 0.42x
- **Why Now:** Essential for production deployments, debugging becomes easier
- **Dependencies:** Telemetry infrastructure exists
- **Risk:** Low

#### 7. RFC-0008: GraphQL API Layer
- **Impact:** 5/10
- **Effort:** 10 dev-days
- **ROI:** 0.50x
- **Why Now:** Modern web client experience, type-safe queries, introspection
- **Dependencies:** FastAPI exists
- **Risk:** Low (additive)

---

### 🔴 TIER 3: Long-term Strategic (Plan for Q2)

#### 8. RFC-0006: Automatic Segment Compaction
- **Impact:** 9/10
- **Effort:** 20 dev-days
- **ROI:** 0.45x
- **Why Now:** Critical for production stability, but requires careful design
- **Dependencies:** Distributed coordination (already exists)
- **Risk:** High (data integrity, distributed consensus)

#### 9. RFC-0007: Multi-Vector Embeddings per Document
- **Impact:** 9/10
- **Effort:** 25 dev-days
- **ROI:** 0.36x
- **Why Now:** Enables ColBERT, late-interaction models, next-gen retrieval
- **Dependencies:** Schema system changes
- **Risk:** High (storage format changes, index changes)

#### 10. RFC-0010: Read Replicas for Query Scaling
- **Impact:** 10/10
- **Effort:** 30 dev-days
- **ROI:** 0.33x
- **Why Now:** Critical for scale, but requires significant distributed systems work
- **Dependencies:** Log replication (exists), segment synchronization
- **Risk:** Very High (distributed consistency, operational complexity)

---

## Detailed RFC Scorecard

| RFC | Title | Impact | Effort | ROI | Category | Priority |
|-----|-------|--------|--------|-----|----------|----------|
| RFC-0002 | Lazy ONNX Loading | 8 | 3d | 2.67 | Quick Win | P0 |
| RFC-0009 | Benchmark Suite | 5 | 7d | 0.71 | Quick Win | P0 |
| RFC-0001 | Pydantic V2 | 7 | 10d | 0.70 | Strategic | P1 |
| RFC-0004 | Distance Metrics | 6 | 8d | 0.75 | Strategic | P1 |
| RFC-0003 | Streaming API | 7 | 15d | 0.47 | Strategic | P1 |
| RFC-0008 | GraphQL API | 5 | 10d | 0.50 | Strategic | P2 |
| RFC-0005 | Observability | 5 | 12d | 0.42 | Strategic | P2 |
| RFC-0006 | Compaction | 9 | 20d | 0.45 | Long-term | P3 |
| RFC-0007 | Multi-Vector | 9 | 25d | 0.36 | Long-term | P3 |
| RFC-0010 | Read Replicas | 10 | 30d | 0.33 | Long-term | P4 |

---

## Recommended Implementation Sequence

### Sprint 1 (2 weeks)
1. **RFC-0002** (Lazy ONNX) - 3 days
2. **RFC-0009** (Benchmarks) - 7 days

### Sprint 2-3 (4 weeks)
3. **RFC-0001** (Pydantic V2) - 10 days
4. **RFC-0004** (Distance Metrics) - 8 days

### Sprint 4-5 (4 weeks)
5. **RFC-0003** (Streaming API) - 15 days
6. **RFC-0008** (GraphQL API) - 10 days (parallel)

### Sprint 6 (2 weeks)
7. **RFC-0005** (Observability) - 12 days

### Q2 Planning
8. **RFC-0006** (Compaction) - 4 weeks
9. **RFC-0007** (Multi-Vector) - 5 weeks
10. **RFC-0010** (Read Replicas) - 6 weeks

---

## Risk Assessment

### Low Risk (Ship Soon)
- RFC-0002, RFC-0009, RFC-0004, RFC-0008, RFC-0005
- Additive changes, minimal API surface changes

### Medium Risk (Requires Testing)
- RFC-0001, RFC-0003
- Changes to core validation/serialization logic, new API patterns

### High Risk (Requires Design Review)
- RFC-0006, RFC-0007, RFC-0010
- Distributed systems, storage format changes, complex migration paths

---

## Success Metrics

### Q1 Goals
- Ship 7 RFCs (0002, 0009, 0001, 0004, 0003, 0008, 0005)
- Achieve 20% performance improvement (RFC-0001)
- Reduce import time by 50% (RFC-0002)
- Zero performance regressions (RFC-0009)

### Q2 Goals
- Complete distributed architecture improvements (RFC-0006, RFC-0010)
- Enable next-gen retrieval models (RFC-0007)
- 10x query throughput for read-heavy workloads (RFC-0010)

---

## Dependency Graph

```
RFC-0009 (Benchmarks)
    ↓
RFC-0001 (Pydantic V2) ──→ RFC-0003 (Streaming API)
    ↓
RFC-0006 (Compaction) ──→ RFC-0010 (Read Replicas)
    ↓
RFC-0007 (Multi-Vector)

RFC-0002 (Lazy ONNX) ← Independent
RFC-0004 (Distance Metrics) ← Independent
RFC-0008 (GraphQL API) ← Independent
RFC-0005 (Observability) ← Independent
```

---

## Budget Summary

### Q1 Total: 75 dev-days (15 weeks with 1 engineer, or 7.5 weeks with 2 engineers)
- Quick Wins: 10 dev-days
- Strategic: 65 dev-days

### Q2 Total: 75 dev-days
- Long-term Strategic: 75 dev-days

### Full Program: 150 dev-days (~30 weeks with 1 engineer, or ~15 weeks with 2 engineers)

---

## Notes & Assumptions

1. **Parallelization:** Some RFCs can be worked on in parallel (e.g., RFC-0008 and RFC-0003)
2. **Learning Curve:** Estimates assume familiarity with Rust, Python, distributed systems
3. **Testing Rigor:** High-risk RFCs include extra time for property testing and chaos engineering
4. **Documentation:** Each RFC includes 1-2 days for docs/examples
5. **Community Input:** Strategic RFCs should have RFC review period (1 week, not in estimate)

---

## Approval Status

| Stakeholder | Status | Date | Notes |
|-------------|--------|------|-------|
| Engineering Lead | Pending | - | - |
| Product Manager | Pending | - | - |
| CTO | Pending | - | - |

---

## Revision History

- **v1.0** (2025-11-17): Initial prioritization matrix created
