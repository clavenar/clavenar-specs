import copy
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
SCHEMA = json.loads(
    (CONTRACTS / "brain-provider-routing-v2.schema.json").read_text()
)
FIXTURE = json.loads(
    (CONTRACTS / "brain-provider-routing-v2.fixture.json").read_text()
)


class BrainProviderRoutingContractTests(unittest.TestCase):
    def validate(self, value: dict) -> None:
        jsonschema.Draft202012Validator(
            SCHEMA,
            format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
        ).validate(value)

        credentials = value["credentials"]
        providers = value["providers"]
        models = value["models"]
        assignments = [
            value["workloads"]["classifier"]["fast"],
            value["workloads"]["classifier"]["deep"],
            *(
                assignment
                for name, assignment in value["workloads"].items()
                if name != "classifier"
            ),
        ]

        for provider in providers.values():
            self.assertIn(provider["credential"], credentials)
        for model in models.values():
            self.assertIn(model["provider"], providers)
        for assignment in assignments:
            self.assertIn(assignment["primary"], models)
            for fallback in assignment["fallback"]["models"]:
                self.assertIn(fallback, models)
                self.assertNotEqual(assignment["primary"], fallback)

        expected_sources = {
            "anthropic": "environment",
            "openai": "environment",
            "google": "environment",
            "bedrock": "aws_default_chain",
            "vertex": "google_application_default",
            "ollama": "none",
        }
        for provider in providers.values():
            source = credentials[provider["credential"]]["source"]
            self.assertEqual(expected_sources[provider["kind"]], source)

    def test_fixture_is_strict_complete_and_secret_free(self) -> None:
        self.validate(FIXTURE)
        self.assertEqual(
            {"anthropic", "openai", "google", "bedrock", "vertex", "ollama"},
            {provider["kind"] for provider in FIXTURE["providers"].values()},
        )
        serialized = json.dumps(FIXTURE).lower()
        for forbidden in ("api_key_value", "secret_value", "bearer_token"):
            self.assertNotIn(forbidden, serialized)

    def test_inline_secret_or_unscoped_environment_reference_is_rejected(self) -> None:
        inline = copy.deepcopy(FIXTURE)
        inline["credentials"]["anthropic-key"]["value"] = "not-allowed"
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(inline)

        unscoped = copy.deepcopy(FIXTURE)
        unscoped["credentials"]["anthropic-key"]["variable"] = "ANTHROPIC_API_KEY"
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(unscoped)

        malformed_scoped = copy.deepcopy(FIXTURE)
        malformed_scoped["credentials"]["anthropic-key"]["variable"] = (
            "CLAVENAR_BRAIN__BAD"
        )
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(malformed_scoped)

    def test_fallback_policy_is_explicit_and_bounded(self) -> None:
        disabled_with_target = copy.deepcopy(FIXTURE)
        disabled_with_target["workloads"]["pii"]["fallback"]["models"] = [
            "openai-fast"
        ]
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(disabled_with_target)

        transient_without_target = copy.deepcopy(FIXTURE)
        transient_without_target["workloads"]["pii"]["fallback"] = {
            "policy": "transient_only",
            "models": [],
        }
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(transient_without_target)

        too_many = copy.deepcopy(FIXTURE)
        too_many["workloads"]["pii"]["fallback"] = {
            "policy": "transient_only",
            "models": ["openai-fast", "google-fast", "ollama-fast"],
        }
        with self.assertRaises(jsonschema.ValidationError):
            self.validate(too_many)

    def test_dangling_references_and_wrong_credential_sources_fail(self) -> None:
        for mutate in (
            lambda item: item["providers"]["anthropic-primary"].update(
                credential="missing"
            ),
            lambda item: item["models"]["anthropic-fast"].update(
                provider="missing"
            ),
            lambda item: item["workloads"]["pii"].update(primary="missing"),
            lambda item: item["providers"]["ollama-local"].update(
                credential="anthropic-key"
            ),
        ):
            candidate = copy.deepcopy(FIXTURE)
            mutate(candidate)
            with self.subTest(candidate=candidate):
                with self.assertRaises(AssertionError):
                    self.validate(candidate)


if __name__ == "__main__":
    unittest.main()
