RFC-0015: Hot/Cold Data Tiering
Status: Draft
Author: Claude Code Analysis
Created: 2025-11-17
Commit Base: 091f8bd5c553f8267c48664e98fb32215055f58e

## Summary

Implement intelligent hot/cold data tiering to reduce storage costs by 40-60% through automated migration of infrequently accessed collections to cheaper storage tiers (S3 Glacier, Infrequent Access). Collections are automatically promoted/demoted based on access patterns, with transparent query routing ensuring consistent user experience regardless of storage tier.

## Motivation

### Problem Statement

Currently, **all Chroma data is stored in expensive "hot" storage** (S3 Standard, local SSD), regardless of access patterns:

**Cost Analysis** (Typical Enterprise Customer):
- 1TB total data
- 80% is "cold" (accessed <1x/month): 800GB
- 20% is "hot" (accessed daily): 200GB

**Current Cost** (S3 Standard at $0.023/GB/month):
- Total: 1TB × $0.023 = $23/month

**With Tiering** (S3 Glacier at $0.004/GB/month for cold):
- Hot: 200GB × $0.023 = $4.60
- Cold: 800GB × $0.004 = $3.20
- **Total: $7.80/month = 66% savings**

**At Scale** (100TB):
- Current: $2,300/month
- With Tiering: $780/month
- **Savings: $1,520/month = $18.2K/year**

### User Stories

1. **Enterprise Customer**: "We have 50TB of historical embeddings accessed once per quarter. Why are we paying premium S3 pricing for cold data?"

2. **Compliance Officer**: "We need to retain 7 years of data for compliance, but querying old data is rare. Tiering would save $100K/year."

3. **ML Engineer**: "My training datasets are 10TB but only used during re-training (quarterly). Auto-tiering would be perfect."

### Business Impact

- **Cost Reduction**: 40-60% storage savings = $10K-$100K/year per customer
- **Competitive Advantage**: Pinecone/Weaviate lack automated tiering
- **Retention**: Lower costs enable longer data retention
- **Scalability**: Store 10x more data for same budget

## Detailed Design

### Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│                    Query Router                            │
│  - Checks collection tier                                 │
│  - Routes to appropriate storage backend                  │
└────────────┬───────────────────────────────────────────────┘
             │
   ┌─────────┴─────────┬──────────────────────┐
   │                   │                      │
   ↓                   ↓                      ↓
┌────────┐      ┌──────────┐         ┌──────────────┐
│  HOT   │      │   WARM   │         │    COLD      │
│        │      │          │         │              │
│ S3     │      │ S3 IA    │         │ S3 Glacier   │
│ Standard│     │          │         │              │
│        │      │          │         │              │
│ Access: │     │ Access:  │         │ Access:      │
│ <10ms  │     │ ~100ms   │         │ 3-5 hours    │
│        │      │          │         │ (retrieval)  │
│ Cost:  │      │ Cost:    │         │ Cost:        │
│ $23/TB │     │ $12.5/TB │         │ $4/TB        │
└────────┘      └──────────┘         └──────────────┘
     ↑               ↑                      ↑
     │               │                      │
     └───────────────┴──────────────────────┘
              Tiering Manager
         (monitors access, migrates data)
```

### Tiering Policies

**File**: `chromadb/storage/tiering/policy.py`

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

class StorageTier(Enum):
    HOT = "hot"           # S3 Standard
    WARM = "warm"         # S3 Intelligent-Tiering or S3 IA
    COLD = "cold"         # S3 Glacier Flexible Retrieval
    ARCHIVE = "archive"   # S3 Glacier Deep Archive

@dataclass
class TieringPolicy:
    """Policy for automatic data tiering"""

    # HOT → WARM transition
    warm_after_days: int = 30  # No access for 30 days

    # WARM → COLD transition
    cold_after_days: int = 90  # No access for 90 days

    # COLD → ARCHIVE transition
    archive_after_days: int = 365  # No access for 1 year

    # Promotion triggers (opposite direction)
    hot_on_access: bool = True  # Promote to hot on first access
    prefetch_related: bool = False  # Prefetch related collections

    # Cost constraints
    max_retrieval_cost_per_month: float = 100.0  # $100 budget

    # Performance SLAs
    max_query_latency_ms: int = 5000  # Max 5s for cold data retrieval

@dataclass
class CollectionTierMetadata:
    """Metadata tracking collection tier status"""
    collection_id: str
    current_tier: StorageTier
    last_accessed: datetime
    access_count_30d: int
    size_bytes: int
    tier_changed_at: datetime
    estimated_monthly_cost: float
```

