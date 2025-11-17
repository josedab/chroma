"""Unit tests for segment compaction."""

import tempfile
import shutil
from datetime import datetime, timedelta
from uuid import uuid4
import pytest

from chromadb.config import Settings, System
from chromadb.segment.impl.compaction.compactor import (
    SegmentCompactor,
    FragmentationInfo,
)
from chromadb.segment.impl.compaction.status import CompactionState, CompactionStatus
from chromadb.segment.impl.compaction.scheduler import CompactionConfig


class TestFragmentationInfo:
    """Test FragmentationInfo class."""

    def test_fragmentation_info_basic(self):
        """Test basic fragmentation info metrics."""
        info = FragmentationInfo(
            total_records=100,
            deleted_records=30,
            size_bytes=1024 * 1024 * 1024,  # 1GB
        )

        assert info.live_records == 70
        assert info.deleted_ratio == 0.3
        assert info.fragmentation_ratio == 0.3
        assert info.size_gb == 1.0

    def test_fragmentation_info_empty(self):
        """Test fragmentation info with no records."""
        info = FragmentationInfo(
            total_records=0,
            deleted_records=0,
            size_bytes=0,
        )

        assert info.live_records == 0
        assert info.deleted_ratio == 0.0
        assert info.fragmentation_ratio == 0.0
        assert info.size_gb == 0.0

    def test_should_compact_size_threshold(self):
        """Test compaction trigger based on size threshold."""
        info = FragmentationInfo(
            total_records=1000000,
            deleted_records=250000,  # 25% deleted
            size_bytes=2 * 1024 * 1024 * 1024,  # 2GB
        )

        # Should compact: size > 1GB and fragmentation > 20%
        assert info.should_compact(
            size_threshold_gb=1.0,
            fragmentation_threshold=0.2,
        )

        # Should not compact: fragmentation threshold too high
        assert not info.should_compact(
            size_threshold_gb=1.0,
            fragmentation_threshold=0.3,
        )

        # Should not compact: size threshold too high
        assert not info.should_compact(
            size_threshold_gb=3.0,
            fragmentation_threshold=0.2,
        )

    def test_should_compact_deleted_threshold(self):
        """Test compaction trigger based on deleted records."""
        info = FragmentationInfo(
            total_records=1000,
            deleted_records=400,  # 40% deleted
            size_bytes=100 * 1024 * 1024,  # 100MB (below size threshold)
        )

        # Should compact: deleted ratio > 30%
        assert info.should_compact(deleted_threshold=0.3)

        # Should not compact: deleted threshold too high
        assert not info.should_compact(deleted_threshold=0.5)

    def test_should_compact_time_based(self):
        """Test compaction trigger based on idle time."""
        old_time = datetime.now() - timedelta(days=10)
        info = FragmentationInfo(
            total_records=1000,
            deleted_records=150,  # 15% deleted
            size_bytes=500 * 1024 * 1024,  # 500MB
            last_modified=old_time,
        )

        # Should compact: idle > 7 days and some fragmentation
        assert info.should_compact(idle_days=7)

        # Should not compact: idle threshold too high
        assert not info.should_compact(idle_days=15)

        # Recent modification should not trigger
        recent_info = FragmentationInfo(
            total_records=1000,
            deleted_records=150,
            size_bytes=500 * 1024 * 1024,
            last_modified=datetime.now(),
        )
        assert not recent_info.should_compact(idle_days=7)


