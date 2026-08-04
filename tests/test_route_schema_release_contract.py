import hashlib
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
SCHEMA = json.loads(
    (CONTRACTS / "route-schema-release-v1.schema.json").read_text()
)
DEFINITION = json.loads(
    (CONTRACTS / "route-schema-release-v1.definition.json").read_text()
)
FIXTURE = json.loads(
    (CONTRACTS / "route-schema-release-v1.fixture.json").read_text()
)


def canonical_sha256(value):
    encoded = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def test_release_inventory_is_strict_and_complete():
    jsonschema.Draft202012Validator(SCHEMA).validate(FIXTURE)
    assert FIXTURE["release"] == "1.234.0"
    assert FIXTURE["totals"] == {
        "contracts": 6,
        "routes": 141,
        "schemas": 12,
        "services": 4,
        "typeBindings": 13,
    }
    assert {
        contract["id"] for contract in FIXTURE["contracts"]
    } == {
        "policy-evaluate",
        "hil-decision",
        "ledger-audit",
        "console-saml",
        "postgres-ledger",
        "rust-sdk-hil",
    }


def test_route_inventory_has_exact_unique_service_counts():
    routes = FIXTURE["routes"]
    keys = {
        (route["service"], route["method"], route["pathTemplate"])
        for route in routes
    }
    assert len(keys) == len(routes) == 141
    assert {
        service: sum(route["service"] == service for route in routes)
        for service in ("hil", "identity", "ledger", "policy-engine")
    } == {
        "hil": 29,
        "identity": 51,
        "ledger": 36,
        "policy-engine": 25,
    }


def test_every_example_validates_and_digests_reconcile():
    definition_ids = {
        contract["id"]: contract for contract in DEFINITION["contracts"]
    }
    for contract in FIXTURE["contracts"]:
        assert contract["id"] in definition_ids
        for record in contract["schemas"]:
            jsonschema.Draft202012Validator(
                record["jsonSchema"],
                format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
            ).validate(record["example"])
            assert record["schemaSha256"] == canonical_sha256(record["jsonSchema"])
            assert record["exampleSha256"] == canonical_sha256(record["example"])
        assert all(
            binding["itemSha256"].startswith("sha256:")
            for binding in contract["sourceBindings"]
        )


def test_public_docs_name_the_generated_contract_and_correct_routes():
    tech_spec = (ROOT / "TECH_SPEC.md").read_text()
    features = (ROOT / "FEATURES.md").read_text()
    inventory = (ROOT / "docs/ROUTE_SCHEMA_INVENTORY.md").read_text()
    for text in (tech_spec, features, inventory):
        assert "clavenar.route-schema-release/v1" in text
    assert "POST /evaluate" in inventory
    assert "POST /decide/{id}" in inventory
    assert "GET /verify" in inventory
    assert "CLAVENAR_CONSOLE_SAML_IDP_METADATA_URL" in inventory
    assert "dsnSecretKey" in inventory
