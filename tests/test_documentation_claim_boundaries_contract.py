import copy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts/documentation-claim-boundaries-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts/documentation-claim-boundaries-v1.fixture.json").read_text()
)


def test_documentation_claim_boundaries_fixture_is_strict():
    jsonschema.Draft7Validator(SCHEMA).validate(FIXTURE)


@pytest.mark.parametrize(
    ("claim_id", "status"),
    [
        ("attestation", "designed"),
        ("approver-provenance", "caller-asserted"),
        ("signing", "universal"),
        ("admissibility", "guaranteed"),
        ("retention", "fixed-seven-years"),
        ("deployment", "source-implies-production"),
    ],
)
def test_documentation_claim_boundaries_reject_scope_weakening(claim_id, status):
    candidate = copy.deepcopy(FIXTURE)
    claim = next(item for item in candidate["claims"] if item["id"] == claim_id)
    claim["status"] = status
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(SCHEMA).validate(candidate)


@pytest.mark.parametrize(("gate", "value"), [("source", False), ("built", False), ("deployed", False)])
def test_documentation_claim_boundaries_require_every_release_surface(gate, value):
    candidate = copy.deepcopy(FIXTURE)
    candidate["gates"][gate] = value
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(SCHEMA).validate(candidate)


def test_documentation_claim_boundaries_reject_extra_fields():
    candidate = copy.deepcopy(FIXTURE)
    candidate["claims"][0]["marketingApproved"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(SCHEMA).validate(candidate)
