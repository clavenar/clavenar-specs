import copy
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "contracts" / "hil-retention-v1.schema.json").read_text())
FIXTURE = json.loads((ROOT / "contracts" / "hil-retention-v1.fixture.json").read_text())


def validate_semantics(document: dict) -> None:
    jsonschema.Draft202012Validator(SCHEMA).validate(document)
    d08_cap = document["d08Binding"]["maximumRetentionSeconds"]
    for tier in document["tiers"]:
        if tier["terminalPayloadRetentionSeconds"] > d08_cap:
            raise ValueError(f"{tier['id']} payload retention exceeds D-08")
        if tier["metadataRetentionSeconds"] > d08_cap:
            raise ValueError(f"{tier['id']} metadata retention exceeds D-08")
    if document["protection"]["plaintextPersistence"]:
        raise ValueError("plaintext-at-rest is prohibited")
    if len(set(document["protection"]["aadFields"])) != len(
        document["protection"]["aadFields"]
    ):
        raise ValueError("AAD fields must be unique")


class HilRetentionContractTests(unittest.TestCase):
    def test_fixture_validates(self) -> None:
        validate_semantics(FIXTURE)

    def test_d08_cap_and_tier_order_are_fixed(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["tiers"][1]["terminalPayloadRetentionSeconds"] = 2592001
        with self.assertRaises((jsonschema.ValidationError, ValueError)):
            validate_semantics(changed)

        changed = copy.deepcopy(FIXTURE)
        changed["tiers"][0], changed["tiers"][1] = (
            changed["tiers"][1],
            changed["tiers"][0],
        )
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

    def test_plaintext_or_weak_envelope_is_rejected(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["protection"]["plaintextPersistence"] = True
        with self.assertRaises((jsonschema.ValidationError, ValueError)):
            validate_semantics(changed)

        changed = copy.deepcopy(FIXTURE)
        changed["protection"]["algorithm"] = "base64"
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

        changed = copy.deepcopy(FIXTURE)
        changed["protection"]["aadFields"].remove("tenant")
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

    def test_legacy_and_expiry_paths_fail_closed(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["legacyTier"]["unknownNewWrite"] = "standard"
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

        changed = copy.deepcopy(FIXTURE)
        changed["readBoundary"]["authenticationFailure"] = "return-null-payload"
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

    def test_wp_11_6_does_not_claim_purge_or_erasure(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["doesNotAssert"].remove("physical-purge")
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)


if __name__ == "__main__":
    unittest.main()
