from __future__ import annotations

import hashlib
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
FIXTURE = ROOT / "contracts/customer-legal-exchange-v1.fixture.json"
SCHEMA = ROOT / "contracts/customer-legal-exchange-v1.schema.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_customer_legal_exchange_fixture_matches_strict_schema() -> None:
    schema = load(SCHEMA)
    fixture = load(FIXTURE)
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(fixture)
    assert fixture["contract"] == "clavenar.customer-legal-exchange/v1"
    assert fixture["release"] == "1.245.0"
    assert fixture["totals"] == {
        "legalDocuments": 8,
        "guides": 2,
        "downloadableTools": 1,
        "publishedArtifacts": 11,
        "requiredExecutionFields": 12,
        "explicitNonclaims": 8,
        "recipientRoles": 2,
        "rejectedUnsafeStates": 14,
    }


def test_governed_mirrors_are_byte_identical() -> None:
    for name in (
        "customer-legal-exchange-v1.fixture.json",
        "customer-legal-exchange-v1.schema.json",
    ):
        expected = (ROOT / "contracts" / name).read_bytes()
        assert (WORKSPACE / "clavenar-e2e/contracts" / name).read_bytes() == expected
        assert (
            WORKSPACE / "clavenar-website/public/schemas" / name
        ).read_bytes() == expected


def test_exact_public_pack_and_tool_match_contract_commitments() -> None:
    fixture = load(FIXTURE)
    website = WORKSPACE / "clavenar-website/public"
    artifacts = [
        *fixture["legalPack"]["documents"],
        *fixture["legalPack"]["guides"],
        fixture["secureExchange"]["tool"],
    ]
    assert len(artifacts) == fixture["totals"]["publishedArtifacts"]
    for artifact in artifacts:
        payload = (website / artifact["path"]).read_bytes()
        actual = f"sha256:{hashlib.sha256(payload).hexdigest()}"
        assert actual == artifact["sha256"], artifact["path"]


def test_public_documents_cover_required_legal_and_safety_boundaries() -> None:
    public = WORKSPACE / "clavenar-website/public"
    required = {
        "legal/v1.0/master-services-agreement.md": (
            "## 4. Confidentiality",
            "## 6. Intellectual property and licenses",
            "## 10. Liability",
            "## 11. Term, suspension, termination, and effect",
        ),
        "legal/v1.0/data-processing-addendum.md": (
            "## 1. Roles, scope, and instructions",
            "## 6. Personal-data incidents",
            "## 7. Return, deletion, and evidence",
            "## 9. International transfers",
        ),
        "legal/v1.0/scc-election.md": (
            "Decision (EU) 2021/914",
            "Module 2",
            "Module 3",
            "## 5. Annex II",
        ),
        "legal/v1.0/security-data-schedule.md": (
            "## 3. Customer-controlled secure exchange",
            "AES-256-GCM",
            "## 7. Incident response",
            "## 8. Retention, return, and deletion",
        ),
        "legal/v1.0/procurement-response.md": (
            "SOC 2 report | Not claimed",
            "ISO 27001 certification | Not claimed",
            "No default public SLA",
        ),
        "legal/v1.0/founding-design-partner-offer.md": (
            "## Four-week evaluation",
            "USD $15,000",
            "There is no automatic renewal",
            "Each requires separate written",
        ),
    }
    for name, markers in required.items():
        text = (public / name).read_text(encoding="utf-8")
        for marker in markers:
            assert marker in text, (name, marker)
