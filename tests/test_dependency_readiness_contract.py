import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts" / "dependency-readiness-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (ROOT / "contracts" / "dependency-readiness-v1.fixture.json").read_text()
)

EXPECTED_SERVICES = {
    "nats",
    "vault",
    "vault-custodian",
    "bootstrap",
    "upstream-stub",
    "identity",
    "brain",
    "policy-engine",
    "ledger",
    "hil",
    "deep-review",
    "proxy",
    "assurance",
    "console",
    "demo-mint",
    "simulator",
    "website",
}

EXPECTED_HELM = {
    "nats",
    "vault",
    "upstream-stub",
    "identity",
    "brain",
    "policy-engine",
    "ledger",
    "hil",
    "deep-review",
    "proxy",
    "assurance",
    "console",
}


class DependencyReadinessContractTest(unittest.TestCase):
    def test_fixture_validates(self) -> None:
        jsonschema.Draft202012Validator(SCHEMA).validate(FIXTURE)

    def test_inventory_is_exact_and_unique(self) -> None:
        services = FIXTURE["services"]
        ids = [service["id"] for service in services]
        self.assertEqual(EXPECTED_SERVICES, set(ids))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            EXPECTED_HELM,
            {service["id"] for service in services if "helm" in service["topologies"]},
        )
        self.assertTrue(
            all("compose" in service["topologies"] for service in services)
        )

    def test_dependencies_are_topology_closed_and_acyclic(self) -> None:
        services = {service["id"]: service for service in FIXTURE["services"]}
        for topology in ("compose", "helm"):
            nodes = {
                service_id
                for service_id, service in services.items()
                if topology in service["topologies"]
            }
            edges = {
                service_id: {
                    edge["service"]
                    for edge in service["startupAfter"]
                    if topology in edge["topologies"]
                }
                for service_id, service in services.items()
                if service_id in nodes
            }
            for service_id, dependencies in edges.items():
                self.assertTrue(
                    dependencies <= nodes,
                    f"{topology}:{service_id} has unavailable dependencies",
                )
                self.assertNotIn(service_id, dependencies)

            visiting: set[str] = set()
            visited: set[str] = set()

            def visit(service_id: str) -> None:
                if service_id in visiting:
                    self.fail(f"{topology} readiness dependency cycle at {service_id}")
                if service_id in visited:
                    return
                visiting.add(service_id)
                for dependency in edges[service_id]:
                    visit(dependency)
                visiting.remove(service_id)
                visited.add(service_id)

            for service_id in nodes:
                visit(service_id)

    def test_http_services_have_distinct_liveness_and_readiness(self) -> None:
        for service in FIXTURE["services"]:
            if service["readiness"]["type"] != "http":
                continue
            self.assertEqual("http", service["liveness"]["type"])
            self.assertNotEqual(
                service["liveness"]["target"], service["readiness"]["target"]
            )
            self.assertTrue(service["liveness"]["target"].endswith(("/health", "/healthz")))
            if service["id"] == "nats":
                self.assertTrue(
                    service["readiness"]["target"].endswith(
                        "/healthz?js-enabled-only=true"
                    )
                )
            else:
                self.assertIn("/readyz", service["readiness"]["target"])
            self.assertEqual(
                "command-nonzero" if service["id"] == "nats" else "http-503",
                service["failureMode"],
            )

    def test_external_providers_are_configuration_only(self) -> None:
        provider_services = {
            service["id"]
            for service in FIXTURE["services"]
            if service["providerProbe"] == "configuration-only"
        }
        self.assertEqual({"brain", "deep-review", "demo-mint"}, provider_services)
        self.assertEqual(
            "configuration-only", FIXTURE["limits"]["externalProviderProbe"]
        )

    def test_critical_dependency_checks_are_explicit(self) -> None:
        checks = {service["id"]: set(service["checks"]) for service in FIXTURE["services"]}
        self.assertTrue({"server", "jetstream"} <= checks["nats"])
        self.assertTrue({"active", "unsealed"} <= checks["vault"])
        self.assertTrue(
            {
                "vault",
                "ca",
                "oidc",
                "control_sync",
                "outbox_worker",
                "attestation_k8s_key_bound",
                "attestation_signed_measurement_registry",
            }
            <= checks["identity"]
        )
        self.assertTrue({"forensic_consumer", "identity_signing"} <= checks["ledger"])
        self.assertIn("outbox_worker", checks["policy-engine"])
        self.assertIn("sweeper", checks["hil"])
        self.assertTrue(
            {"brain", "policy_engine", "hil", "ledger", "identity", "upstream"}
            <= checks["proxy"]
        )
        self.assertTrue({"assets", "version"} <= checks["website"])


if __name__ == "__main__":
    unittest.main()
