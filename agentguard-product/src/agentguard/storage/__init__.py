"""Elastic storage integration for AgentGuard."""

from agentguard.storage.elastic_config import ElasticConfig, load_elastic_config
from agentguard.storage.elastic_store import AgentGuardElasticStore

__all__ = ["AgentGuardElasticStore", "ElasticConfig", "load_elastic_config"]
