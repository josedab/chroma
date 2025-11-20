RFC-0016: Embedding Drift Detection & Quality Monitoring
Status: Draft
Author: Claude Code Analysis
Created: 2025-11-17
Commit Base: 091f8bd5c553f8267c48664e98fb32215055f58e

## Summary

Implement automated monitoring and alerting for embedding quality degradation, model drift, and data distribution shifts. This system continuously tracks embedding statistics (similarity distributions, cluster quality, outliers) and alerts when quality metrics degrade, enabling proactive model updates before users notice accuracy drops.

## Motivation

### Problem Statement

Embedding quality can degrade silently due to:

1. **Model Drift**: Embedding model updated upstream (OpenAI, Cohere) with different outputs
2. **Data Distribution Shift**: New domain-specific vocabulary not in training data
3. **Preprocessing Changes**: Tokenization bugs, encoding issues
4. **Quality Degradation**: Noisy/malformed input documents

**Real-World Example**:
```
Week 1: OpenAI updates text-embedding-ada-002 model
Week 2: Customer embeddings start diverging from existing corpus
Week 3: Search quality drops 30%, customers complain
Week 4: Customer churns, $50K ARR lost
```

**Current Gap**: No automated detection, customers discover issues before engineers.

### User Stories

1. **ML Engineer**: "I need alerts when embedding similarity distribution shifts significantly, indicating potential model drift."

2. **Product Manager**: "Search quality dropped last month. How can we detect quality regressions before customers notice?"

3. **Data Scientist**: "I want to track embedding cluster cohesion over time to monitor semantic consistency."

### Business Impact

- **Revenue Protection**: Prevent churn from undetected quality issues ($50K-$500K/incident)
- **Unique Feature**: No vector DB offers embedding quality monitoring
- **ML Quality Assurance**: Confidence in production embeddings
- **Proactive Support**: Fix issues before customers report them

## Detailed Design

### Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│              Continuous Monitoring Loop                    │
│                                                            │
│  Every N hours:                                           │
│  1. Sample embeddings from collections                    │
│  2. Compute quality metrics                               │
│  3. Compare to baseline                                   │
│  4. Alert on significant drift                            │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────────┐
│              Quality Metrics Computed                      │
│                                                            │
│  Statistical:                                             │
│  - Mean/std of pairwise similarities                      │
│  - Embedding norm distribution                            │
│  - Dimensionality (PCA variance explained)                │
│                                                            │
│  Semantic:                                                │
│  - Cluster cohesion (silhouette score)                    │
│  - Outlier detection (isolation forest)                   │
│  - Nearest neighbor consistency                           │
│                                                            │
│  Comparative:                                             │
│  - KL divergence from baseline                            │
│  - Wasserstein distance                                   │
│  - Statistical hypothesis tests                           │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────────┐
│              Alert & Dashboard                            │
│                                                            │
│  Alerts:                                                  │
│  - Slack/PagerDuty when drift detected                   │
│  - Severity levels (warning, critical)                    │
│                                                            │
│  Dashboard:                                               │
│  - Time series of quality metrics                        │
│  - Drift scores over time                                │
│  - Collection comparison                                 │
└────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Embedding Quality Metrics

**File**: `chromadb/monitoring/embedding_quality.py`

