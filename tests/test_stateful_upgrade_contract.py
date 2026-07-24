import copy
from datetime import datetime
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts" / "stateful-upgrade-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts" / "stateful-upgrade-v1.fixture.json").read_text()
)
SERVICES = {"ledger", "hil", "identity", "policy-engine", "proxy"}
FUNCTIONAL = {
    "ledger": "chain-valid",
    "hil": "pending-and-decision-retained",
    "identity": "agent-and-credential-retained",
    "policy-engine": "active-version-and-history-retained",
    "proxy": "execution-intent-result-retained",
}


def validate_semantics(receipt: dict) -> None:
    jsonschema.Draft202012Validator(
        SCHEMA,
        format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
    ).validate(receipt)
    started = datetime.fromisoformat(receipt["startedAt"].replace("Z", "+00:00"))
    backed_up = datetime.fromisoformat(
        receipt["backup"]["createdAt"].replace("Z", "+00:00")
    )
    finished = datetime.fromisoformat(receipt["finishedAt"].replace("Z", "+00:00"))
    if not started <= backed_up <= finished:
        raise ValueError("backup must occur inside the upgrade operation")
    if receipt["sourceRelease"]["version"] == receipt["targetRelease"]["version"]:
        raise ValueError("source and target releases must be distinct")
    if receipt["backup"]["sourceVersion"] != receipt["sourceRelease"]["version"]:
        raise ValueError("backup source release mismatch")
    if receipt["backup"]["targetVersion"] != receipt["targetRelease"]["version"]:
        raise ValueError("backup target release mismatch")

    workloads = {row["service"]: row for row in receipt["workloads"]}
    backups = {row["service"]: row for row in receipt["backup"]["workloads"]}
    if set(workloads) != SERVICES or set(backups) != SERVICES:
        raise ValueError("upgrade workload inventory is incomplete")
    if len(receipt["workloads"]) != len(workloads):
        raise ValueError("upgrade workload inventory contains duplicates")
    if len(receipt["backup"]["workloads"]) != len(backups):
        raise ValueError("backup workload inventory contains duplicates")
    if len({row["pvcUid"] for row in workloads.values()}) != len(SERVICES):
        raise ValueError("PVC identity must be unique per workload")
    for service, row in workloads.items():
        if row["functionalVerification"] != FUNCTIONAL[service]:
            raise ValueError(f"{service} functional verification mismatch")
        if not (
            row["mutatedStateSha256"]
            == row["afterUpgradeStateSha256"]
            == row["afterRollbackStateSha256"]
        ):
            raise ValueError(f"{service} state commitment changed")
        if row["recordsBefore"] != row["recordsAfterRollback"]:
            raise ValueError(f"{service} record count changed")


class StatefulUpgradeContractTests(unittest.TestCase):
    def test_fixture_validates(self) -> None:
        validate_semantics(FIXTURE)

    def test_every_sqlite_workload_is_exactly_covered(self) -> None:
        self.assertEqual(SERVICES, {row["service"] for row in FIXTURE["workloads"]})
        self.assertTrue(
            all(row["rolloutStrategy"] == "Recreate" for row in FIXTURE["workloads"])
        )
        self.assertTrue(
            all(
                row["schema"]["rollbackMode"] == "verified-backup-restore"
                for row in FIXTURE["workloads"]
            )
        )

    def test_overlapping_writer_or_unverified_backup_is_rejected(self) -> None:
        mutations = [
            ("maximumObservedApplicationWriters", 2),
            ("backup", "verification", "unchecked-copy"),
            ("faults", "failedScheduling", "overlappingWritersObserved", 1),
            ("rollback", "backupRestored", False),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                receipt = copy.deepcopy(FIXTURE)
                target = receipt
                for key in mutation[:-2]:
                    target = target[key]
                target[mutation[-2]] = mutation[-1]
                with self.assertRaises(jsonschema.ValidationError):
                    validate_semantics(receipt)

    def test_missing_workload_or_changed_state_is_rejected_semantically(self) -> None:
        missing = copy.deepcopy(FIXTURE)
        missing["workloads"].pop()
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(missing)

        changed = copy.deepcopy(FIXTURE)
        changed["workloads"][0]["afterRollbackStateSha256"] = (
            "sha256:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        )
        with self.assertRaises(ValueError):
            validate_semantics(changed)

    def test_phase_reordering_and_unknown_fields_are_rejected(self) -> None:
        reordered = copy.deepcopy(FIXTURE)
        reordered["phaseSequence"][3], reordered["phaseSequence"][4] = (
            reordered["phaseSequence"][4],
            reordered["phaseSequence"][3],
        )
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(reordered)

        unknown = copy.deepcopy(FIXTURE)
        unknown["bestEffort"] = True
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(unknown)


if __name__ == "__main__":
    unittest.main()
