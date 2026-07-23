import copy
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "contracts" / "backup-set-manifest-v1.fixture.json"
SCHEMA = ROOT / "contracts" / "backup-set-manifest-v1.schema.json"
INVENTORY = ROOT / "contracts" / "state-recovery-inventory-v1.fixture.json"

CAPTURED = {
    "application-secrets",
    "attestation-authority",
    "broker-jetstream",
    "caddy-acme-state",
    "hil-decisions",
    "identity-authority",
    "ledger-evidence",
    "observability-state",
    "policy-governance",
    "proxy-execution",
    "vault-key-metadata",
    "vault-recovery-material",
    "workload-pki-authority",
    "workload-trust-history",
}


class BackupSetManifestContractTests(unittest.TestCase):
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

    def test_fixture_validates(self) -> None:
        self.validate(self.fixture)
        self.assertEqual("pass", self.fixture["result"])

    def test_complete_inventory_partition(self) -> None:
        coverage = self.fixture["coverage"]
        groups = [
            set(coverage["capturedStateIds"]),
            set(coverage["externalCustodyStateIds"]),
            set(coverage["reconstructibleStateIds"]),
            set(coverage["signedSourceStateIds"]),
        ]
        self.assertEqual(CAPTURED, groups[0])
        for index, group in enumerate(groups):
            for other in groups[index + 1 :]:
                self.assertFalse(group & other)
        self.assertEqual(
            {state["id"] for state in self.inventory["states"]},
            set().union(*groups),
        )

    def test_capture_rows_cover_each_captured_state_once(self) -> None:
        states = [
            state_id
            for capture in self.fixture["captures"]
            for state_id in capture["stateIds"]
        ]
        self.assertEqual(CAPTURED, set(states))
        self.assertEqual(len(states), len(set(states)))

    def test_reconstructible_private_identities_are_not_captured(self) -> None:
        captured = self.fixture["coverage"]["capturedStateIds"]
        self.assertNotIn("workload-current-identities", captured)
        self.assertNotIn("simulator-agent-identities", captured)

    def test_plaintext_or_unverified_upload_is_rejected(self) -> None:
        for field in ("plaintextUploaded", "verified"):
            mutated = copy.deepcopy(self.fixture)
            mutated["encryption"][field] = not mutated["encryption"][field]
            with self.assertRaises(jsonschema.ValidationError):
                self.validate(mutated)

    def test_mutable_offsite_reference_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.fixture)
        mutated["offsite"]["reference"] = (
            "ghcr.io/clavenar/clavenar-prod-backups:latest"
        )
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(mutated)

    def test_failure_counters_are_rejected(self) -> None:
        mutated = copy.deepcopy(self.fixture)
        mutated["metrics"]["uploadFailures"] = 1
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(mutated)

    def test_future_claims_remain_withheld(self) -> None:
        self.assertEqual(
            {"isolated-restore", "disaster-recovery", "upgrade-safety"},
            set(self.fixture["doesNotAssert"]),
        )
        mutated = copy.deepcopy(self.fixture)
        mutated["doesNotAssert"] = ["disaster-recovery", "upgrade-safety"]
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(mutated)

    def test_unknown_fields_are_rejected(self) -> None:
        mutated = copy.deepcopy(self.fixture)
        mutated["offsite"]["bestEffort"] = True
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(mutated)


if __name__ == "__main__":
    unittest.main()
