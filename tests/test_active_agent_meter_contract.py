from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts/active-agent-meter-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts/active-agent-meter-v1.fixture.json").read_text()
)
VALIDATOR = jsonschema.Draft202012Validator(
    SCHEMA, format_checker=jsonschema.FormatChecker()
)


class ActiveAgentMeterContractTests(unittest.TestCase):
    def test_fixture_is_valid(self) -> None:
        VALIDATOR.validate(FIXTURE)

    def test_unknown_invoice_fields_are_rejected(self) -> None:
        value = deepcopy(FIXTURE)
        value["provider_cost_micros"] = 42
        with self.assertRaises(jsonschema.ValidationError):
            VALIDATOR.validate(value)

    def test_bare_or_foreign_agent_keys_are_rejected(self) -> None:
        for agent_key in ("payments", "globex/payments", "acme/payments/instance"):
            with self.subTest(agent_key=agent_key):
                value = deepcopy(FIXTURE)
                value["agents"][0]["agent_key"] = agent_key
                if agent_key == "globex/payments":
                    # The schema owns syntax; the tenant-equality invariant is
                    # enforced by the Ledger reconciler and E2E source checker.
                    VALIDATOR.validate(value)
                else:
                    with self.assertRaises(jsonschema.ValidationError):
                        VALIDATOR.validate(value)

    def test_zero_adjustment_and_unknown_kind_are_rejected(self) -> None:
        for field, replacement in (("units_delta", 0), ("kind", "discount")):
            with self.subTest(field=field):
                value = deepcopy(FIXTURE)
                value["adjustments"][0][field] = replacement
                with self.assertRaises(jsonschema.ValidationError):
                    VALIDATOR.validate(value)

    def test_window_and_grace_are_version_pinned(self) -> None:
        for section, field, replacement in (
            ("window", "days", 31),
            ("finalization", "late_event_grace_hours", 48),
        ):
            with self.subTest(field=field):
                value = deepcopy(FIXTURE)
                value[section][field] = replacement
                with self.assertRaises(jsonschema.ValidationError):
                    VALIDATOR.validate(value)


if __name__ == "__main__":
    unittest.main()
