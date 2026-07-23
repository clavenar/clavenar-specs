# Cryptographic verification profile

`clavenar.cryptographic-verification/v2` is the fail-closed verification
profile layered on `clavenar.ledger-chain/v5`. It distinguishes a valid
unkeyed hash walk from evidence whose historical signatures and RFC 3161
timestamps have also been verified against explicit trust.

The machine-readable sources are:

- `contracts/historical-signing-keys-v1.schema.json`
- `contracts/historical-signing-keys-v1.fixture.json`
- `contracts/cryptographic-verification-v2.schema.json`
- `contracts/cryptographic-verification-v2.fixture.json`

## Historical signing keys

Identity serves `GET /ledger-verification-keys` only on its workload-mTLS
listener. The exact Ledger workload certificate must receive the
`identity.verification-keys.read` capability. The response issuer and audience
are the two exact service SPIFFE IDs; HTTP reachability, a caller header, or the
public `/jwks.json` endpoint cannot supply this authority.

`generated_at <= evaluation_time < expires_at`, and the response lifetime is at
most 120 seconds. `sequence` is the greatest retained Vault Transit key
version. A verifier remembers the greatest sequence it has accepted and rejects
a lower value. `lineage_sha256` is SHA-256 over RFC 8785/JCS canonical JSON of
this exact object:

```json
{
  "audience": "<ledger SPIFFE ID>",
  "issuer": "<identity SPIFFE ID>",
  "keys": ["<keys in descending numeric version order>"],
  "sequence": 1
}
```

Each `public_key_sha256` is SHA-256 over the exact UTF-8
`public_key_pem` bytes, including its final newline. Exactly one key is
`active`; older retained keys are `historical_trusted`. Duplicate IDs,
unsupported algorithms, invalid PEM, fingerprints, times, ordering, active-key
counts, or lineage commitments invalidate the whole response.

A signed row is valid only when its exact `kid` exists, has state `active` or
`historical_trusted`, its row timestamp is not before `activated_at`, and its
signature verifies with that Ed25519 public key. A missing, `retired`, or
`untrusted` key is a verification failure, not an unsigned-row classification.
Partially populated signature/key fields also fail. `agent_spiffe` is
independently committed attribution and does not create a signing shape when
both `signature` and `key_id` are absent. Such optional-signature rows remain
explicitly unsigned hash-chain evidence.

### Bounded legacy lifecycle classification

The historical Identity lifecycle publisher generated the UUID and timestamp
used in its signature but omitted both from the request. Ledger therefore
retained different values, and the original signed position is not
recoverable. A forged-signature result is classified
`identity_lifecycle_position_not_retained` only for a frozen chain-v3
non-execution lifecycle row or an early chain-v5 non-execution lifecycle row
whose sequence is within the closed interval `416970..442530`, committed
`policy_decision` is exactly null, and key is exactly
`clavenar-identity:v35` or `clavenar-identity:v36`. Its count and first/last
sequence are explicit. It receives no verified-signature or compliance
credit. Hash-chain failure, malformed or partial signing fields, execution
rows, key failures, and every chain-v5 row outside that exact frozen producer
epoch remain invalid.

New non-execution lifecycle requests carry this exact object under the
chain-committed `policy_decision` field:

```json
{
  "contract": "clavenar.lifecycle-signed-position/v1",
  "id": "018f57f0-d9c8-7b35-8f80-7b28ac5bf342",
  "timestamp": "2026-07-23T10:00:00Z"
}
```

Identity signs those exact values and Ledger uses them as the retained row
position. Omission, partial fields, unknown fields, malformed values, or use on
another signing shape fails before append.

### Frozen pre-egress verdict projection

One frozen chain-v4 epoch signed the complete verdict reasoning immediately
before Proxy appended its egress audit note. The verifier always attempts the
exact stored verdict first. A forged chain-v4 result receives one additional
attempt only when the final delimiter is exactly ` | egress: `, the retained
signed prefix is nonempty, and the suffix is one of:

- `egress policy sanitize: [SSN=sanitize,CREDIT_CARD=sanitize,EMAIL=sanitize] (confidence 0.85)`
- `egress policy: sanitized [SSN=sanitize,CREDIT_CARD=sanitize,EMAIL=sanitize] (confidence 0.85)`
- `egress policy sanitize: [EMAIL=sanitize] (confidence 0.55)`
- `egress policy: sanitized [EMAIL=sanitize] (confidence 0.55)`

The retained prefix must then verify under the row's temporally valid
historical key. Unknown or changed suffixes remain forged. This is a
verification of the exact historical signing projection, not an exception:
the row increments `verified_signed_rows`. New verdict emissions sign the
final reasoning including the egress suffix, so this projection is never used
for current rows.

## RFC 3161 timestamps

Every retained `rfc3161` anchor is re-verified from its stored response bytes.
Verification requires:

1. the stored `proof_sha256` equals the response bytes (retained lowercase
   64-hex values and the explicit `sha256:`-prefixed form are both verified);
2. the response is a granted RFC 3161 `TimeStampResp`;
3. the CMS signature and ESS signer binding verify;
4. the timestamp certificate has the time-stamping extended-key purpose and
   verifies through the configured untrusted signer certificate to the pinned
   CA;
5. certificate validity covers the timestamp generation time; and
6. the message imprint is SHA-256 over the exact anchored chain hash.

The trust profile is a deployment input, and its root-plus-signer bytes are
committed as `trust_bundle_sha256`. Missing trust, a different root or signer,
malformed DER, wrong imprint, proof mutation, an invalid signature, or an
untrusted chain fails the cryptographic result. A generic webhook reference is
reported as an external reference but never counts as a verified TSA anchor.

## Aggregate and compliance rules

`GET /verify` may return a complete `clavenar.verified-chain/v1` commitment only
when the required cryptographic profile has status `verified` or
`verified_with_legacy_exceptions`. The second status requires every
non-excepted signed row to verify, a fresh accepted key lineage, no failed RFC
3161 response, and at least one verified RFC 3161 response when timestamp trust
is required. A changed key lineage or trust profile invalidates the incremental
checkpoint and forces a historical walk.

Compliance derivation consumes the cryptographic result. A non-null
`signature` or `key_id` is never itself evidence that a row is signed.
Signature-backed metrics count only rows in `verified_signed_rows`; the
`legacy_unverifiable.rows` count is never credited. Timestamp-backed controls
count only cryptographically verified RFC 3161 responses. `unavailable` or
`invalid` cryptography yields partial or no evidence and cannot satisfy Article
15.

This profile is evidence verification, not a conformity assessment or legal
conclusion.
