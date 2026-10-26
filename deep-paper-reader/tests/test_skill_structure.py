"""Mechanical smoke tests for the packaged skill sources."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_REFERENCES = (
    "deep-reading-workflow.md",
    "method-and-formula.md",
    "experiment-analysis.md",
    "critical-review.md",
    "domain-patterns.md",
    "output-contract.md",
    "teaching-playbook.md",
    "interactive-svg.md",
    "architecture-style.md",
)


class SkillStructureTests(unittest.TestCase):
    def test_required_structure(self):
        self.assertTrue((ROOT / "SKILL.md").is_file())
        self.assertTrue((ROOT / "agents/openai.yaml").is_file())
        self.assertTrue((ROOT / "assets/reading-note-template.md").is_file())
        for name in EXPECTED_REFERENCES:
            self.assertTrue((ROOT / "references" / name).is_file(), name)

    def test_references_in_entrypoint_resolve(self):
        content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        paths = re.findall(r"`((?:references|assets|scripts)/[^`\n]+)`", content)
        for path in paths:
            self.assertTrue((ROOT / path).is_file(), path)

    def test_name_matches_directory(self):
        self.assertEqual(ROOT.name, "deep-paper-reader")

    def test_readme_tree_files_exist(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        tree = readme.split("```text", 1)[1].split("```", 1)[0]
        for name in re.findall(r"[\w\-]+\.(?:md|py|yaml)", tree):
            self.assertTrue(any(ROOT.rglob(name)), name)

    def test_frontmatter_and_no_todos_in_runtime_docs(self):
        content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(content, r"\A---\nname: deep-paper-reader\n")
        self.assertRegex(content, r"\ndescription: >-\n")
        for path in [ROOT / "SKILL.md", *(ROOT / "references").glob("*.md")]:
            txt = path.read_text(encoding="utf-8")
            self.assertNotIn("[TODO:", txt)
            self.assertGreater(len(txt), 700)


if __name__ == "__main__":
    unittest.main()