```python
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
from scipy import stats
from scipy.spatial.distance import cosine
from sklearn.decomposition import PCA
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score

@dataclass
class EmbeddingQualityMetrics:
    """Comprehensive embedding quality metrics"""

    # Statistical Metrics
    mean_norm: float  # Average L2 norm
    std_norm: float  # Std dev of norms
    mean_similarity: float  # Avg pairwise cosine similarity
    std_similarity: float  # Std dev of similarities
    percentile_25_similarity: float
    percentile_75_similarity: float

    # Dimensionality Metrics
    pca_variance_explained_90: int  # Dims needed for 90% variance
    intrinsic_dimensionality: float  # Estimated intrinsic dims

    # Cluster Quality
    silhouette_score: float  # Cluster cohesion (-1 to 1)
    num_clusters: int  # Detected clusters
    outlier_percentage: float  # % of outliers

    # Drift Detection
    kl_divergence_from_baseline: float  # Distribution shift
    wasserstein_distance: float  # Distribution distance

    # Timestamp
    computed_at: datetime
    sample_size: int

class EmbeddingQualityAnalyzer:
    """Analyzes embedding quality and detects drift"""

    def compute_metrics(
        self,
        embeddings: np.ndarray,
        baseline_metrics: Optional[EmbeddingQualityMetrics] = None
    ) -> EmbeddingQualityMetrics:
        """
        Compute comprehensive quality metrics.

        Args:
            embeddings: (N, D) array of embeddings
            baseline_metrics: Historical baseline for drift detection

        Returns:
            Quality metrics
        """
        N, D = embeddings.shape

        # 1. Statistical Metrics
        norms = np.linalg.norm(embeddings, axis=1)
        mean_norm = np.mean(norms)
        std_norm = np.std(norms)

        # Pairwise similarities (sample for large N)
        sample_size = min(1000, N)
        sample_idx = np.random.choice(N, sample_size, replace=False)
        sample_emb = embeddings[sample_idx]

        similarities = []
        for i in range(sample_size):
            for j in range(i+1, sample_size):
                sim = 1 - cosine(sample_emb[i], sample_emb[j])
                similarities.append(sim)

        similarities = np.array(similarities)
        mean_sim = np.mean(similarities)
        std_sim = np.std(similarities)
        p25_sim = np.percentile(similarities, 25)
        p75_sim = np.percentile(similarities, 75)

        # 2. Dimensionality Analysis
        pca = PCA(n_components=min(D, 100))
        pca.fit(embeddings)
        variance_explained = np.cumsum(pca.explained_variance_ratio_)
        dims_90 = np.argmax(variance_explained >= 0.90) + 1

        # Intrinsic dimensionality (MLE estimator)
        intrinsic_dim = self._estimate_intrinsic_dim(embeddings)

        # 3. Cluster Quality
        # Use DBSCAN for clustering
        clustering = DBSCAN(eps=0.3, min_samples=5, metric='cosine')
        labels = clustering.fit_predict(sample_emb)

        num_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        outlier_pct = np.sum(labels == -1) / len(labels) * 100

        # Silhouette score (skip if too few clusters)
        if num_clusters > 1:
            sil_score = silhouette_score(sample_emb, labels, metric='cosine')
        else:
            sil_score = 0.0

        # 4. Drift Detection
        kl_div = 0.0
        wasserstein = 0.0
        if baseline_metrics:
            # KL divergence of similarity distributions
            kl_div = self._compute_kl_divergence(
                similarities,
                baseline_metrics.mean_similarity,
                baseline_metrics.std_similarity
            )

            # Wasserstein distance
            wasserstein = stats.wasserstein_distance(
                similarities,
                np.random.normal(
                    baseline_metrics.mean_similarity,
                    baseline_metrics.std_similarity,
                    len(similarities)
                )
            )

        return EmbeddingQualityMetrics(
            mean_norm=mean_norm,
            std_norm=std_norm,
            mean_similarity=mean_sim,
            std_similarity=std_sim,
            percentile_25_similarity=p25_sim,
            percentile_75_similarity=p75_sim,
            pca_variance_explained_90=dims_90,
            intrinsic_dimensionality=intrinsic_dim,
            silhouette_score=sil_score,
            num_clusters=num_clusters,
            outlier_percentage=outlier_pct,
            kl_divergence_from_baseline=kl_div,
            wasserstein_distance=wasserstein,
            computed_at=datetime.utcnow(),
            sample_size=sample_size
        )

    def _estimate_intrinsic_dim(self, embeddings: np.ndarray) -> float:
        """Estimate intrinsic dimensionality using MLE"""
        # Maximum Likelihood Estimation method
        # Based on Levina & Bickel (2004)
        from sklearn.neighbors import NearestNeighbors

        k = 10
        nbrs = NearestNeighbors(n_neighbors=k+1, metric='euclidean')
        nbrs.fit(embeddings)
        distances, _ = nbrs.kneighbors(embeddings)

        # Use k nearest neighbors (exclude self)
        distances = distances[:, 1:]

        # MLE estimate
        m = np.mean(np.log(distances[:, -1] / distances[:, :-1]), axis=1)
        return 1 / np.mean(m)

    def _compute_kl_divergence(
        self,
        samples: np.ndarray,
        baseline_mean: float,
        baseline_std: float
    ) -> float:
        """Compute KL divergence between sample and baseline distributions"""
        # Approximate with Gaussian distributions
        sample_mean = np.mean(samples)
        sample_std = np.std(samples)

        # KL divergence for Gaussians
        kl = np.log(baseline_std / sample_std) + \
             (sample_std**2 + (sample_mean - baseline_mean)**2) / (2 * baseline_std**2) - 0.5

        return kl

    def detect_drift(
        self,
        current_metrics: EmbeddingQualityMetrics,
        baseline_metrics: EmbeddingQualityMetrics,
        sensitivity: float = 0.05
    ) -> dict:
        """
        Detect statistically significant drift.

        Args:
            current_metrics: Current quality metrics
            baseline_metrics: Historical baseline
            sensitivity: P-value threshold (default 0.05)

        Returns:
            Drift detection results
        """
        drift_detected = False
        drift_signals = []

        # 1. KL divergence threshold
        if current_metrics.kl_divergence_from_baseline > 0.1:
            drift_signals.append({
                "metric": "kl_divergence",
                "value": current_metrics.kl_divergence_from_baseline,
                "threshold": 0.1,
                "severity": "high"
            })
            drift_detected = True

        # 2. Similarity shift (t-test equivalent)
        similarity_shift = abs(
            current_metrics.mean_similarity - baseline_metrics.mean_similarity
        )
        if similarity_shift > 2 * baseline_metrics.std_similarity:
            drift_signals.append({
                "metric": "similarity_shift",
                "value": similarity_shift,
                "threshold": 2 * baseline_metrics.std_similarity,
                "severity": "medium"
            })
            drift_detected = True

        # 3. Cluster quality degradation
        silhouette_drop = baseline_metrics.silhouette_score - current_metrics.silhouette_score
        if silhouette_drop > 0.1:
            drift_signals.append({
                "metric": "cluster_quality",
                "value": silhouette_drop,
                "threshold": 0.1,
                "severity": "medium"
            })
            drift_detected = True

        # 4. Outlier increase
        outlier_increase = current_metrics.outlier_percentage - baseline_metrics.outlier_percentage
        if outlier_increase > 10.0:  # 10% increase
            drift_signals.append({
                "metric": "outliers",
                "value": outlier_increase,
                "threshold": 10.0,
                "severity": "low"
            })
            drift_detected = True

        return {
            "drift_detected": drift_detected,
            "drift_signals": drift_signals,
            "drift_score": len(drift_signals),
            "recommendation": self._generate_recommendation(drift_signals)
        }

    def _generate_recommendation(self, drift_signals: List[dict]) -> str:
        """Generate actionable recommendation"""
        if not drift_signals:
            return "No action needed. Embedding quality is stable."

        high_severity = [s for s in drift_signals if s["severity"] == "high"]
        if high_severity:
            return (
                "CRITICAL: Significant embedding drift detected. "
                "Recommended actions:\n"
                "1. Verify embedding model version hasn't changed\n"
                "2. Check for data quality issues in recent ingests\n"
                "3. Consider re-embedding corpus with current model\n"
                "4. Review preprocessing pipeline for bugs"
            )

        return (
            "WARNING: Moderate embedding drift detected. "
            "Monitor closely and investigate if trend continues."
        )
```

