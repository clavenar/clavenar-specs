import copy
from datetime import datetime
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts" / "alert-delivery-lifecycle-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts" / "alert-delivery-lifecycle-v1.fixture.json").read_text()
)


def validate_semantics(receipt: dict) -> None:
    jsonschema.Draft202012Validator(
        SCHEMA,
        format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
    ).validate(receipt)
    timestamps = [
        receipt["alert"]["startsAt"],
        receipt["firing"]["receivedAt"],
        receipt["acknowledgement"]["acknowledgedAt"],
        receipt["alert"]["endsAt"],
        receipt["resolution"]["receivedAt"],
    ]
    parsed = [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in timestamps]
    if parsed != sorted(parsed):
        raise ValueError("alert lifecycle timestamps are not monotonic")
    if receipt["firing"]["notificationId"] == receipt["resolution"]["notificationId"]:
        raise ValueError("firing and resolution notifications must be distinct")


class AlertDeliveryLifecycleContractTest(unittest.TestCase):
    def test_fixture_validates(self) -> None:
        validate_semantics(FIXTURE)

    def test_discard_or_unauthenticated_receiver_is_rejected(self) -> None:
        for field, value in (("discardReceiver", True), ("authenticated", False)):
            mutated = copy.deepcopy(FIXTURE)
            mutated["routing"][field] = value
            with self.assertRaises(jsonschema.ValidationError):
                validate_semantics(mutated)

    def test_missing_acknowledgement_or_resolution_is_rejected(self) -> None:
        for field in ("acknowledgement", "resolution"):
            mutated = copy.deepcopy(FIXTURE)
            del mutated[field]
            with self.assertRaises(jsonschema.ValidationError):
                validate_semantics(mutated)

    def test_non_monotonic_or_reused_notification_is_rejected(self) -> None:
        mutated = copy.deepcopy(FIXTURE)
        mutated["acknowledgement"]["acknowledgedAt"] = "2026-07-24T14:59:00Z"
        with self.assertRaises(ValueError):
            validate_semantics(mutated)
        mutated = copy.deepcopy(FIXTURE)
        mutated["resolution"]["notificationId"] = mutated["firing"]["notificationId"]
        with self.assertRaises(ValueError):
            validate_semantics(mutated)


if __name__ == "__main__":
    unittest.main()
