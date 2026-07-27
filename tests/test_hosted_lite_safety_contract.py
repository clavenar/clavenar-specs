import copy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts/hosted-lite-safety-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts/hosted-lite-safety-v1.fixture.json").read_text()
)


def test_hosted_lite_safety_fixture_is_strict():
    jsonschema.Draft7Validator(SCHEMA).validate(FIXTURE)


@pytest.mark.parametrize(
    ("pointer", "value"),
    [
        (("profiles", "hosted", "selection"), "implicit"),
        (("profiles", "hosted", "startupRefusal"), False),
        (("authentication", "minimumTokenBytes"), 31),
        (("authentication", "agentOperatorOverlap"), "allow"),
        (("authentication", "anonymousMcp"), True),
        (("authentication", "anonymousPendingRead"), True),
        (("authentication", "anonymousDecision"), True),
        (("posture", "mode"), "observe"),
        (("posture", "verboseVerdicts"), True),
        (("rateLimit", "required"), False),
        (("rateLimit", "maximumQps"), 101.0),
        (("rateLimit", "maximumBurst"), 201),
        (("rateLimit", "beforePipeline"), False),
        (("durability", "ledger"), "memory"),
        (("durability", "scaleToZero"), True),
        (("durability", "minimumMachines"), 0),
        (("adapter", "required"), False),
        (("adapter", "identifier"), "raw-http"),
        (("adapter", "upstreamScheme"), "http"),
        (("adapter", "responseId"), "ignore"),
        (("adapter", "responseBodyBytes"), 1048577),
        (("adapter", "wholeOperationMillis"), 30001),
        (("adapter", "automaticEffectRetries"), 1),
        (("hostedTemplate", "persistentVolume"), False),
        (("production", "execIncluded"), True),
        (("production", "execOptInAllowed"), True),
    ],
)
def test_hosted_lite_safety_rejects_weakening(pointer, value):
    candidate = copy.deepcopy(FIXTURE)
    target = candidate
    for segment in pointer[:-1]:
        target = target[segment]
    target[pointer[-1]] = value
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(SCHEMA).validate(candidate)


def test_hosted_lite_safety_rejects_extra_fields():
    candidate = copy.deepcopy(FIXTURE)
    candidate["hostedTemplate"]["docsOnly"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(SCHEMA).validate(candidate)