### Core Components

#### 1. Tiering Manager

**File**: `chromadb/storage/tiering/manager.py`

```python
from typing import List, Optional
import asyncio
from datetime import datetime, timedelta
from chromadb.config import Component, System
from chromadb.storage.tiering.policy import (
    TieringPolicy,
    StorageTier,
    CollectionTierMetadata
)

class TieringManager(Component):
    """Manages automated data tiering across storage backends"""

    def __init__(self, system: System):
        super().__init__(system)
        self._policy = TieringPolicy(
            warm_after_days=system.settings.get("chroma_tier_warm_after_days", 30),
            cold_after_days=system.settings.get("chroma_tier_cold_after_days", 90),
            archive_after_days=system.settings.get("chroma_tier_archive_after_days", 365)
        )

    async def evaluate_tiering(self) -> List[dict]:
        """
        Evaluate all collections and recommend tier changes.

        Returns list of recommended migrations.
        """
        recommendations = []

        # Get all collection metadata
        collections = await self._get_collection_metadata()

        for col in collections:
            current_tier = col.current_tier
            recommended_tier = self._recommend_tier(col)

            if recommended_tier != current_tier:
                recommendations.append({
                    "collection_id": col.collection_id,
                    "from_tier": current_tier,
                    "to_tier": recommended_tier,
                    "reason": self._explain_recommendation(col, recommended_tier),
                    "cost_impact": self._estimate_cost_impact(col, recommended_tier)
                })

        return recommendations

    def _recommend_tier(self, col: CollectionTierMetadata) -> StorageTier:
        """Recommend storage tier based on access patterns"""
        days_since_access = (datetime.utcnow() - col.last_accessed).days

        # Promote on recent access
        if days_since_access < 7 and col.access_count_30d > 10:
            return StorageTier.HOT

        # Demote based on inactivity
        if days_since_access > self._policy.archive_after_days:
            return StorageTier.ARCHIVE
        elif days_since_access > self._policy.cold_after_days:
            return StorageTier.COLD
        elif days_since_access > self._policy.warm_after_days:
            return StorageTier.WARM
        else:
            return StorageTier.HOT

    async def migrate_collection(
        self,
        collection_id: str,
        to_tier: StorageTier
    ) -> None:
        """Migrate collection to target tier"""

        # Step 1: Copy data to new tier
        await self._copy_to_tier(collection_id, to_tier)

        # Step 2: Update metadata
        await self._update_tier_metadata(collection_id, to_tier)

        # Step 3: Verify migration
        await self._verify_migration(collection_id, to_tier)

        # Step 4: Delete from old tier (if verified)
        await self._cleanup_old_tier(collection_id)

        logger.info(
            f"Migrated collection {collection_id} to {to_tier.value}"
        )

    def _estimate_cost_impact(
        self,
        col: CollectionTierMetadata,
        new_tier: StorageTier
    ) -> dict:
        """Estimate monthly cost change from tier migration"""

        # Storage costs per GB per month
        storage_costs = {
            StorageTier.HOT: 0.023,      # S3 Standard
            StorageTier.WARM: 0.0125,    # S3 IA
            StorageTier.COLD: 0.004,     # S3 Glacier
            StorageTier.ARCHIVE: 0.00099 # S3 Deep Archive
        }

        size_gb = col.size_bytes / (1024**3)

        current_cost = size_gb * storage_costs[col.current_tier]
        new_cost = size_gb * storage_costs[new_tier]

        # Add retrieval costs for cold/archive
        retrieval_cost = 0
        if new_tier in [StorageTier.COLD, StorageTier.ARCHIVE]:
            # Estimate based on access frequency
            monthly_accesses = col.access_count_30d
            retrieval_cost = monthly_accesses * size_gb * 0.01  # $0.01/GB retrieval

        return {
            "current_monthly_cost": current_cost,
            "new_monthly_cost": new_cost + retrieval_cost,
            "monthly_savings": current_cost - (new_cost + retrieval_cost),
            "annual_savings": (current_cost - (new_cost + retrieval_cost)) * 12
        }
```

