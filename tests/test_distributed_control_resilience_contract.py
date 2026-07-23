import copy
import hashlib
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "contracts" / "distributed-control-resilience-v1.fixture.json"
SCHEMA = ROOT / "contracts" / "distributed-control-resilience-v1.schema.json"
INVENTORY = ROOT / "contracts" / "distributed-control-state-v1.fixture.json"


class DistributedControlResilienceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE.read_text())
        cls.schema = json.loads(SCHEMA.read_text())
        cls.inventory = json.loads(INVENTORY.read_text())

    def validate(self, value: dict) -> None:
        jsonschema.Draft202012Validator(self.schema).validate(value)

    def test_fixture_validates_and_binds_exact_inventory_bytes(self) -> None:
        self.validate(self.fixture)
        digest = hashlib.sha256(INVENTORY.read_bytes()).hexdigest()
        self.assertEqual(digest, self.fixture["inventory"]["sha256"])

    def test_every_mandatory_inventory_row_fails_closed_exactly_once(self) -> None:
        inventory_ids = {
            row["id"]
            for row in self.inventory["controls"]
            if row["classification"] == "mandatory"
        }
        policies = self.fixture["mandatoryControls"]
        policy_ids = [row["id"] for row in policies]
        self.assertEqual(policy_ids, sorted(policy_ids))
        self.assertEqual(inventory_ids, set(policy_ids))
        self.assertEqual(len(policy_ids), len(set(policy_ids)))
        self.assertEqual({"fail-closed"}, {row["outageMode"] for row in policies})
        self.assertEqual({"disabled"}, {row["snapshotMode"] for row in policies})

    def test_initial_sync_and_post_hil_boundaries_are_explicit(self) -> None:
        policies = {row["id"]: row for row in self.fixture["mandatoryControls"]}
        for control_id in (
            "agent-suspension",
            "decoy-invocation",
            "force-hil-containment",
            "grant-max-uses",
            "grant-revocation",
        ):
            self.assertEqual("process-readiness", policies[control_id]["initialSync"])
        self.assertEqual(
            "per-applicable-key", policies["tenant-spend-quota"]["initialSync"]
        )
        self.assertEqual(
            {"agent-suspension", "force-hil-containment", "grant-revocation", "tenant-spend-quota"},
            {row["id"] for row in policies.values() if row["postHilRecheck"]},
        )

    def test_only_advertisement_may_degrade_without_authorizing(self) -> None:
        self.assertEqual(
            [
                {
                    "id": "decoy-advertisement",
                    "degradedBehavior": "omit-advertisement",
                    "authorizationEffect": "none",
                }
            ],
            self.fixture["advisoryControls"],
        )

    def test_schema_rejects_fail_open_snapshot_and_incomplete_rows(self) -> None:
        fail_open = copy.deepcopy(self.fixture)
        fail_open["mandatoryControls"][0]["outageMode"] = "fail-open"
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(fail_open)

        snapshot = copy.deepcopy(self.fixture)
        snapshot["snapshotAuthorization"]["mode"] = "signed"
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(snapshot)

        incomplete = copy.deepcopy(self.fixture)
        del incomplete["mandatoryControls"][0]["initialSync"]
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(incomplete)

        unknown = copy.deepcopy(self.fixture)
        unknown["mandatoryControls"][0]["fallback"] = "allow"
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(unknown)


if __name__ == "__main__":
    unittest.main()
