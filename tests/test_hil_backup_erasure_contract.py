import copy
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts" / "hil-backup-erasure-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts" / "hil-backup-erasure-v1.fixture.json").read_text()
)


def validate(document: dict) -> None:
    jsonschema.Draft202012Validator(SCHEMA).validate(document)


class HilBackupErasureContractTests(unittest.TestCase):
    def test_fixture_validates(self) -> None:
        validate(FIXTURE)

    def test_restore_cannot_prefer_embedded_disposition(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["dispositionAuthority"]["restoreMinimum"] = "backup-embedded"
        with self.assertRaises(jsonschema.ValidationError):
            validate(changed)

    def test_transaction_bound_is_fixed(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["sanitization"]["maximumRowsPerTransaction"] = 101
        with self.assertRaises(jsonschema.ValidationError):
            validate(changed)

    def test_public_receipt_cannot_add_sensitive_fields(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["receipt"]["requiredBindings"][-1] = "tenant"
        with self.assertRaises(jsonschema.ValidationError):
            validate(changed)


if __name__ == "__main__":
    unittest.main()
