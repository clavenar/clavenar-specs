# Cryptographic verification profile

`clavenar.cryptographic-verification/v1` is the fail-closed verification
profile layered on `clavenar.ledger-chain/v5`. It distinguishes a valid
unkeyed hash walk from evidence whose historical signatures and RFC 3161
timestamps have also been verified against explicit trust.

The machine-readable sources are:

- `contracts/historical-signing-keys-v1.schema.json`
- `contracts/historical-signing-keys-v1.fixture.json`
- `contracts/cryptographic-verification-v1.schema.json`
- `contracts/cryptographic-verification-v1.fixture.json`

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
Partially populated signing fields also fail. Truly unsigned row shapes remain
explicitly unsigned hash-chain evidence.

## RFC 3161 timestamps

Every retained `rfc3161` anchor is re-verified from its stored response bytes.
Verification requires:

1. the stored `proof_sha256` equals the response bytes;
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
when the required cryptographic profile has status `verified`. That status
requires every signed row to verify, a fresh accepted key lineage, no failed
RFC 3161 response, and at least one verified RFC 3161 response when timestamp
trust is required. A changed key lineage or trust profile invalidates the
incremental checkpoint and forces a historical walk.

Compliance derivation consumes the cryptographic result. A non-null
`signature` or `key_id` is never itself evidence that a row is signed.
Signature-backed metrics count a row only when the aggregate walk verified all
signed rows under the accepted lineage. Timestamp-backed controls count only
cryptographically verified RFC 3161 responses. `unavailable` or `invalid`
cryptography yields partial or no evidence and cannot satisfy Article 15.

This profile is evidence verification, not a conformity assessment or legal
conclusion.
