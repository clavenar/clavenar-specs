from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
FIXTURE = ROOT / "contracts/onboarding-prospect-evidence-v1.fixture.json"
SCHEMA = ROOT / "contracts/onboarding-prospect-evidence-v1.schema.json"
NAMES = (FIXTURE.name, SCHEMA.name)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_fixture_matches_strict_schema_and_privacy_boundary() -> None:
    schema = load(SCHEMA)
    fixture = load(FIXTURE)
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(fixture)
    assert fixture["contract"] == "clavenar.onboarding-prospect-evidence/v1"
    assert fixture["release"] == "1.244.0"
    assert fixture["privacyBoundary"]["releaseArtifactIdentityCount"] == 0
    assert fixture["privacyBoundary"]["rawContactDataInGit"] is False
    assert fixture["eventPolicy"]["sourceCompletenessCountsAsEvidence"] is False
    assert fixture["gatePolicy"]["deliveryCreditWithoutAdvance"] is False
    assert fixture["totals"] == {
        "playbooks": 2,
        "privateInputAliases": 3,
        "recordStates": 7,
        "evidenceKinds": 2,
        "publicIdentityFields": 0,
        "requiredGateConditions": 5,
    }


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("privacyBoundary", "releaseArtifactIdentityCount"), 1),
        (("privacyBoundary", "rawContactDataInGit"), True),
        (("artifacts", "relativePrivatePathFallback"), True),
        (("recordPolicy", "ownerRequired"), False),
        (("eventPolicy", "sourceCompletenessCountsAsEvidence"), True),
        (("gatePolicy", "minimumActualInterviewEvents"), 0),
        (("gatePolicy", "productionPilotApprovalIndependent"), False),
    ),
)
def test_schema_rejects_weakened_evidence_boundaries(
    path: tuple[str, ...],
    value: object,
) -> None:
    schema = load(SCHEMA)
    candidate = copy.deepcopy(load(FIXTURE))
    target = candidate
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(candidate)


def test_governed_mirrors_are_byte_identical() -> None:
    for name in NAMES:
        expected = (ROOT / "contracts" / name).read_bytes()
        assert (
            WORKSPACE / "clavenar-e2e/contracts" / name
        ).read_bytes() == expected
        assert (
            WORKSPACE / "clavenar-website/public/schemas" / name
        ).read_bytes() == expected
