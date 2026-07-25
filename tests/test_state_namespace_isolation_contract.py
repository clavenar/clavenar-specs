import copy
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts" / "state-namespace-isolation-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts" / "state-namespace-isolation-v1.fixture.json").read_text()
)
EXPECTED_COMPONENTS = {
    "hil-pending",
    "ledger-chain",
    "ledger-live-views",
    "platform-reset",
    "proxy-routing",
    "shared-ownership",
}


def validate_semantics(document: dict) -> None:
    jsonschema.Draft202012Validator(SCHEMA).validate(document)
    ids = [component["id"] for component in document["components"]]
    if ids != sorted(ids) or set(ids) != EXPECTED_COMPONENTS:
        raise ValueError("namespace component inventory is incomplete or unordered")
    if document["cleanup"]["selection"] != "explicit-owner-only":
        raise ValueError("cleanup selection is not explicit")


class StateNamespaceIsolationContractTests(unittest.TestCase):
    def test_fixture_is_exact_and_complete(self) -> None:
        validate_semantics(FIXTURE)

    def test_operator_or_legacy_cleanup_is_rejected(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["cleanup"]["namespace"] = "operator"
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

        changed = copy.deepcopy(FIXTURE)
        changed["cleanup"]["legacyRetention"] = "optional"
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

    def test_volume_recreation_and_allocator_reset_are_rejected(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["cleanup"]["volumeAction"] = "recreate"
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

        changed = copy.deepcopy(FIXTURE)
        changed["prohibitions"].pop()
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

    def test_chain_version_and_namespace_order_are_fixed(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["ledger"]["chainVersion"] = 5
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

        changed = copy.deepcopy(FIXTURE)
        changed["namespaces"].reverse()
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

    def test_missing_component_or_source_check_is_rejected(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["components"].pop()
        with self.assertRaises((jsonschema.ValidationError, ValueError)):
            validate_semantics(changed)

        changed = copy.deepcopy(FIXTURE)
        changed["components"][0]["sourceChecks"] = []
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)


if __name__ == "__main__":
    unittest.main()
