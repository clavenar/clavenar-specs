import copy
import hashlib
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "contracts" / "residual-product-disposition-v1.fixture.json"
SCHEMA = ROOT / "contracts" / "residual-product-disposition-v1.schema.json"
SANDBOX_CORPUS = (
    ROOT.parent / "clavenar-sandbox" / "benchmark" / "adversarial-cases.json"
)


class ResidualProductDispositionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    def validate(self, value: dict) -> None:
        jsonschema.Draft202012Validator(self.schema).validate(value)

    def validate_semantics(self, value: dict) -> None:
        self.validate(value)
        expected_ids = {
            "per-tenant-notification-channel-selection",
            "hil-transition-webauthn-signatures",
            "high-impact-webauthn-step-up",
            "multi-replica-policy-rule-consistency",
            "cli-policy-crud-parity",
            "real-provider-deep-review-benchmark",
            "sandbox-severity-adversarial-corpus",
            "biometric-mobile-push-approval",
            "hard-gated-approver-group-routing",
        }
        self.assertEqual(expected_ids, {row["id"] for row in value["dispositions"]})
        shipped = [row for row in value["dispositions"] if row["status"] == "shipped"]
        deferred = [
            row for row in value["dispositions"] if row["status"] == "deferred"
        ]
        self.assertEqual(value["shippedCount"], len(shipped))
        self.assertEqual(value["deferredCount"], len(deferred))
        self.assertEqual(
            ["sandbox-severity-adversarial-corpus"],
            [row["id"] for row in shipped],
        )
        self.assertTrue(all(row["evidence"] for row in shipped))
        self.assertTrue(all(not row["evidence"] for row in deferred))
        self.assertTrue(all(row["promotionRequirements"] for row in deferred))

    def test_fixture_is_exact_and_deny_unknown(self) -> None:
        self.validate_semantics(self.fixture)
        unknown = copy.deepcopy(self.fixture)
        unknown["dispositions"][0]["bestEffort"] = True
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(unknown)

    def test_missing_or_substituted_disposition_is_rejected(self) -> None:
        missing = copy.deepcopy(self.fixture)
        missing["dispositions"].pop()
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(missing)

        substituted = copy.deepcopy(self.fixture)
        substituted["dispositions"][0]["id"] = "global-notification-lifecycle"
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(substituted)

    def test_deferred_claim_cannot_carry_shipped_evidence(self) -> None:
        value = copy.deepcopy(self.fixture)
        value["dispositions"][0]["evidence"] = copy.deepcopy(
            value["dispositions"][6]["evidence"]
        )
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(value)

    def test_shipped_claim_requires_evidence_and_no_promotion_work(self) -> None:
        without_evidence = copy.deepcopy(self.fixture)
        without_evidence["dispositions"][6]["evidence"] = []
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(without_evidence)

        with_promotion = copy.deepcopy(self.fixture)
        with_promotion["dispositions"][6]["promotionRequirements"] = ["more work"]
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(with_promotion)

    def test_sandbox_binding_matches_reviewed_corpus(self) -> None:
        binding = self.fixture["bindings"]["sandboxAdversarialCorpus"]
        self.assertTrue(SANDBOX_CORPUS.is_file())
        self.assertEqual(
            binding["sha256"],
            hashlib.sha256(SANDBOX_CORPUS.read_bytes()).hexdigest(),
        )
        corpus = json.loads(SANDBOX_CORPUS.read_text(encoding="utf-8"))
        self.assertEqual(binding["contract"], corpus["contract"])
        self.assertEqual(binding["caseCount"], len(corpus["cases"]))
        self.assertEqual(
            {
                "staticAnnotationOnly": True,
                "authorizationBoundary": False,
                "executionIsolation": False,
                "tenantAuthorityEnforcedByAnalyzer": False,
            },
            corpus["scope"],
        )


if __name__ == "__main__":
    unittest.main()