#### 2. Monitoring Service

**File**: `chromadb/monitoring/drift_monitor.py`

```python
import asyncio
from datetime import datetime, timedelta
from chromadb.config import Component, System
from chromadb.monitoring.embedding_quality import (
    EmbeddingQualityAnalyzer,
    EmbeddingQualityMetrics
)

class EmbeddingDriftMonitor(Component):
    """Continuously monitors embedding quality and detects drift"""

    def __init__(self, system: System):
        super().__init__(system)
        self._analyzer = EmbeddingQualityAnalyzer()
        self._baseline_metrics = {}  # collection_id -> baseline
        self._alert_client = system.instance(AlertClient)

    async def start_monitoring(
        self,
        interval_hours: int = 24,
        sample_size: int = 1000
    ):
        """Start continuous monitoring loop"""
        while True:
            try:
                await self._monitor_all_collections(sample_size)
            except Exception as e:
                logger.error(f"Drift monitoring error: {e}")

            # Wait for next interval
            await asyncio.sleep(interval_hours * 3600)

    async def _monitor_all_collections(self, sample_size: int):
        """Monitor all collections for drift"""
        collections = await self._get_active_collections()

        for collection in collections:
            try:
                await self._monitor_collection(collection.id, sample_size)
            except Exception as e:
                logger.error(
                    f"Error monitoring collection {collection.id}: {e}"
                )

    async def _monitor_collection(
        self,
        collection_id: str,
        sample_size: int
    ):
        """Monitor single collection"""

        # Sample embeddings
        embeddings = await self._sample_embeddings(collection_id, sample_size)
        if len(embeddings) < 100:
            logger.warning(
                f"Collection {collection_id} has <100 embeddings, skipping"
            )
            return

        # Get baseline (or create if first run)
        baseline = self._baseline_metrics.get(collection_id)

        # Compute current metrics
        current_metrics = self._analyzer.compute_metrics(
            embeddings,
            baseline_metrics=baseline
        )

        # Store metrics
        await self._store_metrics(collection_id, current_metrics)

        # Detect drift (if we have baseline)
        if baseline:
            drift_result = self._analyzer.detect_drift(
                current_metrics,
                baseline
            )

            if drift_result["drift_detected"]:
                await self._send_alert(collection_id, drift_result)

        else:
            # First run, establish baseline
            self._baseline_metrics[collection_id] = current_metrics
            logger.info(
                f"Established baseline for collection {collection_id}"
            )

    async def _send_alert(
        self,
        collection_id: str,
        drift_result: dict
    ):
        """Send drift alert"""
        severity = max(
            [s["severity"] for s in drift_result["drift_signals"]],
            default="low"
        )

        message = f"""
        🚨 Embedding Drift Detected

        Collection: {collection_id}
        Drift Score: {drift_result["drift_score"]}
        Severity: {severity.upper()}

        Signals:
        {self._format_signals(drift_result["drift_signals"])}

        Recommendation:
        {drift_result["recommendation"]}
        """

        await self._alert_client.send_alert(
            channel="embedding-quality",
            severity=severity,
            message=message
        )

    def _format_signals(self, signals: List[dict]) -> str:
        """Format drift signals for alert"""
        return "\n".join([
            f"- {s['metric']}: {s['value']:.3f} (threshold: {s['threshold']:.3f})"
            for s in signals
        ])
```

