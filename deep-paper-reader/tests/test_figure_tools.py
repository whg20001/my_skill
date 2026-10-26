#!/usr/bin/env python3
"""Run: python -m unittest discover -s tests -v"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import tempfile  # noqa: E402

from check_figure import check_svg, find_browser, html_selftest  # noqa: E402
from svg_figure_kit import Figure, min_font_px, rich  # noqa: E402

SVG_HEAD = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 400">'
            "<title>t</title><desc>d</desc><style>text{font-size:26px}.tiny{font-size:18px}</style>")


def build_demo() -> Figure:
    fig = Figure(1600, 520, "Demo 架构", "两阶段训练的最小示例")
    fig.section("s1", 20, 300, "A Stage 1", "§3 · Eq. 1", nav="Stage 1")
    fig.box("enc", 40, 100, 240, 140, "Encoder", [(82, "*H* = ENC_{*θ*}(*X*)", "body")],
            "编码器，Stage 1 训练。", "eeg", "trainable")
    fig.box("llm", 340, 100, 240, 140, "Backbone *ω*", [(82, "*ω* 不更新", "body")],
            "主干冻结。", "llm", "frozen")
    fig.line([(280, 150), (340, 150)])
    fig.line([(340, 200), (280, 200)], "gradient")
    fig.end()
    fig.legend_lines(40, 380, ("forward", "gradient"))
    fig.notes(40, 440, ["注：① 示例图，非任何论文。"])
    return fig


class RichTextTests(unittest.TestCase):
    def test_subscript_uses_dy_and_smaller_font(self):
        out = rich("*d*_{LLM}", 24)
        self.assertIn('dy="6.7"', out)
        self.assertIn('font-size="16.8"', out)
        self.assertIn('font-style="italic"', out)

    def test_literal_underscore_and_braces(self):
        self.assertEqual(rich("<eeg_start>", 24), "&lt;eeg_start&gt;")
        self.assertIn("{", rich(r"ENC(\{e\})", 24))
        self.assertIn("}", rich(r"ENC(\{e\})", 24))

    def test_min_font_px(self):
        self.assertEqual(min_font_px(1600), 23)
        self.assertEqual(min_font_px(1920), 27)
        self.assertEqual(min_font_px(1600, 241), 47)


class FigureKitTests(unittest.TestCase):
    def test_demo_passes_checks(self):
        svg = build_demo().svg()
        errors, warnings = check_svg(svg)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertNotIn('role="button"', svg)
        self.assertNotIn("tabindex", svg)
        self.assertIn('stroke-dasharray="8 5"', svg)  # frozen border
        self.assertIn(">可训练<", svg)

    def test_html_adds_interaction_at_runtime(self):
        html = build_demo().html()
        self.assertIn("setAttribute('role', 'button')", html)
        self.assertIn('data-view="s1"', html)
        self.assertIn('"enc": "编码器，Stage 1 训练。"', html)

    def test_section_summaries_reach_the_panel(self):
        fig = build_demo()
        fig.section("s2", 330, 50, "B Stage 2", summary="冻结编码器，只训练接口 </script>")
        fig.end()
        html = fig.html()
        self.assertIn('"all": "两阶段训练的最小示例"', html)  # overview uses desc
        self.assertIn('"s2": "冻结编码器，只训练接口 <\\/script>"', html)
        self.assertNotIn("请选择模块", html)
        self.assertNotIn("__", html.split("<script>")[1].split("const moduleNodes")[0])

    @unittest.skipUnless(find_browser(), "needs Edge or Chrome")
    def test_browser_selftest_covers_views(self):
        # s1 has no summary, so its panel text must list the modules instead.
        with tempfile.TemporaryDirectory() as tmp:
            _, html = build_demo().save(tmp, "demo")
            self.assertTrue(html_selftest(html).startswith("SELFTEST PASS"))


class CheckFigureTests(unittest.TestCase):
    def test_small_font_is_error(self):
        svg = SVG_HEAD + '<text class="tiny">小字</text><text>注：x</text></svg>'
        errors, _ = check_svg(svg)
        self.assertTrue(any("小于 7 pt" in e for e in errors))
        errors, _ = check_svg(svg.replace("viewBox=\"0 0 1600 400\"", "viewBox=\"0 0 1000 400\""))
        self.assertEqual(errors, [])

    def test_missing_reference_and_leaked_role(self):
        svg = SVG_HEAD + ('<path marker-end="url(#nope)"/><g role="button" tabindex="0"><text>注：x</text></g></svg>')
        errors, _ = check_svg(svg)
        self.assertTrue(any("不存在的 id" in e for e in errors))
        self.assertTrue(any("role=button" in e for e in errors))

    def test_disclaimer_in_module_warns(self):
        svg = SVG_HEAD + '<g data-module="m"><text>非图像</text></g><text>注：x</text></svg>'
        _, warnings = check_svg(svg)
        self.assertTrue(any("免责" in w for w in warnings))

    def test_reference_asset_passes(self):
        svg = (ROOT / "assets/architecture-style-reference.svg").read_text(encoding="utf-8")
        errors, _ = check_svg(svg)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
