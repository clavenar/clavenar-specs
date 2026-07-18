# Clavenar — architecture

System-wide architecture diagrams. The wire contracts behind every box and
arrow live in [`../TECH_SPEC.md`](../TECH_SPEC.md); this file is the
visual index. Five views, top-down by abstraction:

1. [System Context](#1-system-context) — who talks to Clavenar, and what
   external services Clavenar depends on.
2. [Container View](#2-container-view) — the four-layer hot path plus
   the orchestrators around it.
3. [Deployment Topology](#3-deployment-topology) — how `prod` and `dev`
   share a host-side Caddy.
4. [Demo-Prefix End-to-End](#4-demo-prefix-end-to-end) — visitor →
   token → cookie → correlation ID, the per-visitor isolation flow.
5. [Trust Chain](#5-trust-chain) — every credential Clavenar issues,
   from CA root down to the per-action ed25519 signature.

Per-repo behavior diagrams live in each service's own `docs/SEQUENCES.md`.

## 1. System Context

```mermaid
flowchart LR
  Visitor[Visitor — browser]
  Operator[Operator — console, clavenarctl]
  Agent[AI Agent — any LLM]
  Upstream[Upstream MCP target]

  subgraph Clavenar[Clavenar]
    direction TB
    Edge[Caddy + console + website + demo-mint]
    Core[proxy + brain + policy + ledger + HIL + identity]
  end

  NATS[NATS — message bus]
  Vault[Vault — secrets + transit ed25519]
  Anthropic[Anthropic API]
  Voyage[Voyage AI — embeddings]
  Turnstile[Cloudflare Turnstile]
  R2[Cloudflare R2 — backups]
  LE[Let's Encrypt — ACME]

  Visitor -->|HTTPS| Edge
  Operator -->|HTTPS + OIDC| Edge
  Agent -->|mTLS MCP| Core
  Core -->|mTLS MCP| Upstream

  Edge --- Core

  Core -->|publish + subscribe| NATS
  Core -->|fetch credentials| Vault
  Core -->|/sign HTTP, transit ed25519| Vault
  Core -->|prompt evaluation| Anthropic
  Core -->|persona embeddings| Voyage
  Edge -->|widget verify| Turnstile
  Edge -->|weekly ledger snapshot| R2
  Edge -->|ACME HTTP-01| LE
```

## 2. Container View

The four-layer hot path is serial: the proxy awaits Brain `/inspect`,
derives `intent_score` from that verdict, then calls Policy `/evaluate`
(`proxy → brain → policy`). The ledger row is written downstream over
the NATS forensic bus once the verdict resolves. Everything else is an
orchestrator hanging off the side: HIL gates Yellow-tier traffic,
identity roots the trust chain, sandbox annotates HIL pendings,
deep-review samples forensic rows.

```mermaid
flowchart TD
  Agent[AI Agent]
  Upstream[Upstream MCP target]
  Browser[Browser — visitor or operator]

  subgraph L1[Layer 1 — Data Plane]
    Proxy[clavenar-proxy 8443]
  end

  subgraph L2L3[Layer 2 plus Layer 3 — Semantic plus Governance]
    Brain[clavenar-brain 8081]
    Policy[clavenar-policy-engine 8082]
  end

  subgraph L4[Layer 4 — Forensic Store]
    Ledger[clavenar-ledger 8083]
  end

  Bus[NATS / JetStream — forensic subjects plus shared durable KV]

  subgraph Orch[Orchestrators]
    HIL[clavenar-hil 8084]
    Identity[clavenar-identity 8086]
    Sandbox[clavenar-sandbox — path-dep into proxy]
    DeepReview[clavenar-deep-review]
    DemoMint[clavenar-demo-mint]
    Simulator[clavenar-simulator]
    UpstreamStub[clavenar-upstream-stub — demo target]
  end

  subgraph Edge[Edge plus UI]
    Caddy[Caddy — TLS terminator]
    Console[clavenar-console 8085]
    Website[clavenar-website — static]
  end

  Agent -->|mTLS MCP| Proxy
  Proxy -->|mTLS POST /inspect| Brain
  Brain -->|intent_score verdict| Proxy
  Proxy -->|mTLS POST /evaluate — carries intent_score| Policy
  Policy -->|mTLS POST /explain-pattern — exact policy-engine SVID| Brain
  Console -->|mTLS narrate-decision + model-snapshot — exact console SVID| Brain
  Proxy -->|HTTP POST /pending — Yellow tier| HIL
  Proxy -->|HTTP /sign + /actor-token| Identity
  Proxy -->|annotate blast-radius| Sandbox
  Proxy -->|mTLS MCP forward| Upstream
  Proxy -->|mTLS MCP forward — demo path| UpstreamStub
  Proxy -->|publish clavenar.forensic| Bus

  Bus -->|consume + persist| Ledger
  Ledger -->|verify-jws via JWKS| Identity
  Identity -->|publish clavenar.forensic.identity| Bus
  Identity -->|atomic actor-token replay reservation| Bus

  HIL -->|annotated by| Sandbox
  DeepReview -->|consume sample| Bus
  DeepReview -->|publish review verdict| Bus

  Simulator -->|persona mTLS traffic| Proxy
  Simulator -->|HTTP /svid + /grant| Identity
  Simulator -->|HTTP auto-decide pendings| HIL

  Browser -->|HTTPS| Caddy
  Caddy -->|reverse proxy| Console
  Caddy -->|reverse proxy| Website
  Caddy -->|reverse proxy /verify only| Ledger
  Caddy -->|reverse proxy /mint| DemoMint

  Console -->|HTTP /audit + /verify| Ledger
  Console -->|HTTP /pending + /decide| HIL
  Console -->|HTTP policy CRUD| Policy
  Console -->|HTTP agents + grants| Identity
  Console -->|HTTP /sim/running| Simulator
  Console -->|exchange demo token| DemoMint

  DemoMint -->|publish demo-mint events| Bus
```

## 3. Deployment Topology

Single VPS runs both `prod` (`clavenar-prod` compose project, standard
ports) and `dev` (`clavenar-dev`, +10000 offset). The production website/Caddy
service is the only browser edge; dev has no website vhost. The reserved
DEV/operator hostname `console.clavenar.com` is a static 404 during the
bootstrap phase. The native production `:8085` and dev `:18085` operator
listeners are host-loopback-only and require mTLS through an SSH tunnel.

```mermaid
flowchart LR
  Internet((Internet))
  Browser[Visitor browser]
  Operator[Operator browser]
  Agent[AI agent]

  subgraph Host[Demo VPS — Europe/Berlin]
    direction TB
    HostCaddy[prod website/Caddy — 80 + 443 — auto-LE]

    subgraph Prod[clavenar-prod project — standard ports]
      direction TB
      P_proxy[proxy 8443]
      P_brain[brain 8081]
      P_policy[policy 8082]
      P_ledger[ledger 8083]
      P_hil[hil 8084]
      P_console[console — loopback 8085 mTLS + internal 9085 demo]
      P_identity[identity 8086]
      P_demomint[demo-mint]
      P_sim[simulator]
      P_stub[upstream-stub]
      P_dr[deep-review]
      P_nats[NATS 4222]
      P_vault[Vault 8200]
      P_vols[(ledger-data + hil-data + identity-data + secrets + caddy-data)]
    end

    subgraph Dev[clavenar-dev project — plus10000 ports]
      direction TB
      D_proxy[proxy 19443]
      D_brain[brain 18081]
      D_policy[policy 18082]
      D_ledger[ledger 18083]
      D_hil[hil 18084]
      D_console[console — loopback 18085 mTLS + internal 9085 demo]
      D_identity[identity 18086]
      D_sim[simulator]
      D_stub[upstream-stub]
      D_dr[deep-review]
      D_nats[NATS 14222]
      D_vault[Vault 18200]
      D_vols[(ledger-data + hil-data + identity-data + secrets + caddy-data)]
    end
  end

  Internet --> Browser
  Internet --> Agent

  Browser -->|clavenar.com| HostCaddy
  Browser -->|demo.clavenar.com| HostCaddy
  Browser -->|console.clavenar.com — static 404| HostCaddy
  Operator -->|SSH tunnel + native mTLS — loopback 8085| P_console
  Operator -->|SSH tunnel + native mTLS — loopback 18085| D_console
  Agent -->|mTLS — 8443| P_proxy

  HostCaddy -->|demo.clavenar.com — curated 9085| P_console
  HostCaddy -->|demo.clavenar.com /verify only| P_ledger
  HostCaddy -->|demo.clavenar.com /mint| P_demomint
```

## 4. Demo-Prefix End-to-End

How a visitor session gets its own correlation-ID namespace. The 8-hex
prefix is minted at Turnstile-time, ridden as a cookie, spliced into
every UUIDv4 the proxy emits, and used by HIL + ledger to gate reads
to the visitor's own traffic.

```mermaid
sequenceDiagram
  participant Visitor
  participant TS as Cloudflare Turnstile
  participant Mint as demo-mint
  participant Console as clavenar-console
  participant Proxy as clavenar-proxy
  participant HIL as clavenar-hil
  participant Ledger as clavenar-ledger
  participant Sim as clavenar-simulator

  Visitor->>TS: solve widget
  TS-->>Visitor: cf-turnstile-response token
  Visitor->>Mint: GET /mint?cf-turnstile-response=...
  Mint->>TS: server-side verify
  TS-->>Mint: OK
  Mint-->>Visitor: 303 demo.clavenar.com/#token=<HS256 JWT — prefix, sub, exp, iat>
  Note over Visitor,Console: Fragment never sent to server. Console JS reads it client-side.
  Visitor->>Console: POST /api/demo-session/exchange — body has JWT
  Console-->>Visitor: Set-Cookie clavenar_demo_session — HttpOnly Secure SameSite=Lax
  Visitor->>Console: GET /demo — fire scenario
  Console->>Proxy: mTLS MCP call_tool — header X-Clavenar-Demo-Prefix 8 hex
  Proxy->>Proxy: mint_correlation_id splices prefix into UUIDv4
  Note over Proxy: correlation_id = prefix-xxxx-4xxx-yxxx-xxxxxxxxxxxx
  Proxy->>HIL: POST /pending — Yellow tier, prefixed correlation_id
  HIL-->>Console: pending visible only when cookie prefix matches
  Visitor->>HIL: POST /decide/{id} — via console
  HIL->>HIL: 403 if pending.correlation_id does not start with cookie prefix
  HIL-->>Console: 200 approved or denied
  Console->>Ledger: GET /audit?prefix=...
  Ledger-->>Console: only rows whose correlation_id matches prefix
  Note over Sim,HIL: Simulator skip filter — SIM_HIL_SKIP_AGENT_ID_PREFIX=demo- — keeps visitor pendings from being auto-decided
```

## 5. Trust Chain

Every credential Clavenar issues, top to bottom. The root is the mTLS
CA (`clavenar-proxy/certs/ca.crt`). The Vault transit key
`clavenar-identity` (ed25519) is the only signing key the rest of the
stack trusts; the `/jwks.json` endpoint on `clavenar-identity` is the
sole verifier.

```mermaid
flowchart TD
  CA[mTLS CA root — clavenar-proxy/certs/ca.crt]
  Vault[Vault transit key — clavenar-identity ed25519]

  Bootstrap[Bootstrap certs — service-name.crt per service]
  AgentAttest[Agent attestation — hardware or k8s projected]
  HumanOIDC[Human OIDC id_token — Okta or Entra]

  SVID[Agent SVID — spiffe://wd.local/tenant/tid/agent/name/instance/uuidv7 — TTL up to 1h]
  Grant[Delegation grant JWT — act.sub = human, scope, yellow_scope]
  ActorToken[A2A actor token — audience-bound, TTL up to 60s, single use]
  WorkloadSVID[Workload SVID — per service, refresh every TTL/2 via ArcSwap]
  Sign[Per-action ed25519 signature — over canonical hashable row]
  LedgerRow[Ledger row — chain v2 or v3, prev_hash linked]

  JWKS[/jwks.json — public verifier endpoint/]

  CA --> Bootstrap
  Bootstrap --> WorkloadSVID
  Vault --> SVID
  Vault --> Grant
  Vault --> ActorToken
  Vault --> WorkloadSVID
  Vault --> Sign

  AgentAttest -->|POST /svid| SVID
  HumanOIDC -->|POST /grant — RFC 8693 token exchange| Grant
  SVID -->|POST /actor-token + grant| ActorToken
  Bootstrap -->|POST /workload-svid every TTL/2| WorkloadSVID

  SVID -->|present on call| Sign
  Grant -->|act.sub binds the human| Sign
  Sign -->|POST /sign — proxy after verdict resolves| LedgerRow
  LedgerRow -->|prev_hash links every prior row| LedgerRow

  Vault --> JWKS
  JWKS -->|verify| Sign
  JWKS -->|verify| Grant
  JWKS -->|verify| ActorToken
```
