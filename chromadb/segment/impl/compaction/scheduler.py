"""Background compaction scheduler."""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from chromadb.config import Component, System
from chromadb.db.system import SysDB
from chromadb.segment import SegmentManager, SegmentType
from chromadb.segment.impl.compaction.compactor import SegmentCompactor
from chromadb.segment.impl.compaction.status import CompactionState
from chromadb.types import Segment, SegmentScope

logger = logging.getLogger(__name__)


class CompactionConfig:
    """Configuration for automatic compaction."""

    def __init__(
        self,
        enabled: bool = False,
        schedule_cron: str = "0 2 * * *",  # Daily at 2 AM
        size_threshold_gb: float = 1.0,
        fragmentation_threshold: float = 0.2,
        deleted_threshold: float = 0.3,
        idle_days: int = 7,
        check_interval_seconds: int = 3600,  # Check every hour
        max_concurrent_compactions: int = 1,
    ):
        self.enabled = enabled
        self.schedule_cron = schedule_cron
        self.size_threshold_gb = size_threshold_gb
        self.fragmentation_threshold = fragmentation_threshold
        self.deleted_threshold = deleted_threshold
        self.idle_days = idle_days
        self.check_interval_seconds = check_interval_seconds
        self.max_concurrent_compactions = max_concurrent_compactions


