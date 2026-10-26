#!/usr/bin/env python3
"""Structural lint for a Deep Paper Reader Markdown report.

This checks headings, a coverage marker, an evidence anchor, and leftover
placeholders. It does NOT check factual claims, math, citation truth, or whether
an arXiv article was actually read; perform source-based review separately.

Usage:
    python scripts/lint_report.py report.md --mode full
    python scripts/lint_report.py report.md --mode quick
    python scripts/lint_report.py report.md --mode focused
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

FULL_TITLES = (
    "0. 论文来源与覆盖",
    "1. 核心观点与阅读导航",
    "2. 研究问题与动机",
    "3. 核心贡献与整体方法",
    "4. 模块、算法与关键公式",
    "5. 实验设计与证据分析",
    "6. 局限性与批判性思考",
    "7. 直观例子与理解检验",
    "8. 论断—原文证据索引",
    "9. 技术洞察与开放问题",
)

# Pattern matching does not establish that any citation is real.
ANCHOR_PATTERN = re.compile(
    r"(?:§\s*\d+(?:\.\d+)*|"
    r"\b(?:Eq\.?\s*\(?\d+\)?|Fig\.?\s*\d+|Figure\s+\d+|"
    r"Table\s+\d+|Algorithm\s+\d+|Abstract)\b)",
    re.IGNORECASE,
)
PLACEHOLDER_PATTERN = re.compile(r"\{\{[^\n]*?\}\}|\[TODO[^\]]*\]|<待填写>")
COVERAGE_PATTERN = re.compile(r"\b(?:complete|partial|abstract-only)\b", re.IGNORECASE)
# "提升 4%" is ambiguous: percentage points or relative improvement?
AMBIGUOUS_PERCENT_PATTERN = re.compile(
    r"(?:提升|提高|下降|降低|增加|减少)了?\s*\d+(?:\.\d+)?\s*%(?!\s*[（(]?\s*(?:相对|relative))",
    re.IGNORECASE,
)
# Markdown table rows, excluding the |---|---| separator.
TABLE_ROW_PATTERN = re.compile(r"^\|(?!\s*:?-).*\|\s*$", re.MULTILINE)


def lint_text(content: str, mode: str = "full") -> Tuple[List[str], List[str]]:
    """Return structural errors and warnings, without pretending to verify science."""
    errors: List[str] = []
    warnings: List[str] = []

    if not content.strip():
        return ["Markdown 笔记为空"], warnings

    leftovers = PLACEHOLDER_PATTERN.findall(content)
    if leftovers:
        errors.append(f"存在未替换占位符 {len(leftovers)} 处（例如：{leftovers[0][:65]}）")

    if mode == "full":
        headings = re.findall(r"^##\s+(.+?)\s*$", content, flags=re.MULTILINE)
        missing = [h for h in FULL_TITLES if h not in headings]
        if missing:
            errors.append("缺少全文精读章节：" + "、".join(missing))
        sections = re.split(r"^##\s+", content, flags=re.MULTILINE)
        by_title = {s.split("\n", 1)[0].strip(): s for s in sections[1:]}
        source_sec = by_title.get(FULL_TITLES[0], "")
        if not COVERAGE_PATTERN.search(source_sec):
            errors.append("§0 中未明确写出覆盖状态：complete / partial / abstract-only")
        evidence = by_title.get(FULL_TITLES[8])
        if evidence is not None:
            if not re.search(r"\|.*\|.*\|", evidence):
                errors.append("证据索引章节缺少 Markdown 表格")
            elif len(TABLE_ROW_PATTERN.findall(evidence)) < 4:
                warnings.append("证据索引不足 3 条论断；通常应覆盖问题定义、创新模块、关键公式、主实验与局限")
        if not re.search(r"PDF|arXiv|来源", content, re.IGNORECASE):
            warnings.append("未发现明显的来源类型标识（PDF / arXiv / 来源）")

    if mode == "quick" and not COVERAGE_PATTERN.search(content):
        errors.append("速览中未明确写出覆盖状态：complete / partial / abstract-only")

    if not ANCHOR_PATTERN.search(content):
        warnings.append("没有检测到 §编号 / Eq. / Fig. / Table / Abstract 等锚点；请检查来源定位")
    if "[原文事实]" not in content and "原文事实" not in content:
        warnings.append("未检测到事实/解释分类用语；需核实是否清晰区分论断性质")
    if re.search(r"\b(?:Table\s+X|Fig\.?\s+X|Eq\.?\s*\(?X\)?)\b", content, re.IGNORECASE):
        warnings.append("疑似未替换证据编号占位符（Table X / Fig. X / Eq. X）")
    ambiguous = AMBIGUOUS_PERCENT_PATTERN.findall(content)
    if ambiguous:
        warnings.append(f"发现 {len(ambiguous)} 处“提升 X%”式表述（例如：{ambiguous[0]}）；请确认是百分点还是相对提升")

    return errors, warnings


def main() -> int:
    # Windows consoles often default to cp1252/GBK, which crashes on Chinese output.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="需要检查的 Markdown 笔记")
    parser.add_argument("--mode", choices=("full", "quick", "focused"), default="full")
    args = parser.parse_args()
    try:
        content = args.report.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: 无法读取 {args.report}: {exc}")
        return 2

    errors, warnings = lint_text(content, args.mode)
    for item in errors:
        print(f"ERROR: {item}")
    for item in warnings:
        print(f"WARN: {item}")
    if errors:
        print("FAIL: 结构检查未通过；仍需独立核查论文原文。")
        return 1
    print("PASS: 基本结构检查通过。该结果不代表事实、数学、实验或引文准确。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
