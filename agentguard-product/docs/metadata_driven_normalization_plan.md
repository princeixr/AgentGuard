# Metadata-Driven Tool Normalization

## Goal

AgentGuard must not require one Python normalizer per tool. Ordinary structured tools
should become governable from their protocol metadata, JSON input schema, and a small
optional developer descriptor.

The runtime flow is:

```text
tool discovery
  -> security descriptor inference
  -> descriptor validation and confidence
  -> generic structured-action normalization
  -> deterministic policy
  -> optional higher tiers
```

Specialized parsers remain plugins for tools that embed another language inside one
argument, such as shell, SQL, browser scripts, or infrastructure plans.

## Registration Contract

For every discovered tool, AgentGuard creates a versioned security descriptor with:

- provider and domain;
- operation and canonical capabilities;
- side-effect, reversibility, external-impact, and privilege metadata;
- JSON input schema;
- argument roles for resources, destinations, content, and estimated value;
- metadata provenance and confidence;
- selected normalizer.

Metadata precedence is:

1. explicit developer descriptor;
2. verified protocol annotations;
3. JSON schema and description inference;
4. tool-name inference;
5. conservative unknown fallback.

Side-effecting tools with low-confidence metadata are not automatically trusted.

## Generic Runtime Normalization

`structured_v1` reads the descriptor and actual call arguments. It emits the canonical
action used by policy:

```json
{
  "domain": "communication",
  "operation": "send",
  "capabilities": ["email.send", "communication.send"],
  "resources": [],
  "destinations": [
    {
      "type": "email",
      "value": "finance@example.com",
      "external": true
    }
  ],
  "data_classes": ["email_address"],
  "side_effect": true,
  "reversible": false,
  "external_impact": true,
  "privilege_level": "standard",
  "estimated_value": null,
  "parser_confidence": 0.9
}
```

Argument roles are inferred from schema property names and descriptions. Developers can
later override incorrect mappings declaratively without implementing Python.

## Conservative Behavior

- Missing required arguments produce an invalid normalization.
- Unknown operations produce low confidence and `unknown_or_unsupported`.
- Side-effecting calls with insufficient metadata use policy fallback.
- Sensitive content detection records data-class indicators without storing additional
  copies of raw content.
- Specialized parsers override `structured_v1` only when deeper syntax understanding is
  necessary.

## Current Integration Scope

This implementation covers Google ADK and MCP tools already discovered by the runtime.
It creates generic descriptors for `workspace_*`, `gmail_local_*`, and future structured
MCP tools from the same registry. Shell continues to use `shell_v1`.

The next extension point is a published developer descriptor file for correcting or
enriching inferred metadata through Guard Admin.
