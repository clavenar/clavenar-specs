import copy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts/outbound-resolution-pinning-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts/outbound-resolution-pinning-v1.fixture.json").read_text()
)


def test_outbound_resolution_pinning_fixture_is_strict():
    jsonschema.Draft7Validator(SCHEMA).validate(FIXTURE)


@pytest.mark.parametrize(
    ("pointer", "value"),
    [
        (("resolution", "answerSet"), "first-only"),
        (("resolution", "minimumAnswers"), 0),
        (("resolution", "maximumAnswers"), 33),
        (("resolution", "rejectWholeSetOnAnyNonPublicAnswer"), False),
        (("resolution", "selection"), "resolver-order"),
        (("resolution", "pinSelectedAddress"), False),
        (("resolution", "applicationClientReresolution"), True),
        (("resolution", "dnsResolveMillis"), 2001),
        (("redirects", "mode"), "automatic"),
        (("redirects", "maximumHops"), 6),
        (("redirects", "validateAndRepinEveryHop"), False),
        (("redirects", "crossOriginSensitiveHeaders"), "forward"),
        (("limits", "execFetch", "responseBodyBytes"), 1048577),
        (("limits", "liteCallback", "responseBodyBytes"), 65537),
        (("rebinding", "resolutionLifetime"), "request"),
        (("production", "execIncluded"), True),
        (("production", "execOptInAllowed"), True),
        (("production", "liteEmptyCallbackAllowlist"), "allow"),
    ],
)
def test_outbound_resolution_pinning_rejects_weakening(pointer, value):
    candidate = copy.deepcopy(FIXTURE)
    target = candidate
    for segment in pointer[:-1]:
        target = target[segment]
    target[pointer[-1]] = value
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(SCHEMA).validate(candidate)


def test_outbound_resolution_pinning_rejects_extra_fields():
    candidate = copy.deepcopy(FIXTURE)
    candidate["resolution"]["callerAddressOverride"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(SCHEMA).validate(candidate)
