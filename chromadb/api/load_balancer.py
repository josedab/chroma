"""
Load Balancer for Read Replicas

Implements client-side load balancing to distribute query requests
across multiple read replica nodes.
"""

import random
import logging
from typing import List, Optional, Literal
from chromadb.api.fastapi import FastAPI
from chromadb.config import System

logger = logging.getLogger(__name__)


class ReplicaLoadBalancer:
    """
    Client-side load balancer for distributing queries across read replicas.

    Supports round-robin and random load balancing strategies.
    Automatically fails over to healthy replicas when one is unavailable.
    """

    def __init__(
        self,
        replica_hosts: List[str],
        strategy: Literal["round_robin", "random"] = "round_robin",
    ):
        """
        Initialize the load balancer with a list of replica hosts.

        Args:
            replica_hosts: List of replica URLs (e.g., ["http://replica1:8000", "http://replica2:8000"])
            strategy: Load balancing strategy - "round_robin" or "random"
        """
        if not replica_hosts:
            raise ValueError("At least one replica host must be provided")

        self.replica_hosts = replica_hosts
        self.strategy = strategy
        self.current_index = 0
        self.healthy_replicas = set(replica_hosts)  # Track healthy replicas

        logger.info(
            f"Initialized ReplicaLoadBalancer with {len(replica_hosts)} replicas "
            f"using {strategy} strategy"
        )

    def get_next_replica(self) -> str:
        """
        Get the next replica to use based on the configured strategy.

        Returns:
            URL of the next replica to use
        """
        if not self.healthy_replicas:
            logger.warning("No healthy replicas available, resetting to all replicas")
            self.healthy_replicas = set(self.replica_hosts)

        healthy_list = list(self.healthy_replicas)

        if self.strategy == "round_robin":
            # Round-robin: cycle through replicas in order
            replica = healthy_list[self.current_index % len(healthy_list)]
            self.current_index = (self.current_index + 1) % len(healthy_list)
            return replica
        elif self.strategy == "random":
            # Random: select a random replica
            return random.choice(healthy_list)
        else:
            raise ValueError(f"Unknown load balancing strategy: {self.strategy}")

    def mark_replica_unhealthy(self, replica: str) -> None:
        """
        Mark a replica as unhealthy (temporarily remove from rotation).

        Args:
            replica: The replica URL to mark as unhealthy
        """
        if replica in self.healthy_replicas:
            self.healthy_replicas.discard(replica)
            logger.warning(f"Marked replica as unhealthy: {replica}")

    def mark_replica_healthy(self, replica: str) -> None:
        """
        Mark a replica as healthy (add back to rotation).

        Args:
            replica: The replica URL to mark as healthy
        """
        if replica not in self.healthy_replicas:
            self.healthy_replicas.add(replica)
            logger.info(f"Marked replica as healthy: {replica}")


def parse_replica_hosts(replica_hosts_str: Optional[str]) -> Optional[List[str]]:
    """
    Parse comma-separated replica hosts string into a list.

    Args:
        replica_hosts_str: Comma-separated list of replica hosts

    Returns:
        List of replica host URLs, or None if input is None/empty
    """
    if not replica_hosts_str:
        return None

    hosts = [host.strip() for host in replica_hosts_str.split(",") if host.strip()]
    return hosts if hosts else None
