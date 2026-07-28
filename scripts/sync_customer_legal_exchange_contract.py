#!/usr/bin/env python3
"""Mirror the public customer legal/exchange contract to governed consumers."""

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
NAMES = (
    "customer-legal-exchange-v1.fixture.json",
    "customer-legal-exchange-v1.schema.json",
)
TARGETS = (
    WORKSPACE / "clavenar-e2e/contracts",
    WORKSPACE / "clavenar-website/public/schemas",
)


def main() -> None:
    for target in TARGETS:
        target.mkdir(parents=True, exist_ok=True)
        for name in NAMES:
            shutil.copyfile(ROOT / "contracts" / name, target / name)


if __name__ == "__main__":
    main()
