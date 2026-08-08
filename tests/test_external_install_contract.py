import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
SCHEMA = json.loads(
    (CONTRACTS / "external-install-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (CONTRACTS / "external-install-v1.fixture.json").read_text()
)


def test_inventory_is_strict_complete_and_public():
    jsonschema.Draft202012Validator(SCHEMA).validate(FIXTURE)
    assert FIXTURE["release"] == "1.245.17"
    assert FIXTURE["network"] == "public"
    assert FIXTURE["isolation"] == "clean-container-and-fresh-kind"
    assert FIXTURE["totals"] == {
        "packageInstalls": 8,
        "goModuleTags": 4,
        "releaseAssets": 11,
        "helmInstalls": 1,
        "protectedImageRepositories": 12,
        "protectedImageSubjects": 13,
    }


def test_every_package_owner_and_install_is_unique_and_versioned():
    packages = FIXTURE["packageInstalls"]
    assert len({item["id"] for item in packages}) == 8
    assert len({item["repository"] for item in packages}) == 8
    assert len({item["install"] for item in packages}) == 8
    assert all(item["version"] in item["install"] for item in packages)
    assert all(item["verification"] for item in packages)


def test_fresh_helm_install_is_exact_and_anonymous():
    helm = FIXTURE["helmInstall"]
    assert helm["version"] == "0.36.12"
    assert helm["registry"] == "oci://ghcr.io/clavenar/charts/clavenar"
    assert helm["valuesAsset"] == "clavenar-images-1.245.17.yaml"
    assert helm["packagedValues"] == "examples/values-bundled.yaml"
    assert helm["cluster"] == "fresh-kind"
    assert helm["imagePolicy"] == "anonymous-exact-digest-only"
    assert FIXTURE["protectedImages"] == {
        "repositories": 12,
        "subjects": 13,
        "tagPolicy": "digest-only",
        "access": "anonymous",
    }


def test_public_specs_name_external_install_gates():
    tech_spec = (ROOT / "TECH_SPEC.md").read_text()
    features = (ROOT / "FEATURES.md").read_text()
    for text in (tech_spec, features):
        assert "clavenar.external-install/v1" in text
        assert "fresh" in text
        assert "anonymous" in text
