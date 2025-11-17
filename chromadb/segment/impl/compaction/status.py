"""Compaction status tracking."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID


class CompactionState(Enum):
    """State of a compaction operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CompactionStatus:
    """Tracks the status of a compaction operation."""

    collection_id: UUID
    segment_id: UUID
    state: CompactionState
    progress: float  # 0.0 to 1.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    error: Optional[str] = None
    original_size_bytes: Optional[int] = None
    compacted_size_bytes: Optional[int] = None
    records_processed: int = 0
    records_total: int = 0

    def to_dict(self) -> dict:
        """Convert status to dictionary for API responses."""
        return {
            "collection_id": str(self.collection_id),
            "segment_id": str(self.segment_id),
            "state": self.state.value,
            "in_progress": self.state == CompactionState.IN_PROGRESS,
            "progress": self.progress,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimated_completion": (
                self.estimated_completion.isoformat()
                if self.estimated_completion
                else None
            ),
            "error": self.error,
            "space_saved_bytes": (
                self.original_size_bytes - self.compacted_size_bytes
                if self.original_size_bytes and self.compacted_size_bytes
                else None
            ),
            "space_saved_percent": (
                (
                    (self.original_size_bytes - self.compacted_size_bytes)
                    / self.original_size_bytes
                    * 100
                )
                if self.original_size_bytes
                and self.compacted_size_bytes
                and self.original_size_bytes > 0
                else None
            ),
        }