class TestCompactionStatus:
    """Test CompactionStatus class."""

    def test_status_to_dict(self):
        """Test status serialization to dict."""
        collection_id = uuid4()
        segment_id = uuid4()

        status = CompactionStatus(
            collection_id=collection_id,
            segment_id=segment_id,
            state=CompactionState.IN_PROGRESS,
            progress=0.5,
            started_at=datetime(2025, 11, 17, 10, 0, 0),
            original_size_bytes=1000000,
            compacted_size_bytes=700000,
        )

        result = status.to_dict()

        assert result["collection_id"] == str(collection_id)
        assert result["segment_id"] == str(segment_id)
        assert result["state"] == "in_progress"
        assert result["in_progress"] is True
        assert result["progress"] == 0.5
        assert result["space_saved_bytes"] == 300000
        assert result["space_saved_percent"] == 30.0

    def test_status_no_size_info(self):
        """Test status without size information."""
        status = CompactionStatus(
            collection_id=uuid4(),
            segment_id=uuid4(),
            state=CompactionState.PENDING,
            progress=0.0,
        )

        result = status.to_dict()

        assert result["space_saved_bytes"] is None
        assert result["space_saved_percent"] is None


class TestCompactionConfig:
    """Test CompactionConfig class."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = CompactionConfig()

        assert config.enabled is False
        assert config.schedule_cron == "0 2 * * *"
        assert config.size_threshold_gb == 1.0
        assert config.fragmentation_threshold == 0.2
        assert config.deleted_threshold == 0.3
        assert config.idle_days == 7
        assert config.check_interval_seconds == 3600
        assert config.max_concurrent_compactions == 1

    def test_config_custom_values(self):
        """Test custom configuration values."""
        config = CompactionConfig(
            enabled=True,
            size_threshold_gb=2.0,
            fragmentation_threshold=0.25,
            deleted_threshold=0.4,
            idle_days=14,
            check_interval_seconds=7200,
            max_concurrent_compactions=2,
        )

        assert config.enabled is True
        assert config.size_threshold_gb == 2.0
        assert config.fragmentation_threshold == 0.25
        assert config.deleted_threshold == 0.4
        assert config.idle_days == 14
        assert config.check_interval_seconds == 7200
        assert config.max_concurrent_compactions == 2


@pytest.fixture
def temp_persist_dir():
    """Create a temporary persist directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_system(temp_persist_dir):
    """Create a test system with compaction enabled."""
    settings = Settings(
        allow_reset=True,
        is_persistent=True,
        persist_directory=temp_persist_dir,
        chroma_compaction_enabled=True,
        chroma_compaction_size_threshold_gb=1.0,
        chroma_compaction_fragmentation_threshold=0.2,
        chroma_compaction_deleted_threshold=0.3,
    )
    return System(settings)


class TestSegmentCompactor:
    """Test SegmentCompactor class."""

    def test_compactor_creation(self, test_system):
        """Test creating a compactor instance."""
        compactor = SegmentCompactor(test_system)
        assert compactor is not None
        assert compactor._persist_directory == test_system.settings.persist_directory

    def test_get_compaction_status_not_found(self, test_system):
        """Test getting status for non-existent compaction."""
        compactor = SegmentCompactor(test_system)
        segment_id = uuid4()

        status = compactor.get_compaction_status(segment_id)
        assert status is None

    def test_clear_completed_status(self, test_system):
        """Test clearing completed compaction status."""
        compactor = SegmentCompactor(test_system)
        segment_id = uuid4()

        # Add a completed status
        status = CompactionStatus(
            collection_id=uuid4(),
            segment_id=segment_id,
            state=CompactionState.COMPLETED,
            progress=1.0,
        )
        compactor._compaction_statuses[segment_id] = status

        # Clear it
        compactor.clear_completed_status(segment_id)

        # Verify it's gone
        assert compactor.get_compaction_status(segment_id) is None

    def test_clear_in_progress_status_doesnt_clear(self, test_system):
        """Test that clearing doesn't remove in-progress status."""
        compactor = SegmentCompactor(test_system)
        segment_id = uuid4()

        # Add an in-progress status
        status = CompactionStatus(
            collection_id=uuid4(),
            segment_id=segment_id,
            state=CompactionState.IN_PROGRESS,
            progress=0.5,
        )
        compactor._compaction_statuses[segment_id] = status

        # Try to clear it
        compactor.clear_completed_status(segment_id)

        # Verify it's still there
        assert compactor.get_compaction_status(segment_id) is not None
