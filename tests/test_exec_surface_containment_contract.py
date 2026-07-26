import copy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts/exec-surface-containment-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts/exec-surface-containment-v1.fixture.json").read_text()
)


def test_fixture_matches_exact_containment_contract():
    jsonschema.Draft7Validator(SCHEMA).validate(FIXTURE)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("status",), "enabled"),
        (("production", "defaultIncluded"), True),
        (("production", "optInAllowed"), True),
        (("evaluationOptIn", "authority", "port"), 9002),
        (
            ("evaluationOptIn", "authority", "exactCallerSpiffe"),
            "spiffe://clavenar.local/service/proxy-evil",
        ),
        (("evaluationOptIn", "health", "mcpFallback"), True),
        (("evaluationOptIn", "health", "servicePublished"), True),
        (("evaluationOptIn", "networkPolicy", "authorityPeers"), ["any"]),
        (("rollback", "execEnabled"), True),
    ],
)
def test_unsafe_mutations_are_rejected(path, value):
    candidate = copy.deepcopy(FIXTURE)
    target = candidate
    for segment in path[:-1]:
        target = target[segment]
    target[path[-1]] = value
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(SCHEMA).validate(candidate)
