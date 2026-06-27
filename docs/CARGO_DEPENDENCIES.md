# Cargo dependency conventions

clavenar has **no Cargo workspace today** — each repo is its own
standalone crate, pulled together by `path = "../..."` deps in local
dev and by sibling-checkout (`gh repo clone`) in CI.

That decision is deliberate. A real workspace would force every repo
to share a single `Cargo.lock`, every consumer rebuild on every
unrelated bump, and complicate the per-repo CI matrix that today is
the unit of independent releases. The trade-off is dependency drift:
nothing structurally prevents repo A from running `reqwest = "0.13"`
while repo B is on `0.12`, and we have hit that exact case (May 2026
audit found brain + ledger on 0.13 while everyone else was 0.12).

## Convention (until a meta-workspace is justified)

For deps that appear in three or more sibling repos, pin to a
**single workspace-canonical version**. The canonical pins live in
this document; per-repo `Cargo.toml` files mirror them. When a pin
needs to move, edit this doc first, then mirror into every consumer
in the same change set.

This is the same convention `deny.toml` already uses (see
`clavenar-specs/deny.toml` — synced verbatim across 20 Rust repos).

### Canonical pins

| Crate | Version | Features (typical) | Notes |
|---|---|---|---|
| `axum` | `0.8.9` | — | The route DSL + extractor surface every service builds on. |
| `axum-server` | `0.7` | `tls-rustls` | mTLS receive path. |
| `tokio` | `1` (loose) | `full` | Don't pin to a patch version; minor/patch bumps are SemVer-safe. |
| `tokio-rustls` | `0.26` | — | |
| `tokio-stream` | `0.1` | `sync` (for broadcast) | |
| `rustls` | `0.23` | `aws-lc-rs` (default-features off) | aws-lc-rs to avoid the ring/aws-lc-rs provider race. |
| `rustls-pemfile` | `2.1` | — | |
| `reqwest` | `0.12` | `json`, `rustls-tls` (default-features off) | Never accidentally pull native-tls. |
| `serde` | `1` | `derive` | |
| `serde_json` | `1` | — | |
| `async-nats` | `0.47` | — | All NATS publishers + the ledger consumer. |
| `tracing` | `0.1` | — | |
| `tracing-subscriber` | `0.3` | `env-filter`, `json` | |
| `tracing-opentelemetry` | `0.22` | — | |
| `opentelemetry` | `0.21` | — | |
| `opentelemetry_sdk` | `0.21` | `rt-tokio` | |
| `opentelemetry-otlp` | `0.14` | `grpc-tonic` | |
| `x509-parser` | `0.16` | — | SAN-URI extraction on client certs. |
| `tower-http` | `0.6` | `add-extension` | Loose-feature in services with broader needs (`full`). |
| `anyhow` | `1` | — | |
| `thiserror` | `1` | — | |
| `chrono` | `0.4` | `serde` | RFC 3339 timestamps in wire types. |
| `uuid` | `1` | `serde`, `v4` | |
| `metrics` | `0.22` | — | Prometheus facade. |
| `metrics-exporter-prometheus` | `0.14` | — | |
| `clap` | `4.5` | `derive`, `env` | CLI parsers. |
| `tempfile` | `3` | — | dev-dependencies for fixtures. |

`async-trait` (`0.1`), `futures` (`0.3`), `sha2` (`0.10`), `hex`
(`0.4`), `base64` (`0.22`) follow the same loose-version pattern.

### Shared crate: `clavenar-shared`

Truly duplicated infrastructure (byte-identical helpers, near-identical
middleware) lives in `repos/clavenar-shared/`, opted into via path-dep
and optional cargo features:

```toml
clavenar-shared = { path = "../clavenar-shared", features = ["mtls"] }
```

Modules today: `nats_tls` (always-on), `mtls` (gated behind the
`mtls` feature so non-mTLS consumers don't pull axum + x509-parser).
New extractions only land in `clavenar-shared` when **three or more
consumers** carry the same logic — the "three similar lines beat
the wrong abstraction" rule cuts both ways.

### When a meta-workspace becomes worth it

The per-repo independent build model breaks down if:

- We start needing atomic version bumps across services (e.g.,
  a wire-contract change that touches 5 repos in one PR).
- CI minutes spent re-resolving the same dep graph repo-by-repo start
  to dominate the bill (currently fine — Actions free tier 2000 min/
  month resets on the 1st; supply-chain job runs only on PR + weekly).
- A new dep needs a `[patch.crates-io]` override across all consumers.

When any of those land, revisit. The migration would be a single
`repos/Cargo.toml` with `[workspace]` + `[workspace.dependencies]`,
plus a `workspace = true` rewrite in each member's deps section.

## Process: bumping a pin

1. Edit the canonical version in this file.
2. Apply the same edit to every consumer's `Cargo.toml`.
3. Run `cargo update` per repo, commit the `Cargo.lock` churn alongside.
4. Verify `cargo deny check all` + `cargo clippy --all-targets -- -D warnings`
   per repo (workspace-wide via `for r in repos/clavenar-*; do …; done`).
5. Land one PR per repo (no PRs in this workspace — direct to main per
   workspace convention). Group commits in the same session so the
   dep graph stays internally consistent during the rollout.
