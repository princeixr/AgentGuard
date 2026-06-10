"""Dashboard repositories."""

from agentguard.server.repositories.elastic import ElasticDashboardRepository
from agentguard.server.repositories.local import LocalDashboardRepository

__all__ = ["ElasticDashboardRepository", "LocalDashboardRepository"]
