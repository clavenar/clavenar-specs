import copy
import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
ATTACK_SCHEMA = json.loads(
    (ROOT / "contracts/attack-release-v1.schema.json").read_text()
)
ATTACK = json.loads(
    (ROOT / "contracts/attack-release-v1.fixture.json").read_text()
)
POLICY_SCHEMA = json.loads(
    (ROOT / "contracts/curated-policy-release-v1.schema.json").read_text()
)
POLICY = json.loads(
    (ROOT / "contracts/curated-policy-release-v1.fixture.json").read_text()
)


def validate(schema, candidate):
    jsonschema.Draft7Validator(schema).validate(candidate)


def test_attack_release_manifest_is_exact_and_reconciled():
    validate(ATTACK_SCHEMA, ATTACK)
    categories = ATTACK["proxyCategories"]
    proxy_ids = [scenario for group in categories for scenario in group["scenarioIds"]]
    direct_ids = ATTACK["directIdentityScenarioIds"]
    assert [group["name"] for group in categories] == sorted(
        group["name"] for group in categories
    )
    assert all(
        group["scenarioIds"] == sorted(group["scenarioIds"]) for group in categories
    )
    assert direct_ids == sorted(direct_ids)
    assert len(proxy_ids) == len(set(proxy_ids)) == ATTACK["totals"]["proxyScenarios"]
    assert len(direct_ids) == ATTACK["totals"]["directIdentityScenarios"]
    assert set(proxy_ids).isdisjoint(direct_ids)
    assert len(proxy_ids) + len(direct_ids) == ATTACK["totals"]["listedScenarios"]


def test_curated_policy_manifest_is_exact_and_reconciled():
    validate(POLICY_SCHEMA, POLICY)
    baseline = POLICY["crossCuttingBaseline"]["policyIds"]
    families = POLICY["industryFamilies"]
    industry_ids = [policy for family in families for policy in family["policyIds"]]
    all_ids = baseline + industry_ids
    assert [family["slug"] for family in families] == [
        "healthcare",
        "finance",
        "payments-fintech",
        "capital-markets",
        "legal",
        "coding",
        "devops",
        "hr",
        "manufacturing",
        "energy-utilities",
        "ml",
        "ecommerce",
        "government",
        "education",
        "insurance",
        "support",
        "marketing",
        "logistics",
        "telecom",
        "cybersecurity-ops",
    ]
    assert all(
        family["policyIds"] == sorted(family["policyIds"]) for family in families
    )
    assert baseline == sorted(baseline)
    assert len(all_ids) == len(set(all_ids)) == POLICY["totals"]["curatedPolicies"]
    assert len(baseline) == POLICY["totals"]["crossCuttingBaselinePolicies"]
    assert len(industry_ids) == POLICY["totals"]["industryPolicies"]
    assert len(families) == POLICY["totals"]["industryFamilies"]
    assert POLICY["sourceLibrary"] == {
        "templates": POLICY["totals"]["sourceLibraryTemplates"],
        "domains": POLICY["totals"]["sourceLibraryDomains"],
    }


@pytest.mark.parametrize(
    ("schema", "fixture", "path", "value"),
    [
        (ATTACK_SCHEMA, ATTACK, ("totals", "listedScenarios"), 92),
        (ATTACK_SCHEMA, ATTACK, ("totals", "proxyCategories"), 9),
        (POLICY_SCHEMA, POLICY, ("totals", "curatedPolicies"), 84),
        (POLICY_SCHEMA, POLICY, ("totals", "industryPolicies"), 85),
        (POLICY_SCHEMA, POLICY, ("sourceLibrary", "templates"), 576),
    ],
)
def test_manifests_reject_stale_counts(schema, fixture, path, value):
    candidate = copy.deepcopy(fixture)
    candidate[path[0]][path[1]] = value
    with pytest.raises(jsonschema.ValidationError):
        validate(schema, candidate)


def test_public_spec_counts_are_manifest_derived():
    tech_spec = (ROOT / "TECH_SPEC.md").read_text()
    features = (ROOT / "FEATURES.md").read_text()
    assert (
        f'{ATTACK["totals"]["proxyScenarios"]} proxy scenarios across '
        f'{ATTACK["totals"]["proxyCategories"]} categories'
    ) in tech_spec
    assert f'{ATTACK["totals"]["listedScenarios"]} listed scenarios total' in tech_spec
    assert f'{POLICY["totals"]["curatedPolicies"]} templates' in tech_spec
    assert f'{POLICY["totals"]["industryPolicies"]} policies' in tech_spec
    assert f'{POLICY["totals"]["industryFamilies"]} public industry families' in tech_spec
    assert f'{ATTACK["totals"]["listedScenarios"]} listed scenarios total' in features
