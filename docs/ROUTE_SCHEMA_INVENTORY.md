# Route and schema release inventory

Release 1.234.0 publishes
[`clavenar.route-schema-release/v1`](../contracts/route-schema-release-v1.fixture.json).
The JSON fixture is authoritative; this page is the readable integration
guide.

## Route authority

The inventory contains 139 exact generated-enforced application routes.

| Service | Routes | Authority |
|---|---:|---|
| HIL | 29 | method, path template, capability, family, allowed caller IDs |
| Identity | 49 | method, path template, capability, family, allowed caller IDs |
| Ledger | 36 | method, path template, capability, family, allowed caller IDs |
| Policy Engine | 25 | method, path template, capability, family, allowed caller IDs |

Console SAML browser routes and Ledger's public aggregate verification route
are documented by the integration contracts but are not added to the 139-route
generated application total.

## Correct contract examples

### Policy

Policy evaluation is `POST /evaluate`, not `/eval`. The request is
`PolicyInput`; the response is `PolicyDecision`.

```json
{
  "tool_type": "database.write",
  "agent_history": {"last_tool": "database.read", "recent_sequence": []},
  "intent_score": 0.82,
  "agent_id": "agent-finance-01",
  "method": "tools/call",
  "correlation_id": "3ab2f91d-9e8d-4a8a-920f-67f587229e0d",
  "arguments": {"target_env": "prod"},
  "agent_kind": "mcp"
}
```

### HIL

A decision targets the pending UUID in the route:
`POST /decide/{id}`. The correlation ID is not the route identifier and an
authenticated deployment derives the principal from the verified credential,
not from caller-supplied attribution fields.

```json
{
  "decision": "approve",
  "reason": "Customer support ticket verified",
  "decided_via": "console"
}
```

### Ledger and audit

`GET /verify` always uses the `VerifyResult` shape and reports an invalid chain
in the response body; it does not use an alternate 409 body.

```json
{
  "valid": true,
  "entries_checked": 85200,
  "first_invalid_seq": null,
  "commitment": {
    "contract": "clavenar.verified-chain/v1",
    "head_hash": "a5d3e8ef0a5d65d47cd3e787f0760f2217daa04151401539dbd58a5d4439b926",
    "length": 85200,
    "tail_chain_version": 6
  },
  "anchors": [],
  "anchor_mismatch": null
}
```

Correlation replay is `GET /audit/correlation/{correlation_id}` on Ledger's
authenticated internal surface.

### Federated identity and SAML

SAML is a Console feature. Build Console with `--features saml`, set
`CLAVENAR_CONSOLE_AUTH=saml`, then configure:

```text
CLAVENAR_CONSOLE_SAML_ENTITY_ID=https://console.example.com
CLAVENAR_CONSOLE_SAML_ACS_URL=https://console.example.com/auth/saml/acs
CLAVENAR_CONSOLE_SAML_IDP_METADATA_URL=https://idp.example.com/metadata
CLAVENAR_CONSOLE_SAML_GROUP_ATTRIBUTES=Group,groups
CLAVENAR_CONSOLE_SAML_TENANT_ATTRIBUTE=org_id
CLAVENAR_CONSOLE_SAML_MFA_ATTRIBUTE=amr
CLAVENAR_CONSOLE_FEDERATED_TENANT_MAP=external-finance=finance
CLAVENAR_CONSOLE_FEDERATED_APPROVER_GROUPS=clavenar-approver
CLAVENAR_CONSOLE_FEDERATED_MFA_VALUES=otp,webauthn
```

The browser flow is `GET /auth/saml/login` followed by the IdP's signed form
POST to `/auth/saml/acs`.

### PostgreSQL Ledger

The supported chart path is one Ledger writer, verified TLS, and no SQLite
PVC. It requires every existing Secret name and key:

```yaml
services:
  ledger:
    replicas: 1
    postgres:
      enabled: true
      dsnSecretName: clavenar-ledger-pg
      dsnSecretKey: url
      tlsCaSecretName: clavenar-ledger-pg-ca
      tlsCaSecretKey: ca.crt
      rotationId: initial
persistence:
  ledger:
    enabled: false
```

### Rust SDK

`HilClient::decide` posts to `POST /decide/{id}` and returns the updated
`PendingRequest`. The caller supplies the pending UUID, typed decision,
optional reason/diff/assertion, a `HilDecideCredential`, and optional operator
surface. Non-2xx responses preserve HIL's exact status and body.

## Verification

```bash
python3 -m pytest tests/test_route_schema_release_contract.py
python3 ../clavenar-e2e/scripts/generate_route_schema_release.py --check
```
