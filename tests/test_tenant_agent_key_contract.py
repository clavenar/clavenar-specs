import copy
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts" / "tenant-agent-key-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts" / "tenant-agent-key-v1.fixture.json").read_text()
)


def validate_semantics(vector: dict) -> None:
    jsonschema.Draft202012Validator(SCHEMA).validate(vector)
    identity = vector["vector"]
    if identity["agentKey"] != f"{identity['tenantId']}/{identity['agentId']}":
        raise ValueError("agentKey is not the canonical tenant/agent serialization")
    if vector["migration"]["legacyBareAgentId"] != identity["agentId"]:
        raise ValueError("legacy migration input does not name the typed agent")


class TenantAgentKeyContractTests(unittest.TestCase):
    def test_fixture_validates(self) -> None:
        validate_semantics(FIXTURE)

    def test_changed_or_bare_key_is_rejected(self) -> None:
        for key in ("support-bot_3", "globex/support-bot_3", "acme.corp/bot"):
            with self.subTest(key=key):
                changed = copy.deepcopy(FIXTURE)
                changed["vector"]["agentKey"] = key
                with self.assertRaises(
                    (jsonschema.ValidationError, ValueError)
                ):
                    validate_semantics(changed)

    def test_unsafe_ambiguous_and_overlong_labels_are_rejected(self) -> None:
        for field, value in (
            ("tenantId", ""),
            ("tenantId", "acme/corp"),
            ("agentId", "support bot"),
            ("agentId", "x" * 64),
            ("agentKey", "acme/bot/extra"),
        ):
            with self.subTest(field=field, value=value):
                changed = copy.deepcopy(FIXTURE)
                changed["vector"][field] = value
                with self.assertRaises(
                    (jsonschema.ValidationError, ValueError)
                ):
                    validate_semantics(changed)

    def test_migration_never_permits_bare_dual_write(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["migration"]["bareDualWriteAllowed"] = True
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)

    def test_unknown_fields_are_rejected(self) -> None:
        changed = copy.deepcopy(FIXTURE)
        changed["defaultTenant"] = "acme.corp"
        with self.assertRaises(jsonschema.ValidationError):
            validate_semantics(changed)


if __name__ == "__main__":
    unittest.main()
