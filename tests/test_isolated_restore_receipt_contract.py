import copy
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "contracts" / "isolated-restore-receipt-v1.fixture.json"
SCHEMA = ROOT / "contracts" / "isolated-restore-receipt-v1.schema.json"
INVENTORY = ROOT / "contracts" / "state-recovery-inventory-v1.fixture.json"


class IsolatedRestoreReceiptContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        cls.inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))

    def validate(self, value: dict) -> None:
        jsonschema.Draft202012Validator(
            self.schema,
            format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
        ).validate(value)

    def validate_semantics(self, value: dict) -> None:
        self.validate(value)
        for result in value["stateResults"]:
            self.assertEqual(
                result["withinRpo"],
                result["lossSeconds"] <= result["rpoSeconds"],
            )
            self.assertEqual(
                result["withinRto"],
                result["restoreSeconds"] <= result["rtoSeconds"],
            )

    def test_fixture_validates_and_withholds_only_future_claims(self) -> None:
        self.validate_semantics(self.fixture)
        self.assertEqual(
            {"disaster-recovery", "upgrade-safety"},
            set(self.fixture["doesNotAssert"]),
        )

    def test_all_inventory_states_are_covered_once_with_exact_objectives(self) -> None:
        inventory_states = {state["id"]: state for state in self.inventory["states"]}
        objectives = {
            profile["id"]: profile
            for profile in self.inventory["profiles"]["objectives"]
        }
        results = self.fixture["stateResults"]
        self.assertEqual(set(inventory_states), {result["stateId"] for result in results})
        self.assertEqual(len(results), len({result["stateId"] for result in results}))
        for result in results:
            state = inventory_states[result["stateId"]]
            objective = objectives[state["objectiveProfile"]]
            self.assertEqual(state["objectiveProfile"], result["objectiveProfile"])
            self.assertEqual(objective["rpoSeconds"], result["rpoSeconds"])
            self.assertEqual(objective["rtoSeconds"], result["rtoSeconds"])
            self.assertLessEqual(result["lossSeconds"], result["rpoSeconds"])
            self.assertLessEqual(result["restoreSeconds"], result["rtoSeconds"])

    def test_partition_matches_backup_inventory_and_dispositions(self) -> None:
        coverage = self.fixture["coverage"]
        partitions = {
            "restored": set(coverage["capturedStateIds"]),
            "external-custody": set(coverage["externalCustodyStateIds"]),
            "reconstructed": set(coverage["reconstructibleStateIds"]),
            "signed-source": set(coverage["signedSourceStateIds"]),
        }
        seen: set[str] = set()
        for partition in partitions.values():
            self.assertFalse(seen & partition)
            seen |= partition
        self.assertEqual(
            {state["id"] for state in self.inventory["states"]},
            seen,
        )
        for result in self.fixture["stateResults"]:
            self.assertIn(result["stateId"], partitions[result["disposition"]])

    def test_unsafe_or_partial_restore_cannot_pass(self) -> None:
        mutations = [
            ("chain", "complete", False),
            ("chain", "plaintextImported", True),
            ("isolation", "productionVolumesMounted", 1),
            ("isolation", "hostPortsPublished", 1),
            ("validation", "sqlite", None),
        ]
        for outer, inner, value in mutations:
            with self.subTest(outer=outer, inner=inner):
                mutated = copy.deepcopy(self.fixture)
                if outer == "validation":
                    del mutated[outer][inner]
                else:
                    mutated[outer][inner] = value
                with self.assertRaises(jsonschema.ValidationError):
                    self.validate(mutated)

    def test_missing_state_or_failed_objective_is_rejected_semantically(self) -> None:
        missing = copy.deepcopy(self.fixture)
        missing["stateResults"].pop()
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(missing)

        over_rpo = copy.deepcopy(self.fixture)
        result = over_rpo["stateResults"][2]
        result["lossSeconds"] = result["rpoSeconds"] + 1
        with self.assertRaises(AssertionError):
            self.validate_semantics(over_rpo)

    def test_unknown_fields_and_mutable_references_are_rejected(self) -> None:
        unknown = copy.deepcopy(self.fixture)
        unknown["isolation"]["bestEffort"] = True
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(unknown)

        mutable = copy.deepcopy(self.fixture)
        mutable["source"]["reference"] = "ghcr.io/clavenar/backups:latest"
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(mutable)


if __name__ == "__main__":
    unittest.main()
