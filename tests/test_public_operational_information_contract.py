import copy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts/public-operational-information-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts/public-operational-information-v1.fixture.json").read_text()
)


def validate(candidate):
    jsonschema.Draft7Validator(SCHEMA).validate(candidate)


def test_public_operational_information_fixture_is_exact():
    validate(FIXTURE)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("policy", "mode"), "relaxed"),
        (("policy", "operationalProceduresLocation"), "public"),
        (("policy", "exceptionStatus"), "approved"),
        (("futureException", "status"), "approved"),
        (("futureException", "maximumValidityDays"), 365),
        (("gates", "built"), False),
    ],
)
def test_policy_rejects_a_weaker_boundary(path, value):
    candidate = copy.deepcopy(FIXTURE)
    target = candidate
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(jsonschema.ValidationError):
        validate(candidate)


def test_policy_rejects_a_missing_prohibited_class():
    candidate = copy.deepcopy(FIXTURE)
    candidate["prohibitedDeploymentSpecificClasses"].pop()
    with pytest.raises(jsonschema.ValidationError):
        validate(candidate)


def test_policy_rejects_a_missing_exception_field():
    candidate = copy.deepcopy(FIXTURE)
    candidate["futureException"]["requiredFields"].pop()
    with pytest.raises(jsonschema.ValidationError):
        validate(candidate)


def test_policy_rejects_extra_fields():
    candidate = copy.deepcopy(FIXTURE)
    candidate["policy"]["override"] = True
    with pytest.raises(jsonschema.ValidationError):
        validate(candidate)
