"""Dashboard repositories."""

from agentguard.api.repositories.elastic import ElasticDashboardRepository
from agentguard.api.repositories.local import LocalDashboardRepository

__all__ = ["ElasticDashboardRepository", "LocalDashboardRepository"]
