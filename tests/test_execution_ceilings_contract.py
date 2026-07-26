import copy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts/execution-ceilings-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts/execution-ceilings-v1.fixture.json").read_text()
)


def test_execution_ceilings_fixture_is_strict():
    jsonschema.Draft7Validator(SCHEMA).validate(FIXTURE)


@pytest.mark.parametrize(
    ("pointer", "value"),
    [
        (("serverOwned", "callerOverrides"), True),
        (("serverOwned", "runtimeOverrides"), True),
        (("request", "jsonRpcBodyBytes"), 4194305),
        (("process", "wallClockMillis"), 30001),
        (("process", "cpuSeconds"), 11),
        (("process", "addressSpaceBytes"), 268435457),
        (("process", "processes"), 17),
        (("process", "fileSizeBytes"), 8388609),
        (("process", "openFiles"), 65),
        (("process", "processGroup"), "direct-child-only"),
        (("output", "stdoutBytes"), 262145),
        (("output", "drainAfterLimit"), False),
        (("tools", "fileContentBytes"), 8388609),
        (("tools", "fetchResponseBodyBytes"), 1048577),
        (("production", "optInAllowed"), True),
    ],
)
def test_execution_ceilings_reject_weakening(pointer, value):
    candidate = copy.deepcopy(FIXTURE)
    target = candidate
    for segment in pointer[:-1]:
        target = target[segment]
    target[pointer[-1]] = value
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(SCHEMA).validate(candidate)


def test_execution_ceilings_reject_extra_fields():
    candidate = copy.deepcopy(FIXTURE)
    candidate["process"]["callerTimeoutMillis"] = 1
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(SCHEMA).validate(candidate)