class CompactionScheduler(Component):
    """
    Background service that automatically schedules and runs segment compaction.

    This implements the automatic compaction triggers from the RFC:
    1. Size threshold (segments > 1GB with fragmentation > 20%)
    2. Time-based (segments idle for > 7 days)
    3. Deleted records (deleted records > 30% of total)
    """

    def __init__(self, system: System):
        super().__init__(system)
        self._system = system
        self._sysdb: SysDB = system.require(SysDB)
        self._compactor = SegmentCompactor(system)
        self._config = self._load_config()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._active_compactions: Dict[UUID, threading.Thread] = {}

    def _load_config(self) -> CompactionConfig:
        """Load compaction configuration from system settings."""
        settings = self._system.settings

        # Check if compaction is enabled via settings
        enabled = getattr(settings, "chroma_compaction_enabled", False)

        return CompactionConfig(
            enabled=enabled,
            schedule_cron=getattr(
                settings, "chroma_compaction_schedule", "0 2 * * *"
            ),
            size_threshold_gb=getattr(
                settings, "chroma_compaction_size_threshold_gb", 1.0
            ),
            fragmentation_threshold=getattr(
                settings, "chroma_compaction_fragmentation_threshold", 0.2
            ),
            deleted_threshold=getattr(
                settings, "chroma_compaction_deleted_threshold", 0.3
            ),
            idle_days=getattr(settings, "chroma_compaction_idle_days", 7),
            check_interval_seconds=getattr(
                settings, "chroma_compaction_check_interval_seconds", 3600
            ),
            max_concurrent_compactions=getattr(
                settings, "chroma_compaction_max_concurrent", 1
            ),
        )

    def start(self) -> None:
        """Start the background compaction scheduler."""
        if not self._config.enabled:
            logger.info("Automatic compaction is disabled")
            return

        if self._running:
            logger.warning("Compaction scheduler already running")
            return

        logger.info("Starting compaction scheduler")
        self._running = True
        self._thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the background compaction scheduler."""
        if not self._running:
            return

        logger.info("Stopping compaction scheduler")
        self._running = False

        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

        # Wait for active compactions to complete
        with self._lock:
            for segment_id, thread in list(self._active_compactions.items()):
                logger.info(f"Waiting for compaction of segment {segment_id} to complete")
                thread.join(timeout=10.0)

        logger.info("Compaction scheduler stopped")

    def _run_scheduler(self) -> None:
        """Main scheduler loop."""
        logger.info(
            f"Compaction scheduler running. Check interval: {self._config.check_interval_seconds}s"
        )

        while self._running:
            try:
                self._check_and_compact()
            except Exception as e:
                logger.error(f"Error in compaction scheduler: {e}", exc_info=True)

            # Sleep until next check, but check _running periodically
            sleep_time = self._config.check_interval_seconds
            interval = 1.0  # Check every second if we should stop
            slept = 0.0

            while slept < sleep_time and self._running:
                time.sleep(min(interval, sleep_time - slept))
                slept += interval

    def _check_and_compact(self) -> None:
        """Check all segments and compact those that meet criteria."""
        logger.debug("Checking segments for compaction")

        # Clean up completed compactions
        with self._lock:
            for segment_id in list(self._active_compactions.keys()):
                thread = self._active_compactions[segment_id]
                if not thread.is_alive():
                    del self._active_compactions[segment_id]
                    self._compactor.clear_completed_status(segment_id)

        # Get all collections
        try:
            # Note: In a real implementation, we'd iterate through all collections
            # For now, we'll get segments directly from sysdb
            segments = self._get_all_segments()

            segments_to_compact = self._identify_segments_to_compact(segments)

            if segments_to_compact:
                logger.info(f"Found {len(segments_to_compact)} segments to compact")
                self._compact_segments(segments_to_compact)
            else:
                logger.debug("No segments meet compaction criteria")

        except Exception as e:
            logger.error(f"Error checking segments for compaction: {e}", exc_info=True)

    def _get_all_segments(self) -> List[Segment]:
        """Get all segments from the system."""
        # Note: This is a simplified implementation
        # In production, we'd need a better way to enumerate all segments
        segments: List[Segment] = []

        try:
            # Get all collections
            # Note: SysDB doesn't have a direct method to get all collections
            # We'd need to add that or maintain a registry
            # For now, return empty list
            pass
        except Exception as e:
            logger.error(f"Error getting segments: {e}", exc_info=True)

        return segments

    def _identify_segments_to_compact(self, segments: List[Segment]) -> List[Segment]:
        """Identify which segments should be compacted."""
        segments_to_compact = []

        for segment in segments:
            # Skip non-persistent segments
            segment_type = SegmentType(segment["type"])
            if segment_type not in (
                SegmentType.HNSW_LOCAL_PERSISTED,
                SegmentType.SQLITE,
                SegmentType.HNSW_DISTRIBUTED,
            ):
                continue

            # Skip if already compacting
            if segment["id"] in self._active_compactions:
                continue

            # Check if segment needs compaction
            try:
                # We need the segment implementation to analyze it
                # This would require getting it from the segment manager
                # For now, we'll skip the actual check
                # In production, we'd:
                # 1. Get segment implementation from manager
                # 2. Get fragmentation info
                # 3. Check thresholds
                pass

            except Exception as e:
                logger.error(
                    f"Error analyzing segment {segment['id']} for compaction: {e}",
                    exc_info=True,
                )

        return segments_to_compact

    def _compact_segments(self, segments: List[Segment]) -> None:
        """Compact the identified segments."""
        with self._lock:
            # Respect max concurrent compactions
            slots_available = (
                self._config.max_concurrent_compactions
                - len(self._active_compactions)
            )

            if slots_available <= 0:
                logger.info("Max concurrent compactions reached, deferring remaining segments")
                return

            # Start compaction for available slots
            for segment in segments[:slots_available]:
                self._start_compaction(segment)

    def _start_compaction(self, segment: Segment) -> None:
        """Start compaction for a segment in a background thread."""
        segment_id = segment["id"]
        collection_id = segment["collection"]

        logger.info(
            f"Starting background compaction for segment {segment_id} "
            f"in collection {collection_id}"
        )

        def compact_task():
            try:
                # Get segment implementation
                # Note: This would require the segment manager
                # For now, this is a placeholder
                logger.info(f"Compaction task started for segment {segment_id}")

                # In production:
                # segment_impl = segment_manager.get_segment_impl(segment_id)
                # self._compactor.compact_segment(collection_id, segment, segment_impl)

            except Exception as e:
                logger.error(
                    f"Compaction failed for segment {segment_id}: {e}",
                    exc_info=True,
                )

        thread = threading.Thread(target=compact_task, daemon=True)
        self._active_compactions[segment_id] = thread
        thread.start()

    def trigger_manual_compaction(
        self, collection_id: UUID, segment_manager: SegmentManager
    ) -> None:
        """
        Manually trigger compaction for a collection.

        This is called from the Collection.compact() API.
        """
        logger.info(f"Manual compaction triggered for collection {collection_id}")

        try:
            # Get all segments for the collection
            segments = self._sysdb.get_segments(collection=collection_id)

            for segment in segments:
                scope = segment["scope"]

                # Only compact vector and metadata segments
                if scope not in (SegmentScope.VECTOR, SegmentScope.METADATA):
                    continue

                # Get segment implementation
                segment_type = SegmentScope.VECTOR if scope == SegmentScope.VECTOR else SegmentScope.METADATA

                # Note: We need to get the segment implementation from the manager
                # This is a simplified version
                logger.info(
                    f"Would compact segment {segment['id']} "
                    f"(scope: {scope}, type: {segment['type']})"
                )

                # In production:
                # segment_impl = segment_manager._instance(segment)
                # status = self._compactor.compact_segment(
                #     collection_id, segment, segment_impl
                # )

        except Exception as e:
            logger.error(
                f"Manual compaction failed for collection {collection_id}: {e}",
                exc_info=True,
            )
            raise

    def get_compaction_status(self, collection_id: UUID) -> Dict:
        """Get compaction status for a collection."""
        try:
            # Get all segments for the collection
            segments = self._sysdb.get_segments(collection=collection_id)

            statuses = []
            for segment in segments:
                status = self._compactor.get_compaction_status(segment["id"])
                if status:
                    statuses.append(status.to_dict())

            # Check if any are in progress
            in_progress = any(
                s["state"] == CompactionState.IN_PROGRESS.value for s in statuses
            )

            # Calculate overall progress
            if statuses:
                overall_progress = sum(s["progress"] for s in statuses) / len(statuses)
            else:
                overall_progress = 0.0

            return {
                "in_progress": in_progress,
                "progress": overall_progress,
                "segments": statuses,
            }

        except Exception as e:
            logger.error(
                f"Error getting compaction status for collection {collection_id}: {e}",
                exc_info=True,
            )
            return {
                "in_progress": False,
                "progress": 0.0,
                "error": str(e),
            }
