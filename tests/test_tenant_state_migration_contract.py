import copy
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts" / "tenant-state-migration-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts" / "tenant-state-migration-v1.fixture.json").read_text()
)
EXPECTED_STATES = {
    "agent-lifecycle-state",
    "agent-rate-buckets",
    "hil-pending-rows",
    "lite-pending-access",
    "policy-learning",
    "policy-replay",
    "regulatory-exports",
    "revocation-controls",
    "spend-history",
    "tenant-quota-buckets",
    "tool-definition-pins",
    "vault-upstream-secrets",
    "velocity-history",
}


def validate_semantics(document: dict) -> None:
    jsonschema.Draft202012Validator(SCHEMA).validate(document)
    ids = [state["id"] for state in document["states"]]
    if ids != sorted(ids) or set(ids) != EXPECTED_STATES:
        raise ValueError("tenant state inventory is incomplete, duplicated, or unordered")
    for state in document["states"]:
        if state["cutoverWrite"] != "qualified-only":
            raise ValueError(f"{state['id']} permits an unqualified write")
        if not state["sourceChecks"]:
            raise ValueError(f"{state['id']} lacks source evidence")
    compared = {
        state["id"]
        for state in document["states"]
        if state["legacyRead"] == "tenant-bound-compare"
    }
    if compared != {"vault-upstream-secrets"}:
        raise ValueError("only Vault has an authoritative legacy value to compare")


class TenantStateMigrationContractTests(unittest.TestCase):
    def test_fixture_validates_and_inventory_is_exact(self) -> None:
        validate_semantics(FIXTURE)

    def test_cross_tenant_collision_vector_is_required(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["collisionVector"]["tenantB"] = "acme"
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

    def test_dual_write_and_unqualified_cutover_are_rejected(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["migration"]["legacyDualWriteAllowed"] = True
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

        changed = copy.deepcopy(FIXTURE)
        changed["states"][0]["cutoverWrite"] = "bare-compatible"
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

    def test_missing_state_or_source_evidence_is_rejected(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["states"].pop()
        with self.assertRaises((jsonschema.ValidationError, ValueError)):
            validate_semantics(changed)

        changed = copy.deepcopy(FIXTURE)
        changed["states"][0]["sourceChecks"] = []
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

    def test_unknown_migration_fields_are_rejected(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["migration"]["fallbackTenant"] = "default"
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)


if __name__ == "__main__":
    unittest.main()
