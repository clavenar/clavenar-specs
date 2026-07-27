import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
SCHEMA = json.loads(
    (CONTRACTS / "executable-documentation-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (CONTRACTS / "executable-documentation-v1.fixture.json").read_text()
)


def test_inventory_is_strict_complete_and_two_phase():
    jsonschema.Draft202012Validator(SCHEMA).validate(FIXTURE)
    assert FIXTURE["release"] == "1.235.0"
    assert FIXTURE["phases"] == ["staged", "public"]
    assert FIXTURE["totals"] == {
        "quickstarts": 8,
        "helmRecipes": 6,
        "websiteChecks": 5,
        "phases": 2,
    }


def test_every_quickstart_owner_and_runner_is_unique():
    quickstarts = FIXTURE["quickstarts"]
    assert len({item["id"] for item in quickstarts}) == 8
    assert len({item["repository"] for item in quickstarts}) == 8
    assert len({item["runner"] for item in quickstarts}) == 8
    assert all(item["phases"] == ["staged", "public"] for item in quickstarts)


def test_every_container_is_immutable():
    assert all(
        "@sha256:" in image and not image.endswith(":latest")
        for image in FIXTURE["containerImages"].values()
    )


def test_public_spec_names_executable_contract_and_gates():
    tech_spec = (ROOT / "TECH_SPEC.md").read_text()
    features = (ROOT / "FEATURES.md").read_text()
    for text in (tech_spec, features):
        assert "clavenar.executable-documentation/v1" in text
        assert "staged" in text
        assert "public" in text