#### 2. Query Router with Tier Awareness

**File**: `chromadb/storage/tiering/router.py`

```python
from chromadb.storage.tiering.policy import StorageTier
from chromadb.api.types import QueryResult

class TierAwareQueryRouter:
    """Routes queries based on collection storage tier"""

    async def query(
        self,
        collection_id: str,
        query_embeddings: Embeddings,
        **kwargs
    ) -> QueryResult:
        """Execute query with tier-aware routing"""

        # Step 1: Check collection tier
        tier_metadata = await self._get_tier_metadata(collection_id)

        # Step 2: Handle cold data retrieval
        if tier_metadata.current_tier in [StorageTier.COLD, StorageTier.ARCHIVE]:
            logger.info(
                f"Collection {collection_id} is in {tier_metadata.current_tier.value}, "
                f"initiating retrieval"
            )

            # Check if already restored
            if not await self._is_restored(collection_id):
                # Initiate restore (async)
                restore_job = await self._initiate_restore(collection_id)

                # Wait for restore (3-5 hours for Glacier)
                await self._wait_for_restore(restore_job)

            # Promote to warm tier for future queries
            if self._policy.hot_on_access:
                asyncio.create_task(
                    self._tiering_manager.migrate_collection(
                        collection_id,
                        StorageTier.WARM
                    )
                )

        # Step 3: Execute query on appropriate backend
        backend = self._get_backend_for_tier(tier_metadata.current_tier)
        result = await backend.query(collection_id, query_embeddings, **kwargs)

        # Step 4: Update access metrics
        await self._record_access(collection_id)

        return result

    async def _initiate_restore(self, collection_id: str) -> str:
        """Initiate Glacier restore job"""
        # S3 Glacier restore API
        # Returns job ID for polling
        pass

    async def _wait_for_restore(
        self,
        job_id: str,
        timeout_hours: int = 12
    ) -> None:
        """Poll restore job until complete"""
        # Poll every 5 minutes
        # Raise TimeoutError if exceeds timeout
        pass
```

#### 3. S3 Lifecycle Policies

**File**: `chromadb/storage/tiering/lifecycle.py`

```python
import boto3

class S3LifecycleManager:
    """Manages S3 lifecycle policies for automated tiering"""

    def configure_bucket_lifecycle(self, bucket_name: str) -> None:
        """
        Configure S3 lifecycle rules for automatic tiering.

        This provides a backup/complementary mechanism to application-level tiering.
        """
        s3 = boto3.client('s3')

        lifecycle_config = {
            'Rules': [
                {
                    'Id': 'chroma-auto-tier-warm',
                    'Status': 'Enabled',
                    'Transitions': [
                        {
                            'Days': 30,
                            'StorageClass': 'STANDARD_IA'
                        }
                    ]
                },
                {
                    'Id': 'chroma-auto-tier-cold',
                    'Status': 'Enabled',
                    'Transitions': [
                        {
                            'Days': 90,
                            'StorageClass': 'GLACIER'
                        }
                    ]
                },
                {
                    'Id': 'chroma-auto-tier-archive',
                    'Status': 'Enabled',
                    'Transitions': [
                        {
                            'Days': 365,
                            'StorageClass': 'DEEP_ARCHIVE'
                        }
                    ]
                }
            ]
        }

        s3.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration=lifecycle_config
        )
```

### Configuration

**File**: `chromadb/config.py`

