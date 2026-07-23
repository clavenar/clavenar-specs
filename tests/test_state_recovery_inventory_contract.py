import copy
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "contracts" / "state-recovery-inventory-v1.fixture.json"
SCHEMA = ROOT / "contracts" / "state-recovery-inventory-v1.schema.json"

EXPECTED_STATES = {
    "application-secrets",
    "attestation-authority",
    "broker-jetstream",
    "caddy-acme-state",
    "hil-decisions",
    "identity-authority",
    "ledger-evidence",
    "observability-state",
    "operator-private-custody",
    "operator-public-trust",
    "policy-governance",
    "proxy-execution",
    "release-configuration",
    "simulator-agent-identities",
    "tsa-trust",
    "vault-key-metadata",
    "vault-recovery-material",
    "workload-current-identities",
    "workload-pki-authority",
    "workload-trust-history",
}


class StateRecoveryInventoryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE.read_text())
        cls.schema = json.loads(SCHEMA.read_text())

    def validate(self, value: dict) -> None:
        jsonschema.Draft202012Validator(self.schema).validate(value)

    def test_fixture_validates_and_scope_withholds_future_claims(self) -> None:
        self.validate(self.fixture)
        self.assertEqual(
            {
                "scheduled-backup",
                "isolated-restore",
                "disaster-recovery",
                "upgrade-safety",
            },
            set(self.fixture["approval"]["doesNotAssert"]),
        )
        self.assertEqual(
            "requirements-and-inventory-only", self.fixture["approval"]["scope"]
        )
        self.assertTrue(
            all(not topology["wholeStackHaClaim"] for topology in self.fixture["topologies"])
        )

    def test_state_profile_and_location_identifiers_are_unique(self) -> None:
        state_ids = [state["id"] for state in self.fixture["states"]]
        self.assertEqual(EXPECTED_STATES, set(state_ids))
        self.assertEqual(len(state_ids), len(set(state_ids)))

        locations = [
            (location["topology"], location["resource"])
            for state in self.fixture["states"]
            for location in state["locations"]
        ]
        self.assertEqual(len(locations), len(set(locations)))

        for profiles in self.fixture["profiles"].values():
            ids = [profile["id"] for profile in profiles]
            self.assertEqual(len(ids), len(set(ids)))

    def test_all_profile_references_are_closed_and_objectives_possible(self) -> None:
        profile_keys = {
            name: {profile["id"] for profile in profiles}
            for name, profiles in self.fixture["profiles"].items()
        }
        for state in self.fixture["states"]:
            self.assertIn(state["objectiveProfile"], profile_keys["objectives"])
            self.assertIn(state["consistencyProfile"], profile_keys["consistency"])
            self.assertIn(state["lifecycleProfile"], profile_keys["lifecycle"])
            self.assertIn(state["encryptionProfile"], profile_keys["encryption"])

        for objective in self.fixture["profiles"]["objectives"]:
            self.assertLessEqual(objective["rpoSeconds"], objective["rtoSeconds"])

    def test_lifecycle_is_bounded_and_encryption_custody_is_explicit(self) -> None:
        for lifecycle in self.fixture["profiles"]["lifecycle"]:
            self.assertLessEqual(
                lifecycle["minimumRetentionSeconds"],
                lifecycle["maximumRetentionSeconds"],
            )
            self.assertEqual(
                "extend-until-authorized-release", lifecycle["legalHold"]
            )
        encryption = {
            profile["id"]: profile
            for profile in self.fixture["profiles"]["encryption"]
        }
        for state in self.fixture["states"]:
            profile = encryption[state["encryptionProfile"]]
            self.assertTrue(profile["atRestRequired"])
            self.assertTrue(profile["keyCustodian"])
            if state["confidentiality"] == "secret":
                self.assertEqual("security-key-material", state["encryptionProfile"])
                self.assertTrue(profile["separateRecoveryCustody"])
                self.assertIn(
                    state["protection"]["disposition"],
                    {
                        "backup-required",
                        "reconstructible-no-private-key-backup",
                        "separate-custody-required",
                    },
                )

    def test_restore_graph_is_complete_acyclic_and_ordered(self) -> None:
        states = {state["id"]: state for state in self.fixture["states"]}
        for state_id, state in states.items():
            for dependency in state["restore"]["dependsOn"]:
                self.assertIn(dependency, states)
                self.assertNotEqual(state_id, dependency)
                self.assertLess(
                    states[dependency]["restore"]["order"], state["restore"]["order"]
                )

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(state_id: str) -> None:
            self.assertNotIn(state_id, visiting)
            if state_id in visited:
                return
            visiting.add(state_id)
            for dependency in states[state_id]["restore"]["dependsOn"]:
                visit(dependency)
            visiting.remove(state_id)
            visited.add(state_id)

        for state_id in states:
            visit(state_id)
        self.assertEqual(EXPECTED_STATES, visited)

    def test_protection_statuses_do_not_overclaim_delivery(self) -> None:
        for state in self.fixture["states"]:
            protection = state["protection"]
            self.assertIn(
                protection["backupStatus"],
                {
                    "available-signed-source",
                    "not-applicable-reconstructible",
                    "pending-wp-10.5",
                },
            )
            self.assertEqual("pending-wp-10.6", protection["restoreProofStatus"])
            self.assertEqual("pending-wp-10.7", protection["drStatus"])
            self.assertEqual("pending-wp-10.11", protection["upgradeSafetyStatus"])

    def test_schema_rejects_incomplete_or_overclaiming_rows(self) -> None:
        missing_custody = copy.deepcopy(self.fixture)
        del missing_custody["profiles"]["encryption"][0]["keyCustodian"]
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(missing_custody)

        unbounded = copy.deepcopy(self.fixture)
        unbounded["profiles"]["lifecycle"][0]["maximumRetentionSeconds"] = None
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(unbounded)

        delivered = copy.deepcopy(self.fixture)
        delivered["states"][1]["protection"]["backupStatus"] = "available"
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(delivered)

        unknown = copy.deepcopy(self.fixture)
        unknown["states"][0]["fallback"] = "best-effort"
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(unknown)


if __name__ == "__main__":
    unittest.main()
