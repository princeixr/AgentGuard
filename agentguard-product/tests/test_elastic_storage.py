from agentguard.storage.elastic_config import ElasticConfig, ElasticIndexNames
from agentguard.storage.elastic_store import AgentGuardElasticStore
from agentguard.tracing.schema_v1 import (
    AgentGuardTraceV1,
    ExecutionStateV1,
    IntentContractV1,
    RetrievalTextV1,
    ToolCallV1,
    TraceSourceV1,
    TrajectoryV1,
)


class FakeElasticClient:
    def __init__(self):
        self.existing = set()
        self.put_calls = []
        self.bulk_lines = []
        self.get_response = {}
        self.post_response = {"hits": {"hits": []}}
        self.search_body = None
        self.search_path = None

    def head(self, path):
        return path in self.existing

    def get(self, path):
        return self.get_response

    def put(self, path, body):
        self.put_calls.append((path, body))
        return {"acknowledged": True}

    def post_ndjson(self, path, lines):
        self.bulk_lines = lines
        return {"items": [{"index": {"status": 201}} for _ in range(len(lines) // 2)]}

    def post(self, path, body):
        self.search_path = path
        self.search_body = body
        return self.post_response


def test_setup_indices_creates_missing_indices():
    client = FakeElasticClient()
    store = AgentGuardElasticStore(config=_config(), client=client)

    indices = store.setup_indices()

    assert "agentguard-traces-v1" in indices
    assert any(path == "agentguard-traces-v1" for path, _ in client.put_calls)


def test_bulk_index_traces_uses_trace_id_as_document_id():
    client = FakeElasticClient()
    store = AgentGuardElasticStore(config=_config(), client=client)
    trace = _trace("trace_001")

    result = store.bulk_index_traces([trace])

    assert result.indexed == 1
    assert client.bulk_lines[0] == {
        "index": {"_index": "agentguard-traces-v1", "_id": "trace_001"}
    }
    assert client.bulk_lines[1]["schema_version"] == "agentguard.trace.v1"
    assert client.bulk_lines[1]["@timestamp"]


def test_search_similar_traces_filters_by_domain_and_tool_category():
    client = FakeElasticClient()
    store = AgentGuardElasticStore(config=_config(), client=client)

    store.search_similar_traces(_trace("trace_001"))

    filters = client.search_body["query"]["bool"]["filter"]
    assert {"term": {"intent.domain": "email"}} in filters
    assert {"term": {"proposed_tool_call.tool_category": "email"}} in filters
    assert {"term": {"source.mode": "historical"}} in filters


def test_get_latest_trace_reads_newest_trace_from_elastic():
    client = FakeElasticClient()
    trace = _trace("trace_latest")
    client.post_response = {
        "hits": {"hits": [{"_source": trace.model_dump(mode="json", by_alias=True)}]}
    }
    store = AgentGuardElasticStore(config=_config(), client=client)

    latest = store.get_latest_trace()

    assert latest is not None
    assert latest.trace_id == "trace_latest"
    assert client.search_path == "agentguard-traces-v1/_search"
    assert client.search_body["sort"] == [{"@timestamp": {"order": "desc"}}]


def _config() -> ElasticConfig:
    return ElasticConfig(
        enabled=True,
        url="http://localhost:9200",
        api_key="test",
        indices=ElasticIndexNames(),
    )


def _trace(trace_id: str) -> AgentGuardTraceV1:
    return AgentGuardTraceV1(
        trace_id=trace_id,
        session_id="session_001",
        step_index=1,
        source=TraceSourceV1(
            mode="historical",
            agent_framework="openclaw",
            source_type="live_openclaw",
            agent_id="openclaw_agentguard_productivity",
            scenario_id="scenario_001",
        ),
        intent=IntentContractV1(
            raw_user_request="Draft a reply but do not send.",
            normalized_intent="Draft a reply but do not send.",
            domain="email",
            task_category="email_summary_and_reply",
            available_tools=["gmail_search", "gmail_read", "gmail_draft", "gmail_send"],
            task_relevant_tools=["gmail_search", "gmail_read", "gmail_draft"],
            intent_forbidden_tools=["gmail_send"],
        ),
        proposed_tool_call=ToolCallV1(
            call_id="call_001",
            tool_name="gmail_send",
            tool_category="email",
            risk_level="external_write",
            side_effect_type="external_message_send",
            arguments={"draft_id": "draft_001"},
            argument_summary="draft_id=draft_001",
        ),
        trajectory=TrajectoryV1(prior_tool_names=["gmail_search", "gmail_read"]),
        retrieval_text=RetrievalTextV1(
            summary="Draft a reply but do not send. Proposed gmail_send.",
            intent_text="Draft a reply but do not send.",
            trajectory_text="gmail_search -> gmail_read -> gmail_send",
            argument_text="draft_id=draft_001",
        ),
        execution=ExecutionStateV1(status="proposed"),
    )
