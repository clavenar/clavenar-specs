import copy
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "contracts" / "hil-erasure-v1.schema.json").read_text())
FIXTURE = json.loads((ROOT / "contracts" / "hil-erasure-v1.fixture.json").read_text())


def validate_semantics(document: dict) -> None:
    jsonschema.Draft202012Validator(SCHEMA).validate(document)
    if document["deadlineErasure"]["maximumRowsPerSweep"] > 100:
        raise ValueError("HIL erasure sweep is unbounded")
    allowed = set(document["audit"]["allowedPayloadFields"])
    prohibited = {
        "request_payload",
        "modified_payload",
        "sandbox_report",
        "narrative",
        "approver",
        "credential",
        "notification",
        "reason",
    }
    if allowed & prohibited:
        raise ValueError("deletion audit permits sensitive content")


class HilErasureContractTests(unittest.TestCase):
    def test_fixture_validates(self) -> None:
        validate_semantics(FIXTURE)

    def test_hold_and_sweep_bounds_are_fixed(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["deadlineErasure"]["maximumRowsPerSweep"] = 101
        with self.assertRaises((jsonschema.ValidationError, ValueError)):
            validate_semantics(changed)

        changed = copy.deepcopy(FIXTURE)
        changed["legalHold"]["crossTenantOrUnknown"] = "forbidden"
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

    def test_sensitive_audit_field_is_rejected(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["audit"]["allowedPayloadFields"][-1] = "reason"
        with self.assertRaises((jsonschema.ValidationError, ValueError)):
            validate_semantics(changed)

    def test_wp_11_7_does_not_claim_backup_erasure(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["doesNotAssert"].remove("backup-copy-erasure")
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)


if __name__ == "__main__":
    unittest.main()
