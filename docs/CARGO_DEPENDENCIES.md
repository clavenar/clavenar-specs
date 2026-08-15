# Cargo dependency policy

Clavenar is a collection of independently released Rust crates, not a Cargo
workspace. Local development and CI place the repositories in sibling
directories so path dependencies resolve without a shared root manifest or
lockfile.

This preserves repository-level release and test boundaries, but Cargo cannot
prevent dependency drift across repositories. This document supplies the
coordination policy; each crate's `Cargo.toml` and `Cargo.lock` remain the
executable record of what that crate builds.

## Fleet pins

A dependency used by three or more Clavenar repositories should use the fleet
pin below. Features may differ by consumer, but transport and TLS choices must
remain compatible. A deliberate exception belongs in the consuming manifest
with a reason and must be reviewed during the next coordinated bump.

Change this table and all affected manifests as one coordinated change set.
Unlike this version table, the root [`deny.toml`](../deny.toml) is copied
byte-for-byte into every Rust repository.

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

`async-trait` (`0.1`), `futures` (`0.3`), `sha2` (`0.10`), `hex` (`0.4`),
and `base64` (`0.22`) follow the same major-or-minor pinning pattern.

## Shared infrastructure

Infrastructure used by at least three services belongs in `clavenar-shared`.
Consumers select only the features they need:

```toml
clavenar-shared = { path = "../clavenar-shared", features = ["mtls"] }
```

The crate's `[features]` table is the authoritative feature inventory. Do not
copy that evolving list into this guide. New abstractions belong there only
after three consumers carry materially identical logic; service-specific
behavior remains local.

## When to reconsider a Cargo workspace

Re-evaluate the independent-crate model when one or more of these conditions
becomes persistent:

- releases routinely require one atomic lockfile change across many services;
- repeated dependency resolution dominates CI time; or
- a fleet-wide `[patch.crates-io]` override becomes necessary.

A migration would introduce a root `[workspace]` and
`[workspace.dependencies]`, then replace member pins with `workspace = true`.
That is a release-boundary change, not a dependency cleanup.

## Changing a pin

1. Identify every consumer from canonical `Cargo.toml` files.
2. Update this table and every affected manifest.
3. Run `cargo update` in each consumer and review its `Cargo.lock` diff.
4. Run the commands required by each repository's `AGENTS.md`, including its
   tests, Clippy, and supply-chain checks.
5. Keep the coordinated commits together so the fleet does not advertise a pin
   that its consumers have not adopted.

Review lockfile changes for unexpected TLS backends, duplicate major versions,
new native dependencies, and newly introduced advisories or license classes.
