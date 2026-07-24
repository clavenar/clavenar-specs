import copy
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts" / "deployment-promotion-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts" / "deployment-promotion-v1.fixture.json").read_text()
)


class DeploymentPromotionContractTest(unittest.TestCase):
    def test_fixture_validates(self) -> None:
        jsonschema.Draft202012Validator(SCHEMA).validate(FIXTURE)

    def test_promoted_terminal_requires_both_candidate_gates(self) -> None:
        for gate in ("completeReadiness", "representativeTransaction"):
            mutated = copy.deepcopy(FIXTURE)
            mutated["gates"]["candidate"][gate] = False
            with self.assertRaises(jsonschema.ValidationError):
                jsonschema.Draft202012Validator(SCHEMA).validate(mutated)

    def test_rollback_terminal_requires_both_rollback_gates(self) -> None:
        mutated = copy.deepcopy(FIXTURE)
        mutated["status"] = "rolled_back"
        mutated["publicPointer"] = {
            "before": "1.196.0",
            "after": "1.196.0",
            "confirmed": False,
        }
        mutated["gates"]["rollback"] = {
            "completeReadiness": True,
            "representativeTransaction": True,
        }
        jsonschema.Draft202012Validator(SCHEMA).validate(mutated)
        mutated["gates"]["rollback"]["completeReadiness"] = False
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(SCHEMA).validate(mutated)

    def test_mutable_release_and_local_build_fallback_fail(self) -> None:
        mutated = copy.deepcopy(FIXTURE)
        mutated["candidate"]["releaseReference"] = "clavenar:latest"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(SCHEMA).validate(mutated)
        mutated = copy.deepcopy(FIXTURE)
        mutated["localBuildFallback"] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(SCHEMA).validate(mutated)


if __name__ == "__main__":
    unittest.main()
