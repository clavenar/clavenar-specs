import copy
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "contracts" / "distributed-control-state-v1.fixture.json"
SCHEMA = ROOT / "contracts" / "distributed-control-state-v1.schema.json"


class DistributedControlStateContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE.read_text())
        cls.schema = json.loads(SCHEMA.read_text())

    def validate(self, value: dict) -> None:
        jsonschema.Draft202012Validator(self.schema).validate(value)

    def test_fixture_validates(self) -> None:
        self.validate(self.fixture)

    def test_inventory_is_complete_unique_and_ordered(self) -> None:
        ids = [item["id"] for item in self.fixture["controls"]]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            {
                "agent-suspension",
                "decoy-advertisement",
                "decoy-invocation",
                "force-hil-containment",
                "grant-max-uses",
                "grant-revocation",
                "tenant-spend-quota",
            },
            set(ids),
        )

    def test_only_non_authorizing_catalog_advertisement_is_advisory(self) -> None:
        classifications = {
            item["id"]: item["classification"] for item in self.fixture["controls"]
        }
        self.assertEqual("advisory", classifications.pop("decoy-advertisement"))
        self.assertTrue(classifications)
        self.assertEqual({"mandatory"}, set(classifications.values()))

    def test_durable_kv_contract_is_explicit(self) -> None:
        kv_rows = [
            item
            for item in self.fixture["controls"]
            if item["replication"]["mechanism"].startswith("jetstream-kv")
        ]
        self.assertEqual(6, len(kv_rows))
        for item in kv_rows:
            replication = item["replication"]
            self.assertEqual("retained", replication["durability"])
            self.assertEqual("file", replication["storage"])
            self.assertIn(replication["history"], (1, 64))
            self.assertEqual(
                "CLAVENAR_CONTROL_STATE_REPLICAS",
                replication["replicasEnvironment"],
            )

    def test_authority_and_projection_roles_are_not_ambiguous(self) -> None:
        for item in self.fixture["controls"]:
            self.assertGreaterEqual(len(item["authorities"]), 1)
            for authority in item["authorities"]:
                self.assertEqual("retained", authority["durability"])
            self.assertEqual(
                sorted(item["replication"]["readers"]),
                item["replication"]["readers"],
            )
            self.assertGreaterEqual(len(item["sources"]), 2)

    def test_schema_rejects_weakened_or_incomplete_rows(self) -> None:
        mandatory = copy.deepcopy(self.fixture)
        mandatory["controls"][0]["classification"] = "optional"
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(mandatory)

        incomplete = copy.deepcopy(self.fixture)
        del incomplete["controls"][0]["recovery"]
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(incomplete)

        unknown = copy.deepcopy(self.fixture)
        unknown["controls"][0]["fallback"] = "allow"
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(unknown)


if __name__ == "__main__":
    unittest.main()
