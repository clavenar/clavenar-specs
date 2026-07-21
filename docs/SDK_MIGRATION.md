# Governed execution migration

Clavenar Proxy 0.5.0 and Lite 0.9.0 require every effect-capable `POST /mcp`
request to select exactly one execution model. An unselected tool call returns
HTTP 426 with `error: "client_contract_required"` and `executable: false`
before authentication-side mutation, rate limiting, policy evaluation, HIL,
Ledger, receipt creation, or an upstream call.

Unselected MCP control methods remain compatible because they cannot execute a
tool: `initialize`, `initialized`, `notifications/*`, `ping`, and `tools/list`.

## Upgrade versions

| Component | Minimum version |
|---|---:|
| Proxy | 0.5.0 |
| Lite | 0.9.0 |
| Rust SDK | 0.3.0 |
| TypeScript SDK | 1.5.0 |
| Python SDK | 1.4.0 |
| Go SDK | 1.3.0 |
| Java SDK | 1.4.0 |
| .NET SDK | 1.5.0 |

Upgrade the client before the gateway. During a rolling deployment, upgraded
clients remain compatible with the preceding gateway because they already send
an explicit selector. After every caller is observed using an explicit
contract, upgrade Proxy or Lite. Roll back the gateway first if any maintained
caller still receives 426; do not restore silent execution in the client.

## Choose one execution model

Use side-effect-free decision when the host application owns execution. Create
a canonical UUID before the first network attempt and send:

```http
POST /mcp
x-clavenar-decision-contract: clavenar.decision/v1
x-clavenar-idempotency-id: cfcc8767-4c73-41cc-8ece-b855863924c4
```

The response is authorization only and is never executable by the gateway. A
multi-call model turn is one ordered `clavenar.atomic-tool-call-batch/v1`
decision. Persist the exact intent before invoking the registered executor,
invoke it at most once, persist the actual result and effect identity, and
deliver the terminal receipt from the durable outbox.

Use durable server execution only when the gateway intentionally owns the
upstream call. Create a canonical UUID before the first network attempt and
send:

```http
POST /mcp
x-clavenar-server-execution-contract: clavenar.server-execution/v1
x-clavenar-idempotency-id: cfcc8767-4c73-41cc-8ece-b855863924c4
```

The gateway commits intent before one upstream attempt and commits the exact
result before returning it. Repeating the same identity and payload reads the
retained result. A changed payload conflicts, and an in-flight record remains a
non-executable uncertain outcome.

## Language migration

| Language | Upgrade | Decision entry point |
|---|---|---|
| Rust | `clavenar-sdk` 0.3.0 | `ClavenarClient` prepared/governed execution APIs |
| TypeScript | `@clavenar/agent-sdk` 1.5.0 | `clavenarWrap` |
| Python | `clavenar-agent-sdk` 1.4.0 | `clavenar_wrap` |
| Go | `clavenar-go-sdk` 1.3.0 | `Inspect` / `InspectAll` |
| Java | `com.clavenar:agent-sdk` 1.4.0 | `ClavenarInspector` |
| .NET | `Clavenar.AgentSdk` 1.5.0 | `ClavenarInspector` |

The maintained clients allocate and retain the canonical ID, select only the
decision contract for inspection, submit siblings atomically, and keep the
registered executor outside the retrying decision transport. Do not add the
server-execution header to an inspection wrapper.

For a pending decision, persist the returned pending handle and poll only its
lookup route. Resume the retained prepared request after the exact signed
authorization becomes available. Do not resubmit the original decision or ask
the model to manufacture a replacement call.

## Failure handling

- Retry only an explicitly selected side-effect-free decision, retaining its
  original ID and byte-equivalent request.
- Never automatically retry a registered executor or gateway upstream call.
- Treat HTTP 426 `client_contract_required` as a configuration error. Upgrade
  or add the intended selector; never reinterpret it as allow.
- Treat partial, mixed, legacy, or unknown selectors as invalid requests.
- Reconcile an ambiguous executor outcome through its registered effect lookup;
  do not execute again.
- Redeliver retained receipts from the outbox without entering an execution
  path.

The machine-readable source of this matrix is
[`client-migration-v1.fixture.json`](../contracts/client-migration-v1.fixture.json),
validated by
[`client-migration-v1.schema.json`](../contracts/client-migration-v1.schema.json).
