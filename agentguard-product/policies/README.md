# AgentGuard Policies

`personal_assistant_v1.json` is the published demo policy assigned to the Google ADK
personal assistant.

The policy is capability-based so MCP tool names can change without changing the policy
language. A new MCP integration should map its tools to these capability families:

| Domain | Read or prepare | Side effect | Destructive or financial |
| --- | --- | --- | --- |
| Filesystem | `filesystem.read`, `filesystem.inspect` | `filesystem.write` | `filesystem.delete` |
| Email and communication | `email.search`, `email.read`, `email.draft` | `email.send`, `communication.send` | N/A |
| Calendar | `calendar.read`, `calendar.draft` | `calendar.create`, `calendar.update` | `calendar.delete` |
| Scheduled jobs | N/A | `schedule.create`, `schedule.update` | `schedule.delete` |
| Google Drive | `drive.read` | `drive.write` | `drive.delete` |
| Web search | `web.search` | N/A | N/A |
| Payments | `payment.prepare` | N/A | `payment.execute`, `wallet.transfer` |
| Shell and system | `dynamic.shell` until normalized | `shell.network_request` | `system.privilege_escalate` |

Phase 3 evaluates tool and capability predicates. Resource predicates such as paths,
recipient domains, calendar targets, payment amounts, and command flags are retained in
the document but deferred until Phase 4 normalizers produce canonical action fields.

Changing a published policy requires a new semantic version. The policy loader computes
an effective SHA-256 hash so decisions and the dashboard can identify the exact content.
