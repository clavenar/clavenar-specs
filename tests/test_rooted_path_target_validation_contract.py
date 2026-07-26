import copy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts/rooted-path-target-validation-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts/rooted-path-target-validation-v1.fixture.json").read_text()
)


def test_rooted_path_target_fixture_is_strict():
    jsonschema.Draft7Validator(SCHEMA).validate(FIXTURE)


@pytest.mark.parametrize(
    ("pointer", "value"),
    [
        (("filesystem", "rootAuthority"), "canonical-path-string"),
        (("filesystem", "maximumPathBytes"), 8192),
        (("filesystem", "reopenResolvedPath"), True),
        (("filesystem", "createParents"), "create-dir-all"),
        (("targets", "credentialsAllowed"), True),
        (("targets", "fragmentsAllowed"), True),
        (("targets", "queryAuthority"), True),
        (("targets", "emptyAllowlist"), "allow"),
        (("targets", "invalidAllowlist"), "ignore"),
        (("targets", "redirects"), "follow"),
        (("production", "execIncluded"), True),
        (("production", "execOptInAllowed"), True),
    ],
)
def test_rooted_path_target_contract_rejects_weakening(pointer, value):
    candidate = copy.deepcopy(FIXTURE)
    target = candidate
    for segment in pointer[:-1]:
        target = target[segment]
    target[pointer[-1]] = value
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(SCHEMA).validate(candidate)


def test_rooted_path_target_contract_rejects_extra_fields():
    candidate = copy.deepcopy(FIXTURE)
    candidate["targets"]["callerDnsOverride"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(SCHEMA).validate(candidate)
