from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"


def load(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


POLICY_SCHEMA = load("brain-model-qualification-v1.schema.json")
POLICY = load("brain-model-qualification-v1.fixture.json")
RECEIPT_SCHEMA = load("brain-model-qualification-receipt-v1.schema.json")
RECEIPT = load("brain-model-qualification-receipt-v1.fixture.json")


def qualification_policy_sha256(policy: dict) -> str:
    thresholds = copy.deepcopy(policy["thresholds"])
    for key in (
        "schemaAdherenceMin",
        "modelEvidenceCoverageMin",
        "costTelemetryCoverageMin",
        "deterministicAccuracyMin",
        "overallAccuracyMin",
        "denyPrecisionMin",
        "denyRecallMin",
        "maxP95LatencyMs",
        "maxP99LatencyMs",
    ):
        thresholds[key] = float(thresholds[key])
    thresholds["categoryAccuracyMin"] = {
        key: float(value)
        for key, value in thresholds["categoryAccuracyMin"].items()
    }
    projection = {
        "contract": policy["contract"],
        "schemaVersion": policy["schemaVersion"],
        "corpus": policy["corpus"],
        "conformance": policy["conformance"],
        "thresholds": thresholds,
        "supportGate": {
            key: policy["supportGate"][key]
            for key in (
                "minimumQualifiedHostedProviders",
                "minimumQualifiedLocalProviders",
            )
        },
        "models": [
            {
                key: model[key]
                for key in (
                    "targetId",
                    "providerKind",
                    "providerClass",
                    "providerAlias",
                    "model",
                )
            }
            for model in policy["models"]
        ],
    }
    canonical = json.dumps(
        projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


class BrainModelQualificationContractTests(unittest.TestCase):
    def test_policy_and_noneligible_receipt_validate(self) -> None:
        jsonschema.Draft202012Validator.check_schema(POLICY_SCHEMA)
        jsonschema.Draft202012Validator.check_schema(RECEIPT_SCHEMA)
        formatter = jsonschema.Draft202012Validator.FORMAT_CHECKER
        jsonschema.Draft202012Validator(
            POLICY_SCHEMA, format_checker=formatter
        ).validate(POLICY)
        jsonschema.Draft202012Validator(
            RECEIPT_SCHEMA, format_checker=formatter
        ).validate(RECEIPT)

    def test_corpus_and_support_gate_are_derived_not_marketing_claims(self) -> None:
        corpus = POLICY["corpus"]
        self.assertEqual(corpus["totalCases"], sum(corpus["categoryCounts"].values()))
        self.assertLessEqual(corpus["deterministicCases"], corpus["totalCases"])

        qualified = [model for model in POLICY["models"] if model["status"] == "qualified"]
        hosted = {model["providerKind"] for model in qualified if model["providerClass"] == "hosted"}
        local = {model["providerKind"] for model in qualified if model["providerClass"] == "local"}
        gate = POLICY["supportGate"]
        self.assertEqual(gate["qualifiedHostedProviders"], len(hosted))
        self.assertEqual(gate["qualifiedLocalProviders"], len(local))
        self.assertEqual(
            gate["eligible"],
            len(hosted) >= gate["minimumQualifiedHostedProviders"]
            and len(local) >= gate["minimumQualifiedLocalProviders"],
        )
        self.assertFalse(gate["eligible"])
        self.assertTrue(all(model["status"] == "experimental" for model in POLICY["models"]))

    def test_provider_neutral_scenarios_are_complete_and_unique(self) -> None:
        expected = {
            "available_complete",
            "connection_unavailable",
            "authentication_rejected",
            "malformed_output",
            "refusal",
            "truncation",
            "post_dispatch_timeout",
            "rate_limited",
        }
        scenarios = POLICY["conformance"]["requiredScenarios"]
        self.assertEqual(expected, {scenario["id"] for scenario in scenarios})
        self.assertEqual(len(expected), len(scenarios))

    def test_schema_rejects_unreceipted_qualified_model(self) -> None:
        candidate = copy.deepcopy(POLICY)
        candidate["models"][0]["status"] = "qualified"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(POLICY_SCHEMA).validate(candidate)

    def test_receipt_rejects_mock_support_eligibility(self) -> None:
        candidate = copy.deepcopy(RECEIPT)
        candidate["result"] = "pass"
        candidate["eligibleForSupport"] = True
        candidate["violations"] = []
        candidate["runCount"] = 3
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(RECEIPT_SCHEMA).validate(candidate)

    def test_receipt_rejects_replayed_run_hashes(self) -> None:
        candidate = copy.deepcopy(RECEIPT)
        candidate["reportSha256"] = [
            candidate["reportSha256"][0],
            candidate["reportSha256"][0],
            candidate["reportSha256"][0],
        ]
        candidate["runCount"] = 3
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(RECEIPT_SCHEMA).validate(candidate)

    def test_policy_semantics_do_not_allow_relaxed_release_floor(self) -> None:
        candidate = copy.deepcopy(POLICY)
        candidate["thresholds"]["maxDegradedResponses"] = 1
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(POLICY_SCHEMA).validate(candidate)

    def test_policy_digest_excludes_only_receipt_derived_matrix_state(self) -> None:
        digest = qualification_policy_sha256(POLICY)
        self.assertEqual(
            "sha256:cd8f3218b415ad2d901a188089d1b8ca2b0efe3a80ca7bcc874798317e5f1c47",
            digest,
        )
        candidate = copy.deepcopy(POLICY)
        candidate["statusAsOf"] = "2026-08-11"
        candidate["models"][0].update(
            status="qualified",
            qualificationReceipt=(
                "receipts/brain-model-qualification/example.json"
            ),
            lastQualifiedAt="2026-08-11",
            statusReason="Passing receipt.",
        )
        candidate["supportGate"]["qualifiedHostedProviders"] = 1
        self.assertEqual(digest, qualification_policy_sha256(candidate))
        candidate["thresholds"]["overallAccuracyMin"] = 0.96
        self.assertNotEqual(digest, qualification_policy_sha256(candidate))


if __name__ == "__main__":
    unittest.main()
