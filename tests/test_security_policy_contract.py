import hashlib
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
SCHEMA = json.loads((CONTRACTS / "security-policy-v1.schema.json").read_text())
FIXTURE = json.loads((CONTRACTS / "security-policy-v1.fixture.json").read_text())


class SecurityPolicyContractTests(unittest.TestCase):
    def test_fixture_validates_and_totals_are_exact(self) -> None:
        jsonschema.Draft202012Validator(SCHEMA).validate(FIXTURE)
        self.assertEqual(FIXTURE["release"], "1.237.0")
        self.assertEqual(FIXTURE["policyVersion"], "1.0.0")
        self.assertEqual(
            FIXTURE["totals"],
            {
                "repositories": 30,
                "securityFiles": 30,
                "contacts": 1,
                "requiredSections": 8,
                "requiredMarkers": 12,
                "forbiddenMarkers": 7,
                "checks": 9,
                "responseTargets": 4,
            },
        )

    def test_repository_inventory_is_unique_sorted_and_complete(self) -> None:
        repositories = FIXTURE["repositories"]
        self.assertEqual(repositories, sorted(repositories))
        self.assertEqual(len(repositories), len(set(repositories)))
        self.assertEqual(len(repositories), 30)
        self.assertIn("clavenar-chaos-catalog", repositories)
        self.assertIn("clavenar-shared", repositories)

    def test_canonical_policy_digest_and_markers_are_exact(self) -> None:
        policy = (ROOT / "SECURITY.md").read_bytes()
        digest = f"sha256:{hashlib.sha256(policy).hexdigest()}"
        self.assertEqual(digest, FIXTURE["canonicalSha256"])
        text = policy.decode("utf-8")
        for section in FIXTURE["requiredSections"]:
            self.assertEqual(text.count(f"## {section}"), 1)
        for marker in FIXTURE["requiredMarkers"]:
            self.assertIn(marker, text)
        for marker in FIXTURE["forbiddenMarkers"]:
            self.assertNotIn(marker, text)

    def test_contact_and_response_targets_are_single_and_explicit(self) -> None:
        text = (ROOT / "SECURITY.md").read_text()
        self.assertEqual(text.count("**Canonical contact:**"), 1)
        self.assertIn(FIXTURE["contact"], text)
        for target in ("Within 72 hours", "Within 7 days", "every 14 days", "within 90 days"):
            self.assertIn(target, text)


if __name__ == "__main__":
    unittest.main()
