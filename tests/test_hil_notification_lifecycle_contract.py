from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts/hil-notification-lifecycle-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts/hil-notification-lifecycle-v1.fixture.json").read_text()
)
VALIDATOR = jsonschema.Draft202012Validator(
    SCHEMA, format_checker=jsonschema.FormatChecker()
)


class HilNotificationLifecycleContractTests(unittest.TestCase):
    def test_fixture_is_valid(self) -> None:
        VALIDATOR.validate(FIXTURE)

    def test_unknown_fields_are_rejected(self) -> None:
        value = deepcopy(FIXTURE)
        value["routing_key"] = "must-never-leak"
        with self.assertRaises(jsonschema.ValidationError):
            VALIDATOR.validate(value)

    def test_invalid_event_name_is_rejected(self) -> None:
        value = deepcopy(FIXTURE)
        value["phase"] = "triggered"
        with self.assertRaises(jsonschema.ValidationError):
            VALIDATOR.validate(value)

    def test_update_requires_pending_and_distinct_update_identity(self) -> None:
        value = deepcopy(FIXTURE)
        value["phase"] = "update"
        value["notification_id"] = (
            "12345678-1234-4123-8123-123456789abc:update:approval-1"
        )
        VALIDATOR.validate(value)
        value["status"] = "approved"
        with self.assertRaises(jsonschema.ValidationError):
            VALIDATOR.validate(value)

    def test_resolve_requires_terminal_status_time_and_identity(self) -> None:
        value = deepcopy(FIXTURE)
        value["phase"] = "resolve"
        value["status"] = "expired"
        value["notification_id"] = (
            "12345678-1234-4123-8123-123456789abc:resolve:expired"
        )
        value["decided_at"] = "2026-07-26T12:10:00Z"
        VALIDATOR.validate(value)
        value["decided_at"] = None
        with self.assertRaises(jsonschema.ValidationError):
            VALIDATOR.validate(value)


if __name__ == "__main__":
    unittest.main()
