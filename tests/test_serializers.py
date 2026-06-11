import json

import pytest

from agentguard.tracing.serializers import load_jsonl


def test_load_jsonl_ignores_an_incomplete_last_record(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text('{"event_id":"complete"}\n{"event_id":', encoding="utf-8")

    assert load_jsonl(path) == [{"event_id": "complete"}]


def test_load_jsonl_rejects_a_malformed_completed_record(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text('{"event_id":"complete"}\nnot-json\n', encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_jsonl(path)
