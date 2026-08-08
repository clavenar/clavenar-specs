import copy
import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
SCHEMA = json.loads(
    (CONTRACTS / "cluster-install-v1.schema.json").read_text()
)
FIXTURE = json.loads(
    (CONTRACTS / "cluster-install-v1.fixture.json").read_text()
)


class ClusterInstallContractTests(unittest.TestCase):
    def test_existing_cluster_installer_is_strict_and_complete(self) -> None:
        jsonschema.Draft202012Validator(SCHEMA).validate(FIXTURE)
        self.assertEqual("existing-kubernetes-cluster", FIXTURE["scope"])
        self.assertEqual(
            "curl -fsSL https://clavenar.ai/install.sh | sh",
            FIXTURE["bootstrap"]["command"],
        )
        self.assertTrue(FIXTURE["helmInstall"]["wait"])
        self.assertTrue(FIXTURE["helmInstall"]["waitForJobs"])
        self.assertEqual(
            "fail-closed", FIXTURE["lifecycle"]["collisionPolicy"]
        )
        self.assertFalse(FIXTURE["lifecycle"]["receipt"]["containsSecrets"])
        self.assertEqual(
            "curl -fsSL https://clavenar.ai/uninstall.sh | sh",
            FIXTURE["uninstallBootstrap"]["command"],
        )
        self.assertEqual(
            [
                "https://dev.clavenar.ai/installers/"
                "clavenar-install-1.2.0.sh"
            ],
            FIXTURE["installer"]["mirrorUrls"],
        )
        self.assertEqual(
            [
                "https://dev.clavenar.ai/installers/"
                "clavenar-uninstall-1.0.0.sh"
            ],
            FIXTURE["uninstaller"]["mirrorUrls"],
        )
        self.assertEqual(
            "retain",
            FIXTURE["lifecycle"]["uninstall"]["defaultDataDisposition"],
        )
        self.assertEqual(
            [
                "persistent-volume-claims",
                "operator-public-trust",
                "namespace",
            ],
            FIXTURE["lifecycle"]["uninstall"]["retainedResources"],
        )

    def test_operator_is_default_and_demo_requires_explicit_evaluation(self) -> None:
        profiles = {item["name"]: item for item in FIXTURE["profiles"]}
        self.assertTrue(profiles["operator"]["default"])
        self.assertFalse(FIXTURE["consoleAccess"]["anonymousDemoDefault"])
        self.assertEqual(
            "operator-mtls", FIXTURE["consoleAccess"]["defaultMode"]
        )
        self.assertEqual(
            "evaluation", FIXTURE["consoleAccess"]["demoOptInProfile"]
        )
        self.assertEqual(
            {
                "workloads-ready",
                "exact-digest-images",
                "operator-admin-ready",
                "anonymous-demo-disabled",
                "tools-list",
                "ledger-chain-advanced",
            },
            set(profiles["operator"]["verification"]),
        )
        self.assertEqual(
            [
                "workloads-ready",
                "exact-digest-images",
                "anonymous-demo-disabled",
            ],
            profiles["custom"]["verification"],
        )

    def test_contract_rejects_cluster_provisioning_or_mutable_identity(
        self,
    ) -> None:
        for mutate in (
            lambda item: item.update(scope="provision-k3s"),
            lambda item: item["bootstrap"].update(
                url="https://clavenar.com/install.sh"
            ),
            lambda item: item["installer"].update(
                sha256="sha256:" + "0" * 64
            ),
            lambda item: item["installer"].update(mirrorUrls=[]),
            lambda item: item["uninstaller"].update(
                checksumMirrorUrls=[]
            ),
            lambda item: item["helmInstall"].update(waitForJobs=False),
            lambda item: item["consoleAccess"].update(
                anonymousDemoDefault=True
            ),
            lambda item: item["lifecycle"].update(
                collisionPolicy="overwrite"
            ),
            lambda item: item["lifecycle"]["uninstall"].update(
                defaultDataDisposition="delete"
            ),
            lambda item: item["lifecycle"]["uninstall"].update(
                destructiveConfirmationFlag=""
            ),
            lambda item: item["clusterAccess"]["preflight"].pop(),
            lambda item: item["profiles"].__setitem__(
                1, copy.deepcopy(item["profiles"][0])
            ),
            lambda item: item["outOfScope"].pop(),
        ):
            with self.subTest(mutate=mutate):
                candidate = copy.deepcopy(FIXTURE)
                mutate(candidate)
                with self.assertRaises(jsonschema.ValidationError):
                    jsonschema.Draft202012Validator(SCHEMA).validate(candidate)

    def test_public_specs_name_existing_cluster_install_boundary(self) -> None:
        tech_spec = (ROOT / "TECH_SPEC.md").read_text()
        features = (ROOT / "FEATURES.md").read_text()
        for text in (tech_spec, features):
            self.assertIn("clavenar.cluster-install/v1", text)
            self.assertIn("existing Kubernetes", text)
            self.assertIn("install.sh", text)
            self.assertIn("uninstall.sh", text)
            self.assertIn("persistent data", text.lower())
