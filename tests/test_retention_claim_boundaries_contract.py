import copy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts/retention-claim-boundaries-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts/retention-claim-boundaries-v1.fixture.json").read_text()
)


def validate(candidate):
    jsonschema.Draft7Validator(SCHEMA).validate(candidate)


def test_retention_claim_boundary_fixture_is_strict():
    validate(FIXTURE)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("publicClaim", "universalDurationSeconds"), 220752000),
        (("publicClaim", "fixedDurationApproved"), True),
        (("publicClaim", "immutableLifecycleApproved"), True),
        (("implementedControls", "recoveryPoint", "automaticPrune"), True),
        (("implementedControls", "recoveryPoint", "objectLockConfigured"), True),
        (
            (
                "implementedControls",
                "exportStorage",
                "destinationLifecycleConfiguredByClavenar",
            ),
            True,
        ),
        (("futureFixedDurationClaim", "status"), "approved"),
    ],
)
def test_retention_claim_boundary_rejects_unproved_claims(path, value):
    candidate = copy.deepcopy(FIXTURE)
    target = candidate
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(jsonschema.ValidationError):
        validate(candidate)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (
            ("implementedControls", "hilPayload", "maximumRetentionSeconds"),
            31536000,
        ),
        (
            ("implementedControls", "ledgerVacuum", "nonDemoMinimumVacuumSeconds"),
            220752000,
        ),
        (
            ("implementedControls", "recoveryPoint", "backupIntervalSeconds"),
            300,
        ),
    ],
)
def test_retention_claim_boundary_rejects_runtime_value_drift(path, value):
    candidate = copy.deepcopy(FIXTURE)
    target = candidate
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(jsonschema.ValidationError):
        validate(candidate)


def test_retention_claim_boundary_rejects_missing_future_evidence():
    candidate = copy.deepcopy(FIXTURE)
    candidate["futureFixedDurationClaim"]["requiredEvidence"].pop()
    with pytest.raises(jsonschema.ValidationError):
        validate(candidate)


def test_retention_claim_boundary_rejects_extra_fields():
    candidate = copy.deepcopy(FIXTURE)
    candidate["publicClaim"]["marketingApproved"] = True
    with pytest.raises(jsonschema.ValidationError):
        validate(candidate)
