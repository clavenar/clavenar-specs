import copy
import hashlib
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "contracts" / "supported-failure-model-v1.fixture.json"
SCHEMA = ROOT / "contracts" / "supported-failure-model-v1.schema.json"


class SupportedFailureModelContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def validate(self, value: dict) -> None:
        jsonschema.Draft202012Validator(self.schema).validate(value)

    def validate_semantics(self, value: dict) -> None:
        self.validate(value)
        self.assertEqual(
            {
                "compose-cold-active-passive",
                "helm-single-writer",
                "staged-postgres-ledger",
            },
            {row["id"] for row in value["topologies"]},
        )
        self.assertEqual(
            {
                "primary-host-loss",
                "network-partition",
                "stale-recovery-point",
                "wrong-release-recovery-point",
                "partial-or-substituted-recovery-point",
                "writer-fence-authority-loss",
                "ledger-process-loss",
                "ledger-sqlite-store-loss",
                "postgres-loss",
                "identity-loss",
                "hil-loss",
                "policy-loss",
                "proxy-execution-state-loss",
                "nats-jetstream-loss",
                "vault-loss",
                "workload-identity-loss",
                "operator-custody-loss",
            },
            {row["id"] for row in value["failureModes"]},
        )
        self.assertTrue(all(row["failClosed"] for row in value["failureModes"]))
        objectives = value["objectives"]
        self.assertGreater(
            objectives["configuredBackupIntervalSeconds"],
            objectives["criticalStateRpoObjectiveSeconds"],
        )
        self.assertFalse(objectives["configuredCadenceMeetsCriticalRpo"])
        self.assertFalse(objectives["passiveReverificationCreatesRecoveryPoint"])
        self.assertTrue(value["drillEvidence"]["evidenceOnly"])
        self.assertFalse(value["drillEvidence"]["guaranteedSlo"])

    def test_fixture_is_exact_and_deny_unknown(self) -> None:
        self.validate_semantics(self.fixture)
        self.assertEqual(6, len(self.fixture["nonClaims"]))

        unknown = copy.deepcopy(self.fixture)
        unknown["objectives"]["bestEffortHa"] = True
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(unknown)

    def test_objective_cadence_and_timer_conflation_are_rejected(self) -> None:
        mutations = []
        cadence = copy.deepcopy(self.fixture)
        cadence["objectives"]["configuredCadenceMeetsCriticalRpo"] = True
        mutations.append(cadence)
        passive = copy.deepcopy(self.fixture)
        passive["objectives"]["passiveReverificationCreatesRecoveryPoint"] = True
        mutations.append(passive)
        guaranteed = copy.deepcopy(self.fixture)
        guaranteed["drillEvidence"]["guaranteedSlo"] = True
        mutations.append(guaranteed)
        for value in mutations:
            with self.subTest(value=value):
                with self.assertRaises(jsonschema.ValidationError):
                    self.validate(value)

    def test_missing_fence_failure_or_nonclaim_is_rejected(self) -> None:
        for field, row in (
            ("topologies", "compose-cold-active-passive"),
            ("failureModes", "network-partition"),
            ("nonClaims", "whole-stack-high-availability"),
        ):
            value = copy.deepcopy(self.fixture)
            value[field] = [
                item
                for item in value[field]
                if (item["id"] if isinstance(item, dict) else item) != row
            ]
            with self.subTest(field=field, row=row):
                with self.assertRaises(jsonschema.ValidationError):
                    self.validate(value)

    def test_bindings_match_public_contracts(self) -> None:
        bindings = self.fixture["bindings"]["postgresLedgerTopology"]
        for name, field in (
            ("postgres-ledger-topology-v1.schema.json", "schemaSha256"),
            ("postgres-ledger-topology-v1.fixture.json", "fixtureSha256"),
        ):
            digest = hashlib.sha256((ROOT / "contracts" / name).read_bytes()).hexdigest()
            self.assertEqual(bindings[field], digest)


if __name__ == "__main__":
    unittest.main()