```python
# Data Tiering Configuration
chroma_tiering_enabled: bool = False
chroma_tier_warm_after_days: int = 30
chroma_tier_cold_after_days: int = 90
chroma_tier_archive_after_days: int = 365
chroma_tier_hot_on_access: bool = True
chroma_tier_evaluation_interval_hours: int = 24
chroma_tier_max_retrieval_cost: float = 100.0
```

## Example Usage

### Cost Savings Calculation

```python
import chromadb

# Enable tiering
client = chromadb.Client(
    settings=chromadb.Settings(
        chroma_tiering_enabled=True,
        chroma_tier_warm_after_days=30,
        chroma_tier_cold_after_days=90
    )
)

# Create collection (starts in HOT tier)
collection = client.create_collection("historical_data")
collection.add(ids=[...], embeddings=[...])  # Add 1TB of data

# After 30 days of no access: automatically migrates to WARM (S3 IA)
# Cost: $23/month → $12.5/month (46% savings)

# After 90 days of no access: automatically migrates to COLD (S3 Glacier)
# Cost: $12.5/month → $4/month (83% savings)

# Query cold data (triggers restore)
results = collection.query(query_embeddings=[...], n_results=10)
# - Initiates Glacier restore (3-5 hours)
# - Auto-promotes to WARM tier for future queries
# - User experience: First query slow, subsequent queries fast

# Manual tier management
admin = client.get_admin()
recommendations = admin.get_tiering_recommendations()
# [
#   {
#     "collection_id": "abc-123",
#     "from_tier": "hot",
#     "to_tier": "warm",
#     "reason": "No access for 45 days",
#     "cost_impact": {
#       "monthly_savings": 10.50,
#       "annual_savings": 126.00
#     }
#   }
# ]

# Apply recommendations
for rec in recommendations:
    admin.migrate_collection(rec["collection_id"], rec["to_tier"])
```

## Implementation Plan

### Phase 1: Core Tiering (5 dev-days)
- Implement TieringManager and policies
- Build tier metadata tracking
- S3 lifecycle policy integration

### Phase 2: Query Router (4 dev-days)
- Tier-aware query routing
- Glacier restore workflows
- Access pattern tracking

### Phase 3: Automation & Monitoring (2 dev-days)
- Automated tier evaluation cron
- Cost reporting dashboard
- Alerting for retrieval costs

### Phase 4: Documentation (1 dev-day)
- Cost optimization guide
- Tiering best practices
- Migration runbook

## Backwards Compatibility

**Zero Breaking Changes**: Tiering is opt-in, all data defaults to HOT tier.

## Performance Impact

| Tier | Query Latency | Storage Cost (per TB/month) |
|------|---------------|---------------------------|
| HOT | 10-50ms | $23 |
| WARM | 50-100ms | $12.50 |
| COLD | 3-5 hours (first access), 50-100ms (restored) | $4 |
| ARCHIVE | 12 hours (first access), 50-100ms (restored) | $1 |

## Testing Strategy

- Unit tests for tier recommendation logic
- Integration tests for S3 lifecycle policies
- Load tests for cold data retrieval
- Cost validation tests

## Success Criteria

1. **Cost Savings**: 40-60% storage cost reduction for customers with >80% cold data
2. **Automation**: 95%+ of tier migrations happen automatically
3. **Performance**: <5% of queries hit cold retrieval (good cache warming)
4. **Transparency**: Users unaware of tiering unless querying very cold data

## Effort Estimation

**Total: 12 dev-days**

| Phase | Dev-Days |
|-------|----------|
| Core Tiering | 5 |
| Query Router | 4 |
| Automation | 2 |
| Documentation | 1 |

## References

1. AWS S3 Storage Classes: https://aws.amazon.com/s3/storage-classes/
2. S3 Lifecycle Policies: https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html
3. S3 Glacier Pricing: https://aws.amazon.com/s3/pricing/
4. Data Tiering Best Practices: https://aws.amazon.com/blogs/storage/optimizing-your-storage-costs-with-amazon-s3/
