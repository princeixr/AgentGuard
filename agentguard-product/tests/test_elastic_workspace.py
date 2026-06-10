import json
from pathlib import Path

from agentguard.storage.elastic_config import ElasticIndexNames
from agentguard.storage.index_templates import all_index_mappings


ELASTIC_WORKSPACE = Path("data/elastic")


def test_elastic_mapping_snapshots_match_code_templates():
    for index_name, expected_mapping in all_index_mappings(ElasticIndexNames()).items():
        path = ELASTIC_WORKSPACE / "mappings" / f"{index_name}.json"
        assert path.exists(), f"Missing mapping snapshot: {path}"
        assert json.loads(path.read_text(encoding="utf-8")) == expected_mapping


def test_elastic_query_files_are_valid_json_objects():
    query_dir = ELASTIC_WORKSPACE / "queries"
    for path in query_dir.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
        assert "query" in payload


def test_elastic_notebooks_are_valid_json_notebooks():
    notebook_dir = ELASTIC_WORKSPACE / "notebooks"
    for path in notebook_dir.glob("*.ipynb"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["nbformat"] == 4
        assert isinstance(payload["cells"], list)
