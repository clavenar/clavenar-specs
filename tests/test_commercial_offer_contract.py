from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
NAMES = (
    "commercial-offer-v1.fixture.json",
    "commercial-offer-v1.schema.json",
)


class CommercialOfferContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = json.loads(
            (ROOT / "contracts" / NAMES[0]).read_text(encoding="utf-8")
        )
        self.schema = json.loads(
            (ROOT / "contracts" / NAMES[1]).read_text(encoding="utf-8")
        )

    def test_exact_offer_is_valid(self) -> None:
        jsonschema.Draft202012Validator.check_schema(self.schema)
        jsonschema.Draft202012Validator(self.schema).validate(self.fixture)
        self.assertEqual("1.245.0", self.fixture["release"])
        self.assertEqual(4, self.fixture["evaluation"]["durationWeeks"])
        self.assertEqual(15000, self.fixture["conversion"]["firstYearFeeUsd"])
        self.assertEqual(36000, self.fixture["renewal"]["annualListFeeUsd"])
        self.assertEqual(0, self.fixture["totals"]["publicFinancialAmounts"])

    def test_schema_rejects_weakened_or_conflicting_terms(self) -> None:
        for path, value in (
            (("evaluation", "durationWeeks"), 2),
            (("evaluation", "productionAuthorization"), True),
            (("conversion", "firstYearFeeUsd"), 0),
            (("conversion", "billingUnit"), "per-cluster"),
            (("renewal", "lifetimePriceLock"), True),
            (("publicity", "required"), True),
            (
                ("validationPolicy", "sourceCompletenessCountsAsEvidence"),
                True,
            ),
        ):
            candidate = copy.deepcopy(self.fixture)
            target = candidate
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.subTest(path=path):
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.Draft202012Validator(self.schema).validate(
                        candidate
                    )

    def test_public_and_deployment_mirrors_are_exact(self) -> None:
        for name in NAMES:
            expected = (ROOT / "contracts" / name).read_bytes()
            self.assertEqual(
                (
                    WORKSPACE / "clavenar-e2e" / "contracts" / name
                ).read_bytes(),
                expected,
            )
            self.assertEqual(
                (
                    WORKSPACE
                    / "clavenar-website"
                    / "public"
                    / "schemas"
                    / name
                ).read_bytes(),
                expected,
            )


if __name__ == "__main__":
    unittest.main()
