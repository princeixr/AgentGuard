# AgentGuardFirewallV2 Package Boundary

All new firewall logic belongs under this package.

```text
firewall_v2/
    engine.py
    models.py
    policy/
    tools/
        normalizers/       # Phase 4
    intent/                # Phase 5
    tiers/
        tier_1/            # Phase 6
        tier_2/
        tier_3/
    routing/
    enforcement/
    persistence/
```

Code outside this package should be limited to integration boundaries:

- `runtime/`: framework adapters that submit intercepted tool calls to V2.
- `api/`: transport and presentation models for dashboard clients.
- `apps/agentguard_dashboard/`: product UI.
- `storage/`: reusable persistence clients.
- `control_plane/`: agent, deployment, and policy assignment metadata.

The existing `governance/*_v1.py` modules remain isolated legacy enforcement. V2 may
observe the same canonical trace during migration, but V2 modules must not import V1
scoring or decision-policy implementations.

When V2 becomes authoritative, the runtime adapter should depend on one firewall
interface. Removing V1 should then require deleting the legacy implementation and
changing the composition root, rather than rewriting V2 modules.
