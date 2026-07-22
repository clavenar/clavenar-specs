import json
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "contracts" / "nats-authorization-v1.fixture.json"
SCHEMA = ROOT / "contracts" / "nats-authorization-v1.schema.json"


class NatsAuthorizationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE.read_text())
        cls.schema = json.loads(SCHEMA.read_text())

    def test_fixture_validates(self) -> None:
        jsonschema.Draft202012Validator(self.schema).validate(self.fixture)

    def test_every_reference_resolves_to_one_exact_certificate_client(self) -> None:
        clients = self.fixture["clients"]
        services = [client["service"] for client in clients]
        self.assertEqual(sorted(services), services)
        self.assertEqual(len(services), len(set(services)))
        for client in clients:
            service = client["service"]
            self.assertEqual(service, client["dnsSan"])
            self.assertEqual(
                f"spiffe://clavenar.local/service/{service}", client["spiffeId"]
            )
            self.assertEqual(
                f"_INBOX.clavenar.{service}", client["inboxPrefix"]
            )

        referenced = set()
        for subject in self.fixture["subjects"]:
            referenced.update(subject["publishers"])
            referenced.update(subject["subscribers"])
            if subject["streamManager"]:
                referenced.add(subject["streamManager"])
            referenced.update(item["service"] for item in subject["durableConsumers"])
        for bucket in self.fixture["kvBuckets"]:
            referenced.add(bucket["manager"])
            referenced.update(bucket["readers"])
            referenced.update(bucket["writers"])
        self.assertEqual(set(services), referenced)

    def test_subject_and_state_namespaces_are_unique_and_ordered(self) -> None:
        subjects = self.fixture["subjects"]
        names = [item["subject"] for item in subjects]
        self.assertEqual(len(names), len(set(names)))
        streams = [item["stream"] for item in subjects if item["stream"]]
        self.assertEqual(len(streams), len(set(streams)))

        buckets = [item["bucket"] for item in self.fixture["kvBuckets"]]
        self.assertEqual(sorted(buckets), buckets)
        self.assertEqual(len(buckets), len(set(buckets)))
        for item in subjects:
            self.assertEqual(sorted(item["publishers"]), item["publishers"])
            self.assertEqual(sorted(item["subscribers"]), item["subscribers"])
        for item in self.fixture["kvBuckets"]:
            self.assertEqual(sorted(item["readers"]), item["readers"])
            self.assertEqual(sorted(item["writers"]), item["writers"])
            self.assertIn(item["manager"], item["readers"])

    def test_contract_keeps_broad_authority_forbidden(self) -> None:
        self.assertEqual(
            [">", "$SYS.>", "$JS.API.>", "$KV.>", "_INBOX.>"],
            self.fixture["forbiddenSubjects"],
        )
        self.assertFalse(self.fixture["profiles"]["prod"]["hostPublication"])
        for profile in self.fixture["profiles"].values():
            self.assertTrue(profile["brokerNetworkInternal"])
            self.assertTrue(profile["persistentVolumeRequired"])
            self.assertEqual("/data/jetstream", profile["jetstreamStore"])


if __name__ == "__main__":
    unittest.main()
