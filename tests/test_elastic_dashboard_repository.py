from agentguard.server.repositories.elastic import ElasticDashboardRepository
from agentguard.demo import generate_demo_fixtures
from agentguard.storage.elastic_config import ElasticConfig, ElasticIndexNames
from agentguard.storage.elastic_store import AgentGuardElasticStore
from agentguard.tracing.serializers import load_jsonl


class FakeElasticClient:
    def __init__(self, fixture_root):
        root = fixture_root / "v1" / "demo"
        indices = ElasticIndexNames()
        self.records = {
            indices.traces: load_jsonl(root / "traces.jsonl"),
            indices.trace_features: load_jsonl(root / "features.jsonl"),
            indices.guard_scores: load_jsonl(root / "scores.jsonl"),
            indices.guard_decisions: load_jsonl(root / "decisions.jsonl"),
            indices.live_events: load_jsonl(root / "live_events.jsonl"),
            indices.labels: load_jsonl(root / "labels.jsonl"),
            indices.scenarios: load_jsonl(root / "scenarios.jsonl"),
            indices.session_risk: [
                {
                    **load_jsonl(root / "traces.jsonl")[0],
                }
            ],
        }

    def get(self, path):
        return {"name": "fake-elastic"}

    def post(self, path, body):
        index = path.split("/", 1)[0]
        return {
            "hits": {
                "hits": [
                    {"_source": record} for record in self.records.get(index, [])
                ]
            }
        }


def test_elastic_dashboard_repository_reads_canonical_indices(tmp_path):
    fixture_root = tmp_path / "fixtures"
    generate_demo_fixtures(fixture_root)
    config = ElasticConfig(
        enabled=True,
        url="http://elastic.test",
        api_key="test",
        indices=ElasticIndexNames(),
    )
    store = AgentGuardElasticStore(
        config=config,
        client=FakeElasticClient(fixture_root),
    )
    repository = ElasticDashboardRepository(store)

    assert repository.is_ready()
    assert len(repository.traces()) == 13
    assert len(repository.decisions()) == 13
    assert len(repository.scenarios()) == 4
