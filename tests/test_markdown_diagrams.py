import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_PATHS = tuple(sorted((*ROOT.glob("*.md"), *(ROOT / "docs").glob("*.md"))))
BOX_DRAWING_CHARACTERS = frozenset("┌┐└┘├┤┬┴┼│─━┃┏┓┗┛┣┫┳┻╋")
MERMAID_BLOCK = re.compile(r"^```mermaid\n(.*?)^```$", re.MULTILINE | re.DOTALL)


class MarkdownDiagramTests(unittest.TestCase):
    def test_markdown_contains_no_box_drawing_diagrams(self):
        violations = {}
        for path in MARKDOWN_PATHS:
            text = path.read_text(encoding="utf-8")
            found = sorted(BOX_DRAWING_CHARACTERS.intersection(text))
            if found:
                violations[str(path.relative_to(ROOT))] = found
        self.assertEqual({}, violations)

    def test_every_mermaid_diagram_is_accessible(self):
        diagrams = 0
        for path in MARKDOWN_PATHS:
            for block in MERMAID_BLOCK.findall(path.read_text(encoding="utf-8")):
                diagrams += 1
                with self.subTest(path=str(path.relative_to(ROOT)), diagram=diagrams):
                    self.assertRegex(block, r"(?m)^\s+accTitle:\s+\S")
                    self.assertRegex(block, r"(?m)^\s+accDescr:\s+\S")
        self.assertGreater(diagrams, 0)


if __name__ == "__main__":
    unittest.main()
