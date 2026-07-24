import copy
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "contracts" / "passive-recovery-v1.fixture.json"
SCHEMA = ROOT / "contracts" / "passive-recovery-v1.schema.json"


class PassiveRecoveryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def validate(self, value: dict) -> None:
        jsonschema.Draft202012Validator(
            self.schema,
            format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
        ).validate(value)

    def validate_semantics(self, value: dict) -> None:
        self.validate(value)
        fence = value["fence"]
        transitions = fence["transitions"]
        self.assertEqual(
            ["demote", "promote", "demote", "promote"],
            [row["action"] for row in transitions],
        )
        self.assertEqual(
            list(range(fence["initialGeneration"] + 1, fence["initialGeneration"] + 5)),
            [row["generation"] for row in transitions],
        )
        self.assertEqual(
            fence["finalGeneration"],
            transitions[-1]["generation"],
        )
        primary = fence["initialHostId"]
        passive = fence["passiveHostId"]
        self.assertEqual(
            [
                (None, primary),
                (passive, primary),
                (None, passive),
                (primary, passive),
            ],
            [
                (row["activeHostId"], row["previousHostId"])
                for row in transitions
            ],
        )
        for phase in ("failover", "failback"):
            self.assertLessEqual(value[phase]["sourceAgeSeconds"], 300)
            self.assertLessEqual(value[phase]["lossWindowSeconds"], 300)
            self.assertLessEqual(value[phase]["restoreDurationSeconds"], 1800)
        continuity = value["failback"]["continuity"]
        self.assertGreater(
            continuity["passiveLedgerRowsAfter"],
            continuity["passiveLedgerRowsBefore"],
        )
        self.assertGreaterEqual(
            continuity["primaryLedgerRowsBefore"],
            continuity["passiveLedgerRowsAfter"],
        )
        self.assertGreater(
            continuity["primaryLedgerRowsAfter"],
            continuity["primaryLedgerRowsBefore"],
        )

    def test_fixture_validates_with_exact_cold_passive_posture(self) -> None:
        self.validate_semantics(self.fixture)
        self.assertFalse(self.fixture["topology"]["dnsIsFence"])
        self.assertFalse(self.fixture["topology"]["partitionedPromotionAllowed"])
        self.assertFalse(self.fixture["topology"]["activeActiveAllowed"])
        self.assertFalse(self.fixture["recovery"]["plaintextCopied"])
        self.assertTrue(self.fixture["fence"]["doublePromotionRefused"])

    def test_missing_transition_timer_or_continuity_is_rejected(self) -> None:
        mutations = []
        transition = copy.deepcopy(self.fixture)
        transition["fence"]["transitions"].pop()
        mutations.append(transition)
        extra_transition = copy.deepcopy(self.fixture)
        extra_transition["fence"]["transitions"].append(
            copy.deepcopy(extra_transition["fence"]["transitions"][-1])
        )
        mutations.append(extra_transition)
        timer = copy.deepcopy(self.fixture)
        timer["timers"]["passiveSyncActive"] = False
        mutations.append(timer)
        continuity = copy.deepcopy(self.fixture)
        del continuity["failback"]["continuity"]
        mutations.append(continuity)
        for value in mutations:
            with self.subTest(value=value):
                with self.assertRaises(jsonschema.ValidationError):
                    self.validate(value)

    def test_generation_host_objective_and_chain_regressions_fail_semantically(self) -> None:
        mutations = []
        generation = copy.deepcopy(self.fixture)
        generation["fence"]["transitions"][2]["generation"] = 9
        mutations.append(generation)
        host = copy.deepcopy(self.fixture)
        host["fence"]["transitions"][1]["activeHostId"] = "other"
        mutations.append(host)
        objective = copy.deepcopy(self.fixture)
        objective["failover"]["sourceAgeSeconds"] = 301
        mutations.append(objective)
        chain = copy.deepcopy(self.fixture)
        chain["failback"]["continuity"]["primaryLedgerRowsBefore"] = 1
        mutations.append(chain)
        for value in mutations:
            with self.subTest(value=value):
                with self.assertRaises(AssertionError):
                    self.validate_semantics(value)

    def test_unknown_fields_mutable_objects_and_partial_state_are_rejected(self) -> None:
        unknown = copy.deepcopy(self.fixture)
        unknown["fence"]["bestEffort"] = True
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(unknown)

        mutable = copy.deepcopy(self.fixture)
        mutable["failover"]["backupObject"] = "ghcr.io/clavenar/backups:latest"
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(mutable)

        partial = copy.deepcopy(self.fixture)
        partial["recovery"]["stateCount"] = 19
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(partial)


if __name__ == "__main__":
    unittest.main()
