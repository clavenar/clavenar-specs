import copy
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts" / "tenant-lifecycle-saga-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts" / "tenant-lifecycle-saga-v1.fixture.json").read_text()
)


def validate_semantics(document: dict) -> None:
    jsonschema.Draft202012Validator(SCHEMA).validate(document)
    for plan in document["plans"]:
        orders = [step["order"] for step in plan["steps"]]
        if orders != list(range(1, len(orders) + 1)):
            raise ValueError(f"{plan['kind']} step order is not contiguous")
    offboard = document["plans"][1]["steps"]
    if offboard[0]["id"] != "authority_fence":
        raise ValueError("offboarding must fence authority first")
    if [step["id"] for step in offboard].index("ledger_final_export") > [
        step["id"] for step in offboard
    ].index("ledger_tombstone"):
        raise ValueError("final export must precede the ledger tombstone")


class TenantLifecycleSagaContractTests(unittest.TestCase):
    def test_fixture_validates_with_exact_order(self) -> None:
        validate_semantics(FIXTURE)

    def test_mutable_intent_and_concurrent_operation_are_rejected(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["idempotency"]["intentMutable"] = True
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

        changed = copy.deepcopy(FIXTURE)
        changed["idempotency"]["activePerTenant"] = 2
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

    def test_effect_cannot_precede_running_journal(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["journaling"]["beforeEffect"] = "best-effort"
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

    def test_offboard_authority_and_export_order_are_fixed(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["plans"][1]["steps"][0], changed["plans"][1]["steps"][1] = (
            changed["plans"][1]["steps"][1],
            changed["plans"][1]["steps"][0],
        )
        with self.assertRaises((jsonschema.ValidationError, ValueError)):
            validate_semantics(changed)

        changed = copy.deepcopy(FIXTURE)
        changed["plans"][1]["steps"][5], changed["plans"][1]["steps"][6] = (
            changed["plans"][1]["steps"][6],
            changed["plans"][1]["steps"][5],
        )
        with self.assertRaises((jsonschema.ValidationError, ValueError)):
            validate_semantics(changed)

    def test_retry_exhaustion_and_success_source_are_fail_closed(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["retry"]["exhaustion"] = "succeeded"
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

        changed = copy.deepcopy(FIXTURE)
        changed["receipt"]["successSource"] = "console-redirect"
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)


if __name__ == "__main__":
    unittest.main()
