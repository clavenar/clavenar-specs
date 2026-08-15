# Clavenar — implemented feature guide

This document is the implementation-first index for Clavenar. It describes
feature families, identifies their owning repositories or contracts, and
points to executable verification. [`TECH_SPEC.md`](TECH_SPEC.md) remains the
design and wire-contract authority.

`main` describes checked-in source. It does not, by itself, prove that a
package was published, a deployment was configured, or a public environment
is running that source. Use the evidence source that matches the claim:

| Claim | Authority |
|---|---|
| Wire shape or compatibility | Versioned schema and fixture in [`contracts/`](contracts/) |
| Source implementation | Owning repository, tests, and `AGENTS.md` |
| Cross-service behavior | `clavenar-e2e` contract checker or runner |
| Published artifact | Protected-distribution receipt and external-install contract |
| Live environment | Environment-bound deployment and smoke receipt |

Verification commands in this guide either include their working directory or
are written from the workspace directory containing `repos/`. This guide does
not prescribe one universal boot command; select the runner for the feature
and topology from `clavenar-e2e/docs/RUNNERS.md`.

## Contents

1. [Request control plane](#1-request-control-plane)
2. [Human-in-the-loop control](#2-human-in-the-loop-control)
3. [Identity, tenancy, and onboarding](#3-identity-tenancy-and-onboarding)
4. [Operator surfaces and authentication](#4-operator-surfaces-and-authentication)
5. [Forensic evidence and compliance projection](#5-forensic-evidence-and-compliance-projection)
6. [SDKs, CLI, and execution contracts](#6-sdks-cli-and-execution-contracts)
7. [Reliability, recovery, and lifecycle](#7-reliability-recovery-and-lifecycle)
8. [Assurance, detection, and evaluation](#8-assurance-detection-and-evaluation)
9. [Distribution and adoption paths](#9-distribution-and-adoption-paths)
10. [Security and release controls](#10-security-and-release-controls)
11. [Governed customer-facing boundaries](#11-governed-customer-facing-boundaries)
12. [Verification routes](#12-verification-routes)

---

## 1. Request control plane

An agent request reaches an upstream effect only after the configured identity,
semantic, deterministic-policy, and human-review controls have resolved. The
Proxy owns ordering and fail posture; downstream services own their specific
decisions.

| Capability | Implemented behavior | Primary owner |
|---|---|---|
| Authenticated ingress | Mutual TLS validates the peer and extracts its SPIFFE identity before agent traffic enters the pipeline. | `clavenar-proxy` |
| Serial enforcement | Security resolution completes before any upstream call; denied, expired, or unresolved decisions cannot race an effect. | `clavenar-proxy` |
| Semantic inspection | Intent, injection, supply-chain, malicious-code, persona-drift, and sequence signals are evaluated through bounded provider-neutral routes. | `clavenar-brain` |
| Deterministic policy | Rego policy is evaluated by `regorus` over server-owned time, velocity, spend, identity, history, and attestation inputs. | `clavenar-policy-engine` |
| Stateful breakers | Distributed velocity, spend, history, revocation, and containment state fail closed when the selected durable authority is unavailable. | Proxy, Policy, NATS KV |
| Explicit execution | Side-effect-free decisions and durable server execution use different selectors and recovery semantics. | Proxy, Lite, SDKs |
| Observe mode | A configured observe profile records the decision that enforcement would have made without representing it as an enforced block. | Proxy, Lite |
| Bounded admission | Body, request-rate, provider, queue, and concurrency ceilings prevent unbounded work from becoming an enforcement bypass. | Owning service |

### Semantic provider routing and qualification

[`clavenar.brain-provider-routing/v2`](contracts/brain-provider-routing-v2.fixture.json)
separates credential references, provider targets, named models, and workload
assignments. Inline secrets, ambiguous fallback, unknown versions, and
provider/credential mismatches fail validation. Runtime fallback is bounded to
declared replay-safe transient cases; authentication, invalid request,
malformed output, policy outcome, and ambiguous post-dispatch failures do not
silently try another provider.

Adapters are not automatically supported merely because they compile.
[`clavenar.brain-model-qualification/v1`](contracts/brain-model-qualification-v1.fixture.json)
binds the qualification corpus, repeated live runs, quality, cost, latency,
degradation, and evidence requirements. The generated support matrix is the
authority for qualification status.

```bash
cd repos/clavenar-specs
python3 -m unittest -v \
  tests.test_brain_provider_routing_contract \
  tests.test_brain_model_qualification_contract
cd ../clavenar-e2e
python3 scripts/check_brain_provider_routing.py
python3 scripts/check_brain_model_qualification.py --source-root .. --require-source
```

### Policy management and backtesting

Policy Engine persists versioned policy mutations with required reasons and a
durable forensic outbox. Console provides list, edit, diff, activation,
deactivation, rollback, and deletion workflows under server-side role checks.
Policy Lab evaluates a candidate against retained replay inputs before
activation. Signed policy exchange adds publisher verification, provenance,
and a mandatory backtest; it does not bypass local authorization.

The curated catalog is release-manifest governed rather than documented by a
hand-maintained count. Use
[`clavenar.curated-policy-release/v1`](contracts/curated-policy-release-v1.fixture.json)
and the owning Policy Engine tests for the current inventory.

```bash
cd repos/clavenar-policy-engine
cargo test
cd ../clavenar-e2e
./dev/run-policies.sh
```

---

## 2. Human-in-the-loop control

HIL converts a policy review outcome into a durable state machine. The
effective request is held until an accountable terminal decision exists.

| Capability | Implemented behavior |
|---|---|
| Tri-state decision | Green continues, Yellow parks for review, and Red denies. Missing or expired Yellow decisions do not become approvals. |
| Exact payload custody | The pending record binds the request that was reviewed; a different payload cannot reuse the decision. |
| Modify and resume | An authorized approver may replace bounded typed fields, after which policy is re-evaluated against the effective request. |
| Sandbox preview | Static analysis summarizes operation class and targets for the approver; the preview is not authorization. |
| Callback delivery | Approved asynchronous work may notify an allowlisted normalized callback target through bounded, durable delivery. |
| Assignment and annotation | Queue ownership and reviewer context are durable operator workflow, separate from the terminal decision. |
| Notification lifecycle | Slack, Teams, and webhook delivery records trigger, retry, terminal result, and resolution without fabricating a human decision. |
| Tenant and demo isolation | Authenticated tenant scope or a validated demo prefix constrains every collection, object, stream, and mutation route. |

Console supplies the primary Approval Center. Mobile-responsive browser flows
remain the supported small-screen path; a separate native mobile product is
not implied.

```bash
cd repos/clavenar-hil
cargo test
cd ../clavenar-e2e
python3 -m unittest -v \
  tests.test_hil_notification_lifecycle \
  tests.test_hil_retention
```

---

## 3. Identity, tenancy, and onboarding

Identity owns agents, workload credentials, grants, signatures, federation,
attestation results, lifecycle state, and their durable evidence.

### Agent and workload identity

| Capability | Boundary |
|---|---|
| Agent SVID issuance | The agent generates its key and CSR locally. Identity constructs the subject and SPIFFE URI, binds verified attestation, and never returns a private key. |
| Exact-current renewal | Renewal authenticates the exact current SVID and supersedes it atomically. Missing or corrupt enrolled state requires an explicit recovery ceremony. |
| Workload SVID refresh | Services renew short-lived workload credentials through exact-current generation state; automatic bootstrap fallback is forbidden. |
| Revocation | Revocation and supersession withdraw runtime authority and emit lifecycle evidence. |
| Credential recovery | A bounded, reasoned operator action revokes the current generation and opens one-use recovery authority. |

### Delegation, signatures, and federation

OIDC delegation grants intersect requested scopes with the registered agent
envelope. Per-action and detached-blob signatures carry typed target, tenant,
audience, purpose, operation, and lifetime bindings. A2A actor tokens add peer
trust-domain validation and durable replay prevention. Historical public keys
remain available for verification without retaining obsolete signing
authority.

Federation accepts only current signed peer bundles and exact trust-domain,
issuer, audience, subject, scope, and lifetime bindings. Unknown or stale
peers, wrong recipients, replayed token identities, and unavailable replay
state fail closed.

### Attestation

[`clavenar.attestation-verifier/v1`](contracts/attestation-verifier-v1.fixture.json)
binds evidence to nonce, CSR, SVID, workload, tenant, measurement, verifier,
and freshness. Production excludes development mock evidence. Approval
retirement, rotation, binding substitution, stale results, or verifier
unavailability withdraws attestation-required authority.

### Registry, tenant state, and lifecycle

The WAO registry implements create, suspend, unsuspend, decommission,
capability-envelope, transfer, migration, and certification workflows.
Production storage identities retain both tenant and agent dimensions.
Authenticated queue and control routes derive tenant authority from verified
identity rather than a request field.

[`clavenar.tenant-state-migration/v1`](contracts/tenant-state-migration-v1.fixture.json)
and [`clavenar.tenant-lifecycle-saga/v1`](contracts/tenant-lifecycle-saga-v1.fixture.json)
govern qualified cutover, restart-safe provisioning, authority fencing,
offboarding, export, deletion, and terminal receipts.

```bash
cd repos/clavenar-identity
cargo test
cd ../clavenar-e2e
./dev/run-onboarding.sh
./dev/run-federation.sh
python3 scripts/check_tenant_state_migration.py --source-root .. --require-source
python3 scripts/check_tenant_lifecycle_saga.py --source-root .. --require-source
```

---

## 4. Operator surfaces and authentication

Console is a server-rendered operator plane. It consumes service APIs through
named workload identity and enforces user roles again at every mutation.

### Operator surfaces

| Surface | Purpose |
|---|---|
| Audit and correlation views | Filtered event inspection, complete request reconstruction, verification, saved views, and bounded live tail |
| Agent narrative | Activity summary, tool and intent distribution, HIL outcomes, notable events, and deep-review context |
| Approval Center | Tenant-scoped pending work, assignment, annotation, decision, and notification status |
| Agent registry | Lifecycle, capability, SVID, grant, and status inspection |
| Policy management | Versioned policy editing, diff, replay, activation, rollback, catalog, and exchange |
| Compliance | Evidence-register projection and signed export entry point |
| Configuration | Redaction-safe dependency, feature, authentication, and readiness diagnostics |
| Operations | Cost/latency, fleet posture, incident cases, assurance, deep review, and simulator controls |
| Demo run | Scoped synthetic pipeline replay; demo evidence is never represented as customer-production state |

### Authentication and accountable decisions

Supported operator modes are selected explicitly: WebAuthn, OIDC, operator
mTLS, SAML where feature-enabled, and tightly bounded compatibility modes.
Non-loopback use refuses unsafe auth-disabled settings.

Roles are monotonic: Viewer reads, Approver may decide HIL work, and Admin may
mutate policy and registry state. Console derives a typed decision principal
from its authenticated session. HIL independently verifies the exact Console
workload and records subject, tenant, method, and credential provenance. A
caller-supplied display name is never the decision authority.

WebAuthn bootstrap and invitation state is durable and one-use. OIDC and SAML
validate issuer, audience, keys, tenant, groups, and configured assurance.
Authentication-generation rotation retains bounded overlap and invalidates
stale sessions after the transition.

```bash
cd repos/clavenar-console
cargo test
cd ../clavenar-e2e
python3 -m unittest -v \
  tests.test_hil_decision_principals \
  tests.test_hil_enrollment_state_contract \
  tests.test_hil_tenant_scope
```

---

## 5. Forensic evidence and compliance projection

### Durable forensic pipeline

Every accepted producer emits a versioned event with causal identity. Mutable
stages first commit intent and a durable outbox, then terminal state. Ledger
deduplicates the logical stage transactionally and appends it to a
tenant-qualified chain. Crash reconciliation and delivery-health telemetry
make missing or delayed stages observable.

The hash chain, signed lifecycle and decision rows, historical-key lineage,
and optional RFC 3161 anchors are distinct verification layers. A populated
signature field is not treated as verified unless the matching cryptographic
authority and lineage validate.

### Regulatory export

Ledger produces a signed Article 11/12-oriented archive containing bounded
chain rows, manifest, detached signature, verification instructions, and
optional technical documentation, analytical pointers, compliance register,
anchors, Annex IV projection, and post-market plan. Manifest schema v8 commits
every included block and a complete verified-chain summary.

The archive is independently verifiable with published historical keys. It is
evidence, not a claim of legal admissibility, conformity assessment, regulator
acceptance, or deployment compliance.

```bash
cd repos/clavenar-ledger
cargo test
cd ../clavenar-e2e
python3 scripts/check_cryptographic_verification_contract.py --source-root ..
```

### Continuous evidence projection

The compliance register derives control-specific status from one explicit
time window. `satisfied`, `partial`, and `no_data` are mechanical outcomes of
the declared predicates. Human-oversight projections require attributable
human decisions and channel provenance; robustness projections require the
declared denial and cryptographic evidence. Control mappings remain evidence
projections, not certification or legal advice.

### Cold tier and SIEM

Ledger can emit Iceberg v2 metadata with Parquet data to LocalFS or
S3-compatible storage and can stream bounded audit events to configured SIEM
sinks. Export pointers can be committed into a regulatory archive. Sink
availability, lifecycle, and retention remain deployment configuration, not a
universal product duration.

---

## 6. SDKs, CLI, and execution contracts

### Client surfaces

| Surface | Role |
|---|---|
| `clavenar-sdk` | Typed Rust clients for Ledger, HIL, Identity, Policy, Simulator, and operator workflows |
| `clavenarctl` | Device auth, agent lifecycle, migration, certification, policy generation, diagnostics, and regulatory export |
| TypeScript and Python SDKs | Anthropic/OpenAI wrappers, direct inspection, pending resolution, streaming, and realtime helpers |
| Go, Java, and .NET SDKs | Wire-compatible decision, pending, streaming, and governed-execution clients |
| Secure transport profile | Reloadable CA, client identity, token, proxy, deadline, and destination policy shared by maintained client paths |

Published versions and exact install commands come from
[`clavenar.external-install/v1`](contracts/external-install-v1.fixture.json),
not from prose in this section.

### Decision and execution separation

[`clavenar.sdk-cross-language/v1`](contracts/sdk-cross-language-v1.fixture.json)
requires each maintained language client to allocate one stable request
identity before network access and explicitly select the side-effect-free
decision contract. Atomic batch helpers retain order and request identity.

Governed execution is a separate host-controlled API. It validates an
authorization, commits durable intent, invokes one registered executor, and
persists the actual result and receipt. Proxy/Lite server execution similarly
commits intent before one upstream attempt and replays only retained completed
results. An interrupted execution reports uncertainty; it is never retried by
guessing that a second effect is safe.

[`clavenar.retry-separation/v1`](contracts/retry-separation-v1.fixture.json)
permits automatic transport retry only for explicit side-effect-free decisions.
[`clavenar.client-migration/v1`](contracts/client-migration-v1.fixture.json)
rejects unselected effect-capable requests before any mutable gate or effect.

```bash
cd repos/clavenar-e2e
python3 scripts/check-server-execution-contract.py --require-source
python3 scripts/check-retry-separation-contract.py \
  --source-root .. --require-source
python3 scripts/check-client-migration-contract.py \
  --source-root .. --require-source
```

---

## 7. Reliability, recovery, and lifecycle

Reliability requirements are contract-tested independently of any one
deployment topology.

| Capability | Implemented boundary |
|---|---|
| Storage | SQLite remains the local/default store where declared; the staged PostgreSQL Ledger path has explicit TLS, migration, and acceptance gates. |
| State inventory | Every durable or reconstructible state family has an owner, source, backup, restore, migration, and disposition. |
| Backup | Scheduled sets are encrypted, committed to exact source state, and written to configured offsite custody. |
| Restore | Recovery runs in isolation, verifies the restored state, and does not overwrite the active writer during validation. |
| Failover | Passive promotion requires writer fencing; ambiguous or double-writer state fails. |
| Readiness | Direct and transitive dependencies withdraw readiness without conflating process liveness. |
| Promotion | Candidate, smoke, public pointer, rollback, and terminal receipt form one transaction. |
| Upgrade | Stateful changes have compatibility, migration, candidate, and rollback rules before source state advances. |
| Alerts | Trigger, retry, terminal delivery, acknowledgement, and resolution are retained without treating best-effort notification as control success. |
| Erasure | Tenant and HIL deletion preserve required forensic evidence and apply explicit retained-backup disposition. |

The active deployment and retained portability/recovery harnesses are selected
through `clavenar-e2e`; source documentation does not claim that one local
command proves a live environment.

```bash
cd repos/clavenar-e2e
python3 scripts/check_dependency_readiness.py --source-root .. --require-source
python3 scripts/check_tenant_state_migration.py --source-root .. --require-source
python3 scripts/check_deployment_promotion.py --require-source
```

---

## 8. Assurance, detection, and evaluation

<a id="14-forensic-tier-deep-review"></a>

### Deep review and containment

Deep Review consumes selected forensic events asynchronously. It strips
untrusted prior verdict fields, minimizes provider input, applies durable
budget and retry rules, and writes a terminal finding or explicit failure
sentinel before acknowledging selected input. It never gates the live request.
High-confidence findings may request containment only after the primary finding
is durable; shadow mode records the proposed action without issuing it.

### Deception

Identity owns tenant-aware decoy registration and broadcasts the effective
set. Proxy may advertise reviewed lures and deterministically deny a matching
tool call before semantic evaluation. Degraded or stale decoy state advertises
and denies nothing rather than inventing registry contents. Decoy evidence and
containment requests remain explicit forensic events.

### Catalogs, simulator, and assurance

The chaos catalog and policy catalog are governed by exact release manifests.
[`clavenar.attack-release/v1`](contracts/attack-release-v1.fixture.json)
currently records **93 listed scenarios total** across proxy and direct-Identity
paths. Runtime selection accepts `--release-manifest`; owning tests prove the
compiled catalog matches the manifest. Do not copy category totals elsewhere.

The Simulator supplies scoped synthetic traffic for demonstrations and load
tests. Continuous Assurance schedules governed catalog execution and records
the exact release, environment, result, and verification status. Synthetic,
mock, or partial runs do not become customer or production evidence.

### Sandbox and outbound isolation

Sandbox statically summarizes a requested operation as a
`safe`/`risky`/`destructive` annotation; it does not authorize the operation.
Authorization, tenant authority, and isolation are enforced by their own
boundaries. The `clavenar.sandbox-adversarial-corpus/v1` binding in
[`clavenar.residual-product-disposition/v1`](contracts/residual-product-disposition-v1.fixture.json)
governs parser and classification adversarial cases.

Rooted-path validation prevents symlink and path escape. Outbound target
normalization rejects credentials, fragments, ambiguous domain boundaries,
local-use names, and unsafe IP targets. DNS pinning validates the complete
answer set and every bounded redirect before connecting.

Optional Exec remains evaluation-only. It requires exact Proxy workload
identity, an immutable allowlisted command policy, structured arguments,
cleared environment, default-deny egress, and hard CPU, process, memory,
file, output, and wall-clock ceilings. Production profiles reject opt-in.

### Discovery scanner

Shadow Scanner inventories likely agent integrations and credential exposure
from explicitly authorized sources. Scanner findings stay private by default;
publication requires a separately governed sanitized artifact. Discovery
output is a lead for review, not proof of compromise or customer state.

---

## 9. Distribution and adoption paths

### Lite evaluation path

`clavenar-lite` is the single-binary local evaluation edition. It combines
authenticated ingress, heuristic inspection, Rego policy, local HIL record and
decision APIs, callbacks, a hash-chained SQLite ledger, backup/restore, and
observe/enforce modes. It does not claim the managed Console approval workflow,
federation, compliance export, or full-edition resume-on-approve path.

`clavenarctl init --guard` can scaffold a local policy and Lite configuration.
The graduation report summarizes observed would-deny and would-review outcomes
and verifies the local chain. An optional local signature makes that report
tamper-evident; it is not an Identity-issued production attestation.

### Packages, images, and Helm

Protected distribution publishes only after exact source, artifact, SBOM,
provenance, license, and immutable-reference gates pass. Package registry,
release asset, image, and Helm availability is verified externally rather than
inferred from a badge or repository.

### Existing-cluster installation

The governed installer targets an existing Kubernetes or K3s API. It confirms
context, permissions, storage, immutable chart and image inputs, selected
credential references, workload readiness, and functional proof. It does not
create or reconfigure clusters, nodes, runtimes, firewalls, provisioners, or
cloud resources. Uninstall is plan-first and retains persistent data by
default.

### Documentation portal

The public documentation site is generated by Eleventy and validated before
and after rendering. Quickstarts, API references, recipes, install paths,
claims, routes, fragments, and served artifacts are reconciled with exact
inventories. A successful local build is source evidence, not a live-release
receipt.

---

## 10. Security and release controls

### Internal service identity and capabilities

Application hops use workload mTLS and exact SPIFFE identities. Generated
route capabilities map caller, method, path template, and capability with a
deny-unknown default. Health and metrics listeners remain separate where the
service contract requires them. Named forwarding identity grants only the
specific forwarding behavior; it does not become general internal authority.

### Supply chain

`clavenar-specs/deny.toml` is the byte-identical Rust fleet policy. Owning
repositories run their language-native dependency, license, test, lint, SBOM,
and provenance gates. Artifact publication is driven from a verified signed
stack BOM; mutable tags and source substitution are not release authority.

### Disclosure and threat model

All 30 repositories carry the same root `SECURITY.md`, governed by
[`clavenar.security-policy/v1`](contracts/security-policy-v1.fixture.json).
The public `security.txt` points reporters to the same private disclosure
channel. Threat documentation organizes trust boundaries and mitigations; it
does not claim that every deployment enabled every optional control.

### Route and schema inventory

[`clavenar.route-schema-release/v1`](contracts/route-schema-release-v1.fixture.json)
generates the exact governed route and schema inventory from owning source. It
rejects duplicate, missing, renamed, invalid, or non-identical projections.

```bash
cd repos/clavenar-e2e
python3 scripts/check_security_policy.py --source-root .. --require-source
python3 scripts/generate_route_schema_release.py --check
python3 scripts/check_endpoint_capability_matrix.py --source-root .. --require-source
```

---

## 11. Governed customer-facing boundaries

These contracts keep public product, commercial, legal, privacy, and release
claims tied to the evidence that can support them.

### Contract-tested documentation claims

[`clavenar.documentation-claim-boundaries/v1`](contracts/documentation-claim-boundaries-v1.fixture.json)
classifies attestation, approver provenance, signing, admissibility, retention,
and deployment wording. Public source, built pages, and the deployed origin reject retired
unconditional claims. Release, evaluation, demo, and customer-production state
remain distinct.

```bash
python3 repos/clavenar-e2e/scripts/check_documentation_claim_boundaries.py \
  --source-root repos --require-source
```

### Explicit compliance derivation boundaries

[`clavenar.compliance-derivation-boundaries/v1`](contracts/compliance-derivation-boundaries-v1.fixture.json)
binds configured authorities, freshness, loud degraded modes, fail-closed
verification, and exact register status semantics. A derived result describes
one evidence window; it is not a conformity assessment.

```bash
python3 repos/clavenar-e2e/scripts/check_compliance_derivation_boundaries.py \
  --source-root repos --require-source
```

### Contract-tested retention claims

[`clavenar.retention-claim-boundaries/v1`](contracts/retention-claim-boundaries-v1.fixture.json)
separates deployment-configured policy, HIL payload deadlines, Ledger vacuum
floors, recovery cadence, and export support. A fixed-duration public claim
requires its own approved lifecycle receipt.

```bash
python3 repos/clavenar-e2e/scripts/check_retention_claim_boundaries.py \
  --source-root repos --require-source
```

### Contract-tested public operational information

[`clavenar.public-operational-information/v1`](contracts/public-operational-information-v1.fixture.json)
permits sanitized architecture, public interfaces, portable contracts and
defaults, externally observable behavior, and protected release/security
evidence. Deployment-specific procedures remain private. A public exception
requires a reviewed classification receipt with exact source, surface,
necessity, threat review, approvals, and expiry.

```bash
python3 repos/clavenar-e2e/scripts/check_public_operational_information.py \
  --source-root repos --require-source
```

### Generated route and schema release inventory

[`clavenar.route-schema-release/v1`](contracts/route-schema-release-v1.fixture.json)
binds generated application routes and machine-validated schemas/examples to
their owning code and exact public/deployment mirrors.

```bash
python3 -m pytest repos/clavenar-specs/tests/test_route_schema_release_contract.py
python3 repos/clavenar-e2e/scripts/generate_route_schema_release.py --check
```

### Executable staged and public documentation

[`clavenar.executable-documentation/v1`](contracts/executable-documentation-v1.fixture.json)
binds SDK, Rust, Lite, CLI, Helm, and website recipes to exact `staged` and
`public` phases. Both use clean immutable runners; public execution additionally
verifies the released BOM.

```bash
python3 repos/clavenar-e2e/scripts/check_executable_documentation.py \
  --source-root repos --require-source
```

### Exact public external installs

[`clavenar.external-install/v1`](contracts/external-install-v1.fixture.json)
binds maintained package, binary, release-asset, image, and Helm surfaces to
exact immutable versions. It verifies anonymous downloads and pulls, checksums,
clean package use, and a fresh Helm installation using exact image digests.

```bash
python3 repos/clavenar-e2e/scripts/check_external_install.py \
  --source-root repos
```

### Existing-cluster operator install

[`clavenar.cluster-install/v1`](contracts/cluster-install-v1.fixture.json)
binds `install.sh` and `uninstall.sh` to checksum-verified immutable releases
for an existing Kubernetes or K3s cluster. Credential selection uses existing
Secret references; persistent data is retained unless the operator supplies
the explicit destructive confirmation required by the uninstaller.

```bash
python3 repos/clavenar-e2e/scripts/check_cluster_install.py \
  --source-root repos
```

### Minimized public pilot intake

[`clavenar.pilot-privacy-intake/v1`](contracts/pilot-privacy-intake-v1.fixture.json)
limits public forms to a business email and allowlisted non-sensitive
qualification values. It rejects free text and production-system, credential,
incident, vulnerability, personal, or regulated-data detail. Retention and
provider inventory remain explicit and contract-tested.

```bash
python3 repos/clavenar-e2e/scripts/check_pilot_privacy_intake.py \
  --source-root repos --require-source
```

### Customer-controlled legal and secure-exchange pack

[`clavenar.customer-legal-exchange/v1`](contracts/customer-legal-exchange-v1.fixture.json)
binds the legal templates, offer schedule, pack index, exchange guide, and
local-only exchange tool. Customer-specific terms remain unsigned blanks until
an executed Order Form selects them. The exchange uses customer/order-specific
X25519 recipients and AES-256-GCM authenticated encryption without a network
path.

```bash
python3 repos/clavenar-e2e/scripts/check_customer_legal_exchange.py \
  --source-root repos --require-source
```

### Evidence-gated outreach and onboarding

[`clavenar.onboarding-prospect-evidence/v1`](contracts/onboarding-prospect-evidence-v1.fixture.json)
keeps prospect identities and raw contact data outside the release graph.
Discovery advances only from committed evidence of actual outreach and an
actual interview; source completeness and builds are not customer evidence.
Production-pilot approval remains separate.

```bash
python3 repos/clavenar-e2e/scripts/check_onboarding_prospect_evidence.py \
  --source-root repos --require-source --require-private-inputs
```

### Exact commercial offer and validation gate

[`clavenar.commercial-offer/v1`](contracts/commercial-offer-v1.fixture.json)
defines Founding Design Partner Offer 1.0.0 once: a four-week USD $0 evaluation,
one agent, one tool/action surface, optional signed 12-month USD $15,000 first
subscription year for up to 25 per-tenant registered agents, and a separately
signed USD $36,000 renewal. It grants no production approval, automatic
renewal, lifetime lock, automatic overage, or publicity right.

Private commercial validation requires founder-supplied financial inputs, an
actual pricing conversation, and exact cross-functional approval. Source
completeness is not market validation.

```bash
python3 repos/clavenar-e2e/scripts/check_commercial_offer.py \
  --source-root repos --require-source --require-private-inputs
```

---

## 12. Verification routes

Choose the smallest proof that matches the claim, then escalate when the claim
crosses a service or release boundary.

### Source and contract verification

```bash
cd repos/clavenar-specs
python3 -m unittest discover -v -s tests -p 'test_*.py'

cd ../clavenar-e2e
python3 scripts/check_repository_documentation.py --source-root .. --require-source
python3 -m unittest discover -v -s tests -p 'test_*.py'
```

### Service verification

Run the changed repository's commands from its `AGENTS.md`. Those commands own
the language toolchain, formatting, unit/integration tests, supply-chain gate,
and any required sibling dependencies. A passing unrelated service test is not
evidence for a cross-service feature.

### Integration verification

Select a focused runner from `repos/clavenar-e2e/docs/RUNNERS.md`. The runner
catalog records its boot model, dependencies, mutation level, and assertions.
Retained Compose runners and the adopted Kubernetes paths are distinct proofs;
do not silently substitute one for the other.

### Release and live verification

Use the exact signed BOM, protected-distribution receipt, external-install
runner, deployment-promotion receipt, and environment smoke appropriate to the
claim. Public endpoints must report the promoted release. Repository state,
local builds, demos, and simulators do not prove customer deployment state.
