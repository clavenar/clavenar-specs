import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
SCHEMA = json.loads(
    (CONTRACTS / "repository-documentation-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (CONTRACTS / "repository-documentation-v1.fixture.json").read_text()
)


class RepositoryDocumentationContractTests(unittest.TestCase):
    def test_fixture_validates_and_totals_are_exact(self) -> None:
        jsonschema.Draft202012Validator(SCHEMA).validate(FIXTURE)
        self.assertEqual(FIXTURE["release"], "1.237.0")
        self.assertEqual(
            FIXTURE["totals"],
            {
                "repositories": 30,
                "publicRepositories": 29,
                "restrictedRepositories": 1,
                "markdownFiles": 265,
                "workspaceInputs": 2,
                "checks": 9,
                "claimStates": 4,
                "corrections": 10,
                "governedServices": 9,
            },
        )

    def test_repository_inventory_is_unique_sorted_and_complete(self) -> None:
        repositories = FIXTURE["repositories"]
        names = [item["name"] for item in repositories]
        self.assertEqual(names, sorted(names))
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(names), 30)
        self.assertEqual(
            sum(item["markdownFiles"] for item in repositories),
            265,
        )
        self.assertEqual(
            [item["name"] for item in repositories if item["visibility"] == "restricted"],
            ["clavenar-internal-specs"],
        )

    def test_checks_claim_states_and_services_are_exact(self) -> None:
        self.assertEqual(
            FIXTURE["claimStates"],
            [
                "source-shipped",
                "release-verified",
                "deployed-verified",
                "external-verified",
            ],
        )
        self.assertEqual(
            set(FIXTURE["serviceInventory"]),
            {
                "proxy",
                "brain",
                "policy-engine",
                "ledger",
                "hil",
                "identity",
                "deep-review",
                "assurance",
                "console",
            },
        )
        self.assertEqual(len(FIXTURE["checks"]), 9)

    def test_correction_groups_are_exact_and_unique(self) -> None:
        correction_ids = [item["id"] for item in FIXTURE["corrections"]]
        self.assertEqual(len(correction_ids), len(set(correction_ids)))
        self.assertEqual(
            set(correction_ids),
            {
                "portable-workspace-roots",
                "private-outreach-inputs",
                "policy-template-targets",
                "governed-service-count",
                "optional-bundled-dependencies",
                "lite-human-review",
                "source-live-evidence-states",
                "deep-review-follow-up-reference",
                "strategy-playbook-references",
                "portable-demo-operations",
            },
        )


if __name__ == "__main__":
    unittest.main()
