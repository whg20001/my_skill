#!/usr/bin/env python3
"""Run: python -m unittest discover -s tests -v"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from lint_report import FULL_TITLES, lint_text  # noqa: E402

EVIDENCE_TABLE = (
    "\n| 关键论断 | 性质 | 位置 | 状态 |\n|---|---|---|---|\n"
    "| 测试一 | 原文事实 | §3.1 | 已核实 |\n"
    "| 测试二 | 原文事实 | Table 1 | 已核实 |\n"
    "| 测试三 | 推测/待验证 | 无 | 待验证 |"
)


def build_full_report(evidence_table: str = EVIDENCE_TABLE) -> str:
    content = "# 虚构论文｜深度精读笔记\n\n"
    content += "\n\n".join(
        "## " + heading + "\n内容（§3.1）。"
        + ("\n来源：PDF；来源覆盖：partial。" if heading.startswith("0.") else "")
        + (evidence_table if heading.startswith("8.") else "")
        for heading in FULL_TITLES
    )
    return content + "\n原文事实。\n"


class LintReportTests(unittest.TestCase):
    def test_good_full_report(self):
        errors, warnings = lint_text(build_full_report())
        self.assertEqual(errors, [])
        self.assertFalse(any("证据索引不足" in w for w in warnings))

    def test_thin_evidence_table_warns(self):
        thin = "\n| 关键论断 | 性质 | 位置 | 状态 |\n|---|---|---|---|\n| 测试 | 原文事实 | §3.1 | 已核实 |"
        errors, warnings = lint_text(build_full_report(thin))
        self.assertEqual(errors, [])
        self.assertTrue(any("证据索引不足" in w for w in warnings))

    def test_missing_sections_and_coverage(self):
        errors, _warnings = lint_text("# 标题\n## 1. 核心观点与阅读导航\n")
        self.assertTrue(any("缺少全文精读章节" in e for e in errors))
        self.assertTrue(any("覆盖状态" in e for e in errors))

    def test_coverage_word_outside_section0_does_not_count(self):
        content = "\n\n".join("## " + h + ("\n来源：PDF。" if h.startswith("0.") else "\npartial derivative（§3.1）") for h in FULL_TITLES)
        errors, _ = lint_text(content)
        self.assertTrue(any("覆盖状态" in e for e in errors))

    def test_unresolved_placeholders(self):
        errors, _warnings = lint_text("回答 {{论文正式标题}}，§2。", mode="focused")
        self.assertTrue(any("未替换占位符" in e for e in errors))

    def test_focused_does_not_need_full_sections(self):
        errors, _warnings = lint_text("该式的变量 $x$ 是输入（§3, Eq.(1)）。", mode="focused")
        self.assertEqual(errors, [])

    def test_quick_requires_coverage(self):
        errors, _ = lint_text("**一句话**：用门控融合两个分类器（§3）。", mode="quick")
        self.assertTrue(any("覆盖状态" in e for e in errors))
        errors, _ = lint_text("**来源与覆盖**：PDF，partial。\n**一句话**：门控融合（§3）。", mode="quick")
        self.assertEqual(errors, [])

    def test_ambiguous_percent_warns(self):
        _, warnings = lint_text("准确率提升 4% （Table 2）。", mode="focused")
        self.assertTrue(any("百分点" in w for w in warnings))
        _, warnings = lint_text("准确率提升 4 个百分点（Table 2），相对提升 5%（相对）。", mode="focused")
        self.assertFalse(any("百分点还是相对" in w for w in warnings))

    def test_empty_fails(self):
        errors, _warnings = lint_text("  ")
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
