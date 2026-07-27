import copy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts/compliance-derivation-boundaries-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts/compliance-derivation-boundaries-v1.fixture.json").read_text()
)


def test_compliance_derivation_boundary_fixture_is_strict():
    jsonschema.Draft7Validator(SCHEMA).validate(FIXTURE)
    assert FIXTURE["release"] == "1.230.0"
    assert len(FIXTURE["configurationSources"]) == 3
    assert len(FIXTURE["degradedModes"]) == 5
    assert len(FIXTURE["failClosedModes"]) == 4
    assert len(FIXTURE["derivations"]) == 3


@pytest.mark.parametrize(
    ("collection", "identifier", "field", "value"),
    [
        ("degradedModes", "revocation-cache-degraded", "posture", "fail-open-silent"),
        (
            "failClosedModes",
            "delegation-jwks-cold-or-stale",
            "outcome",
            "accept advisory claims",
        ),
        (
            "derivations",
            "human-oversight",
            "satisfiedWhen",
            "Any approver-looking field exists.",
        ),
    ],
)
def test_compliance_derivation_boundary_rejects_weakened_posture(
    collection, identifier, field, value
):
    candidate = copy.deepcopy(FIXTURE)
    item = next(entry for entry in candidate[collection] if entry["id"] == identifier)
    item[field] = value
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(SCHEMA).validate(candidate)


@pytest.mark.parametrize(
    "gate",
    ["source", "assembled", "built", "deployed"],
)
def test_compliance_derivation_boundary_requires_every_gate(gate):
    candidate = copy.deepcopy(FIXTURE)
    candidate["gates"][gate] = False
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(SCHEMA).validate(candidate)


def test_compliance_derivation_boundary_rejects_extra_fields():
    candidate = copy.deepcopy(FIXTURE)
    candidate["certified"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(SCHEMA).validate(candidate)
