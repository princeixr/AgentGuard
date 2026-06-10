from agentguard.server.repositories import local as local_repository
from agentguard.demo import generate_demo_fixtures


def test_local_repository_caches_unchanged_jsonl_and_reloads_appends(
    tmp_path,
    monkeypatch,
):
    generate_demo_fixtures(tmp_path)
    repository = local_repository.LocalDashboardRepository(tmp_path)
    original_load_jsonl = local_repository.load_jsonl
    calls = 0

    def counted_load_jsonl(path):
        nonlocal calls
        calls += 1
        return original_load_jsonl(path)

    monkeypatch.setattr(local_repository, "load_jsonl", counted_load_jsonl)

    initial = repository.traces()
    cached = repository.traces()
    trace_path = repository.namespace_root / "traces.jsonl"
    first_line = trace_path.read_text(encoding="utf-8").splitlines()[0]
    with trace_path.open("a", encoding="utf-8") as handle:
        handle.write(first_line + "\n")
    appended = repository.traces()

    assert cached == initial
    assert len(appended) == len(initial) + 1
    assert calls == 2
