<!-- public repo — do not add internal topology, secrets, deploy/runbook, strategy, or absolute host paths -->
# clavenar-specs — public spec hub: TECH_SPEC.md is the source of truth for every wire contract

## Build, test, lint
- Contract tests: `python3 -m unittest discover -v -s tests -p 'test_*.py'`
- Validate prose links and anchors through the repository-documentation gate in
  sibling `clavenar-e2e` after cross-repository documentation changes.
- There is no compiled application here, but the JSON schemas, fixtures, sync
  scripts, and Python regression tests are executable release inputs—not prose.

## Layout
- `TECH_SPEC.md` — the consolidated wire-contract spec; **source of truth**. Each
  `## ` section was once a standalone spec file; legacy cross-refs resolve to its
  anchors. After a `## Contents` TOC, opens with `§0. Module service map`
  (which services each module touches).
- `README.md` — system overview: problem space, four-layer architecture
  (Layer 1 proxy / 2 brain / 3 policy-engine / 4 ledger), per-layer behaviour,
  glossary (MCP, SPIFFE/SVID, A2A, PBAC, HIL, WAO).
- `FEATURES.md` — implementation-first companion: feature-family boundaries,
  owning sources, evidence authority, and executable verification routes.
- `SECURITY.md` — vulnerability-disclosure policy in the GitHub `SECURITY.md`
  convention; kept a separate root file so it surfaces in the GitHub Security tab.
- `deny.toml` — the **canonical** `cargo-deny` config for the whole Rust fleet.
- `contracts/` — versioned JSON schemas and canonical fixtures mirrored into
  implementing repositories; change the public contract here first.
- `scripts/` — contract synchronization and validation helpers, including the
  customer legal-exchange mirror.
- `tests/` — regression tests for contract fixtures, source mirrors, and public
  claim boundaries.
- `docs/ARCHITECTURE.md` — C4 context + container view, deployment topology,
  trust chain; the visual index over `TECH_SPEC.md`.
- `docs/CARGO_DEPENDENCIES.md` — cross-repo dependency conventions (no Cargo
  workspace; path-deps in dev, sibling-checkout in CI).

## Conventions & invariants
- **`TECH_SPEC.md` is the wire-contract source of truth.** When a contract
  changes, update it here first; design docs and READMEs follow. Spec is
  design-first; `FEATURES.md` is implementation-first — keep both in step.
- **`deny.toml` is the canonical sync source.** It is synced *verbatim* across
  every Rust repo. Edit it **here first**, then mirror the exact bytes into each
  other repo's `deny.toml` so CI gates stay uniform. Each `ignore` RUSTSEC entry
  carries a comment naming the issue and the path that pulls it in — never add a
  bare ignore.
- **Public repo — zero internal material.** This repo and its docs ship publicly.
  Carry no business/strategy, ops-runbook, secret, or host-topology content here;
  the `## Runbooks` section of `TECH_SPEC.md` is intentionally a stub ("maintained
  privately"). Keep it that way.
- **`SECURITY.md` stays a separate root file** — do not fold it into `TECH_SPEC.md`;
  the GitHub Security tab points at the root path.
- **Anchors are load-bearing.** Section renames break inbound cross-references and
  the `§0` service map. If you rename a `## ` heading, fix every link to it.
- Markdown voice is terse and technical; tables over prose where a table fits.
  Don't reformat untouched sections in an edit — keep diffs tight.
- Use fenced Mermaid for relationship, flow, and sequence diagrams, with an
  `accTitle` and `accDescr` in every diagram. Use Markdown tables for exact
  mappings. Do not add box-drawing or ASCII-art diagrams, or checked-in rendered
  diagram assets where Mermaid can express the same view.
- Commit subjects must start with a lowercase letter.

## Pointers
README.md — system overview · TECH_SPEC.md — wire contracts ·
FEATURES.md — verification recipes · SECURITY.md — disclosure policy ·
docs/ARCHITECTURE.md · docs/CARGO_DEPENDENCIES.md.
