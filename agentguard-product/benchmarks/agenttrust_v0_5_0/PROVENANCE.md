# AgentTrust Benchmark Provenance

- Upstream repository: https://github.com/chenglin1112/AgentTrust
- Upstream tag: `v0.5.0`
- Upstream commit: `aee262344315e29b4d0a9e23eb180af9b8193d6b`
- Imported files: six YAML scenario suites, `split.json`, and `LICENSE`
- Scenario count: 300
- License: Apache License 2.0
- Imported on: 2026-06-09

The corpus is unmodified. AgentGuard evaluates each case through its own live shell
interception path. Upstream AgentTrust benchmark compatibility rules are disabled by
default and must be requested explicitly when running the benchmark.

The expected `warn` and `review` verdicts are mapped to AgentGuard's
`require_approval` action because AgentGuard Tier 1 has no non-enforcing warning
verdict.