#### 3. Dashboard API

**File**: `chromadb/api/fastapi.py` (add endpoints)

```python
@app.get("/api/v1/monitoring/embedding-quality/{collection_id}")
async def get_embedding_quality(collection_id: str):
    """Get embedding quality metrics for collection"""
    monitor = system.instance(EmbeddingDriftMonitor)
    metrics = await monitor.get_latest_metrics(collection_id)

    return {
        "collection_id": collection_id,
        "metrics": metrics.dict(),
        "status": "healthy" if metrics.kl_divergence_from_baseline < 0.1 else "degraded"
    }

@app.get("/api/v1/monitoring/embedding-quality/{collection_id}/history")
async def get_quality_history(
    collection_id: str,
    days: int = 30
):
    """Get historical quality metrics"""
    monitor = system.instance(EmbeddingDriftMonitor)
    history = await monitor.get_metrics_history(
        collection_id,
        start_date=datetime.utcnow() - timedelta(days=days)
    )

    return {
        "collection_id": collection_id,
        "history": history,
        "timespan_days": days
    }
```

### Configuration

**File**: `chromadb/config.py`

```python
# Embedding Quality Monitoring
chroma_embedding_monitoring_enabled: bool = False
chroma_embedding_monitoring_interval_hours: int = 24
chroma_embedding_monitoring_sample_size: int = 1000
chroma_embedding_drift_sensitivity: float = 0.05
chroma_embedding_alert_channel: str = "slack"
```

## Example Usage

```python
import chromadb

# Enable monitoring
client = chromadb.Client(
    settings=chromadb.Settings(
        chroma_embedding_monitoring_enabled=True,
        chroma_embedding_monitoring_interval_hours=12
    )
)

# Create collection and add data
collection = client.create_collection("products")
collection.add(ids=[...], embeddings=[...], documents=[...])

# Monitoring runs automatically in background
# Alerts sent to Slack/PagerDuty if drift detected

# Manual quality check
quality_report = client.get_embedding_quality("products")
print(f"Mean similarity: {quality_report['mean_similarity']:.3f}")
print(f"Cluster quality: {quality_report['silhouette_score']:.3f}")
print(f"Outliers: {quality_report['outlier_percentage']:.1f}%")

# View historical trends
history = client.get_quality_history("products", days=90)
# Plot time series of metrics
```

## Implementation Plan

### Phase 1: Core Metrics (3 dev-days)
- Implement quality metrics computation
- Statistical tests for drift detection

### Phase 2: Monitoring Service (2 dev-days)
- Background monitoring loop
- Baseline management

### Phase 3: Alerting & Dashboard (2 dev-days)
- Alert integration (Slack, PagerDuty)
- API endpoints for dashboards

### Phase 4: Documentation (1 dev-day)
- Quality metrics guide
- Drift response runbook

## Backwards Compatibility

**Zero Breaking Changes**: Monitoring is opt-in, no impact on existing workflows.

## Performance Impact

- **Overhead**: ~1-2 minutes per 1M embeddings for metrics computation
- **Frequency**: Runs every 24 hours by default (configurable)
- **Impact**: Negligible (<0.01% of daily compute)

## Testing Strategy

- Unit tests for all quality metrics
- Synthetic drift injection tests
- Integration tests with real embedding models

## Success Criteria

1. **Detection**: Detect 95%+ of embedding model changes within 24 hours
2. **False Positives**: <5% false alarm rate
3. **Adoption**: 10+ enterprise customers enable monitoring in Q1
4. **Incidents**: Prevent 3+ quality incidents via early detection

## Effort Estimation

**Total: 7 dev-days**

| Phase | Dev-Days |
|-------|----------|
| Core Metrics | 3 |
| Monitoring | 2 |
| Alerting | 2 |
| Documentation | 1 |

## References

1. **Embedding Quality Metrics**: "Intrinsic Dimensionality Estimation" (Levina & Bickel, 2004)
2. **Drift Detection**: "Learning under Concept Drift" (Gama et al., 2014)
3. **Silhouette Score**: Rousseeuw (1987)
4. **KL Divergence**: Kullback-Leibler divergence for distribution comparison
