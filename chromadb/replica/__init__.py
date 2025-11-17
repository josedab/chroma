"""
Read Replica Support for Chroma

This module provides read replica functionality for horizontally scaling
query throughput in Chroma.
"""

from chromadb.replica.replica_sync import ReplicaSyncService

__all__ = ["ReplicaSyncService"]
