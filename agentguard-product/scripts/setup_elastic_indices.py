"""Create or update AgentGuard Elasticsearch indices."""

from __future__ import annotations

from _bootstrap import bootstrap

bootstrap()

from agentguard.storage import AgentGuardElasticStore, load_elastic_config


def main() -> None:
    config = load_elastic_config()
    config.require_configured()
    store = AgentGuardElasticStore(config=config)
    info = store.ping()
    indices = store.setup_indices()
    cluster_name = info.get("cluster_name", "unknown")
    print(f"Connected to Elastic cluster: {cluster_name}")
    print("Created or updated indices:")
    for index in indices:
        print(f"- {index}")


if __name__ == "__main__":
    main()
