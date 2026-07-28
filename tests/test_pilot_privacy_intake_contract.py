import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
SCHEMA = json.loads((CONTRACTS / "pilot-privacy-intake-v1.schema.json").read_text())
FIXTURE = json.loads((CONTRACTS / "pilot-privacy-intake-v1.fixture.json").read_text())


class PilotPrivacyIntakeContractTests(unittest.TestCase):
    def test_fixture_validates_and_totals_are_exact(self) -> None:
        jsonschema.Draft202012Validator(
            SCHEMA,
            format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
        ).validate(FIXTURE)
        self.assertEqual(FIXTURE["release"], "1.242.0")
        self.assertEqual(
            FIXTURE["totals"],
            {
                "forms": 2,
                "deliveredFields": 7,
                "freeTextFields": 0,
                "transientControlFields": 2,
                "prohibitedContentClasses": 6,
                "processors": 4,
            },
        )

    def test_forms_are_disjoint_enum_only_and_have_no_free_text(self) -> None:
        forms = FIXTURE["intake"]["forms"]
        self.assertEqual([form["kind"] for form in forms], ["pilot", "design_partner"])
        self.assertEqual(forms[0]["deliveredFields"], ["kind", "email", "evaluation_stage"])
        self.assertEqual(
            forms[1]["deliveredFields"],
            ["kind", "email", "interest", "contact_timing"],
        )
        self.assertEqual(FIXTURE["totals"]["freeTextFields"], 0)
        self.assertEqual(FIXTURE["intake"]["unknownFields"], "reject")
        self.assertNotIn("notes", json.dumps(FIXTURE["intake"]))
        self.assertNotIn("production-infra", json.dumps(FIXTURE["intake"]))

    def test_retention_and_deletion_are_bounded(self) -> None:
        self.assertEqual(
            FIXTURE["retention"],
            {
                "inactiveInquiryDays": 90,
                "absoluteIntakeDays": 180,
                "conversionDeletionDays": 30,
                "securityLogDays": 30,
                "rateLimitSeconds": 60,
                "turnstileTokenHashSeconds": 300,
            },
        )
        self.assertEqual(FIXTURE["deletion"]["requestAcknowledgementDays"], 7)
        self.assertEqual(FIXTURE["deletion"]["requestCompletionDays"], 30)

    def test_processor_inventory_is_complete_sorted_and_review_bounded(self) -> None:
        inventory = FIXTURE["processorInventory"]
        processors = inventory["processors"]
        ids = [processor["id"] for processor in processors]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(inventory["reviewCadenceDays"], 90)
        self.assertEqual(inventory["nextReviewBy"], "2026-10-26")
        self.assertEqual(
            {processor["status"] for processor in processors},
            {"active", "disabled"},
        )

    def test_security_tokens_are_never_delivered(self) -> None:
        delivered = {
            field
            for form in FIXTURE["intake"]["forms"]
            for field in form["deliveredFields"]
        }
        self.assertTrue(
            set(FIXTURE["intake"]["transientControlFields"]).isdisjoint(delivered)
        )


if __name__ == "__main__":
    unittest.main()
