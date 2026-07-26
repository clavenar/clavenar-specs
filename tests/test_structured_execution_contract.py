import copy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts/structured-execution-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts/structured-execution-v1.fixture.json").read_text()
)


def test_structured_execution_fixture_is_strict():
    jsonschema.Draft7Validator(SCHEMA).validate(FIXTURE)


@pytest.mark.parametrize(
    ("pointer", "value"),
    [
        (("tool", "name"), "bash"),
        (("commands", 0, "executable"), "bash"),
        (("process", "shell"), True),
        (("process", "pathLookup"), True),
        (("process", "inheritEnvironment"), True),
        (("isolation", "runAsUser"), 0),
        (("isolation", "rootFilesystem"), "writable"),
        (("isolation", "egress", "defaultDeny"), False),
        (("production", "optInAllowed"), True),
    ],
)
def test_structured_execution_rejects_weakened_contract(pointer, value):
    candidate = copy.deepcopy(FIXTURE)
    target = candidate
    for segment in pointer[:-1]:
        target = target[segment]
    target[pointer[-1]] = value
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(SCHEMA).validate(candidate)


def test_structured_execution_rejects_extra_fields():
    candidate = copy.deepcopy(FIXTURE)
    candidate["commands"][0]["environment"]["allowed"]["LD_PRELOAD"] = ["x"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(SCHEMA).validate(candidate)
