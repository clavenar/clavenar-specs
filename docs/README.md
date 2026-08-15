# Clavenar specification guides

This directory contains readable guides for specific integration and design
questions. It does not replace the normative sources at the repository root.

| Guide | Use it for |
|---|---|
| [Architecture](ARCHITECTURE.md) | System boundaries, service relationships, deployment roles, demo isolation, and credential flow. |
| [Cargo dependencies](CARGO_DEPENDENCIES.md) | Fleet-wide Rust dependency pins and the process for changing them. |
| [Cryptographic verification](CRYPTOGRAPHIC_VERIFICATION.md) | Historical signing-key trust, RFC 3161 verification, result classification, and compliance inputs. |
| [Route and schema inventory](ROUTE_SCHEMA_INVENTORY.md) | Generated application routes and representative integration payloads for release 1.234.0. |
| [SDK migration](SDK_MIGRATION.md) | Client migration to explicit decision or durable server-execution contracts. |

## Source authority

| Question | Authority |
|---|---|
| What bytes cross a public wire boundary? | [`TECH_SPEC.md`](../TECH_SPEC.md) and the matching file under [`contracts/`](../contracts/) |
| Which feature family owns an implementation or verification route? | [`FEATURES.md`](../FEATURES.md) |
| How do components relate or how should an integrator apply a contract? | The guides in this directory |

If a guide conflicts with `TECH_SPEC.md` or a machine-readable contract, the
guide is stale. Reconcile all three in the same change; do not use companion
prose to create a second wire authority.

All content here is public product documentation. Deployment-specific topology,
credentials, customer material, and operating procedures remain private.
