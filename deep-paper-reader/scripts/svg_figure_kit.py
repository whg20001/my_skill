#!/usr/bin/env python3
r"""Helpers for building research architecture figures as self-contained SVG + HTML.

The kit encodes the rules in references/architecture-style.md so that a figure
builder only decides content and coordinates:

- fill colour = modality / role, border + pill = training state (trainable / frozen);
- five line kinds: forward, supervise, gradient, inherit (plus legend helpers);
- text markup: *x* italic, _{...} subscript, ^{...} superscript, \{ \} literal
  braces. An underscore not followed by "{" stays literal, so <eeg_start> is safe;
- sub/superscripts use dy shifts (portable), italics use Cambria (clear z, v, w);
- the static SVG carries no role/tabindex; the HTML adds them with JavaScript.

Typical builder (keep it next to the figure, e.g. assets/build_<topic>.py):

    import sys; sys.path.insert(0, r"<skill>/scripts")
    from svg_figure_kit import Figure
    fig = Figure(1600, 1200, "Model 架构", "一句话描述……")
    fig.section("model", 115, 500, "A 模型结构", "§3 · Eq. 1–4", nav="模型结构",
                summary="切换到这个视角时显示在说明框里的分区概要")
    fig.box("encoder", 40, 185, 220, 160, "Encoder", [(90, "*h* = ENC(*X*)", "body")],
            "说明面板里的完整解释与原文锚点", kind="eeg", state="trainable")
    fig.end()
    fig.save("assets", "topic")   # writes topic.svg and topic.html

Then run scripts/check_figure.py on the SVG and look at the rendered PNG.
"""
from __future__ import annotations

import json
import math
from html import escape
from pathlib import Path

SIZES = {"title": 36, "heading": 30, "bold": 26, "": 26, "body": 24, "note": 24, "mono": 24}
FILLS = {  # (fill, modality border)
    "eeg": ("#E4EEF8", "#5B87B8"),       # signal / encoder side
    "bridge": ("#EEE7F6", "#8A6FB0"),    # projector / adapter / fusion interface
    "text": ("#E5F2E6", "#5E9A64"),      # language / token side
    "llm": ("#FBF1D3", "#B8973A"),       # backbone (LLM, decoder, policy …)
    "neutral": ("#FFFFFF", "#9AA5B1"),   # data, loss, label, non-parametric op
}
TRAINABLE = dict(stroke="#C8743A", stroke_width="3")
FROZEN = dict(stroke="#6F7C8B", stroke_width="2.2", stroke_dasharray="8 5")
LINE_COLORS = {"forward": "#4F7FB8", "supervise": "#333", "gradient": "#B0652F", "inherit": "#7D7D7D"}
LINE_LABELS = {"forward": "前向计算", "supervise": "监督信号（标签 / 参考答案）",
               "gradient": "梯度回传（机制示意）", "inherit": "参数继承（跨阶段）"}
STATE_LABELS = {"trainable": "可训练", "frozen": "冻结"}
MODALITY_LABELS = {"eeg": "信号侧", "bridge": "接口", "text": "文本侧", "llm": "主干"}

CSS = """text{font-family:'Times New Roman','Cambria Math','SimSun','Noto Serif CJK SC',serif;fill:#171717;font-size:26px}
.title{font-size:36px;font-weight:bold}.heading{font-size:30px;font-weight:bold}.bold{font-weight:bold}
.body{font-size:24px}.note{font-size:24px;fill:#555}
.mono{font-family:Consolas,'Courier New',monospace;font-size:24px}
.forward{fill:none;stroke:#4F7FB8;stroke-width:2.6}
.supervise{fill:none;stroke:#333;stroke-width:2}
.gradient{fill:none;stroke:#B0652F;stroke-width:2.2;stroke-dasharray:9 5}
.inherit{fill:none;stroke:#7D7D7D;stroke-width:2.4;stroke-dasharray:2 6;stroke-linecap:round}
.selected .module-bg,[data-module]:focus .module-bg{stroke:#1F3A5F;stroke-width:4;stroke-dasharray:none}
[data-module]:focus{outline:none}
.dimmed{opacity:.18}"""


def min_font_px(canvas_width: float, target_width_pt: float = 504, min_pt: float = 7) -> int:
    """Smallest canvas font size that still prints at min_pt when scaled to target_width_pt.

    504 pt = 7 in, a two-column paper's full text width; use ~241 pt for one column.
    """
    return math.ceil(min_pt * canvas_width / target_width_pt)


def text_width(s: str, size: float = 24) -> float:
    """Rough rendered width: CJK and full-width glyphs ≈ 1 em, others ≈ 0.5 em."""
    return sum(size if ord(c) >= 0x2E80 else size * 0.5 for c in s.replace("*", ""))


def parse_markup(s: str, size: float, offset: float = 0.0, italic: bool = False, i: int = 0, runs=None):
    """Split markup into runs of (text, italic, baseline offset, font size)."""
    runs = [] if runs is None else runs
    buf = ""

    def flush():
        nonlocal buf
        if buf:
            runs.append((buf, italic, offset, size))
            buf = ""

    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            buf += s[i + 1]
            i += 2
        elif c == "}":
            flush()
            return runs, i + 1, italic
        elif c == "*":
            flush()
            italic = not italic
            i += 1
        elif c in "_^" and s[i + 1:i + 2] == "{":
            flush()
            shift = 0.28 * size if c == "_" else -0.38 * size
            _, i, _ = parse_markup(s, size * 0.7, offset + shift, italic, i + 2, runs)
        else:
            buf += c
            i += 1
    flush()
    return runs, i, italic


def rich(s: str, size: float) -> str:
    """Render markup as escaped SVG text content with tspans."""
    runs, _, _ = parse_markup(s, size)
    out, current = [], 0.0
    for value, italic, offset, run_size in runs:
        attrs = ""
        if offset != current:
            attrs += f' dy="{offset - current:.1f}"'
            current = offset
        if run_size != size:
            attrs += f' font-size="{run_size:.1f}"'
        if italic:
            attrs += ' font-style="italic" font-family="Cambria,Times New Roman,serif"'
        out.append(f"<tspan{attrs}>{escape(value)}</tspan>" if attrs else escape(value))
    return "".join(out)


class Figure:
    """Accumulates SVG parts; module details feed the HTML side panel."""

    def __init__(self, width: int, height: int, title: str, desc: str):
        self.width, self.height = width, height
        self.title, self.desc = title, desc
        self.parts: list[str] = []
        self.modules: dict[str, str] = {}
        self.sections: list[tuple[str, str]] = []
        self.summaries: dict[str, str] = {"all": desc}
        self.rect(0, 0, width, height, "#FFF")

    # -- primitives -------------------------------------------------------
    def text(self, x, y, value, cls="", anchor="start", raw=False, fill=None):
        size = SIZES.get(cls.split()[0] if cls else "", 26)
        body = escape(value) if raw else rich(value, size)
        extra = f' fill="{fill}"' if fill else ""
        self.parts.append(f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}"{extra}>{body}</text>')

    def rect(self, x, y, w, h, fill="#FFF", **attrs):
        extra = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" {extra}/>')

    def line(self, points, kind="forward"):
        d = "M" + " L".join(f"{x},{y}" for x, y in points)
        self.parts.append(f'<path d="{d}" class="{kind}" marker-end="url(#{kind})"/>')

    def raw(self, svg: str):
        self.parts.append(svg)

    # -- structure --------------------------------------------------------
    def section(self, key, y, h, title, source="", nav=None, summary=""):
        """Dashed region. nav: HTML button label (defaults to key). summary: what the HTML
        panel shows when this view is selected; without it the panel lists the modules."""
        self.sections.append((key, nav or key))
        if summary:
            self.summaries[key] = summary
        self.parts.append(f'<g id="section-{key}" data-section="{key}">')
        self.rect(20, y, self.width - 40, h, "none", stroke="#C9CED4", stroke_width="1.4", stroke_dasharray="7 5")
        self.text(40, y + 42, title, "heading")
        if source:
            self.text(self.width - 40, y + 42, source, "note", "end")

    def end(self):
        self.parts.append("</g>")

    def pill(self, x, y, state):
        if state == "trainable":
            self.rect(x, y, 88, 32, "#C8743A", rx="16")
            self.text(x + 44, y + 24, "可训练", "body bold", "middle", fill="#FFF")
        else:
            self.rect(x, y, 70, 32, "#FFF", rx="16", stroke="#6F7C8B", stroke_width="1.6")
            self.text(x + 35, y + 24, "冻结", "body", "middle", fill="#4F5B68")

    def box(self, key, x, y, w, h, title, rows, detail, kind="neutral", state=None,
            tag=None, inner=None, title_y=40):
        """Module box.

        rows: [(y offset, markup, css class)], centred. detail: HTML panel / tooltip text.
        kind: modality fill (FILLS). state: None | "trainable" | "frozen" (border + pill at
        the top-left, leaving the top-right free for inheritance ports). tag: bottom line,
        e.g. the checkpoint a model-view module uses. inner: callback drawing sub-shapes.
        """
        self.modules[key] = detail
        fill, border = FILLS[kind]
        label = escape(title.replace("*", ""))
        self.parts.append(f'<g data-module="{key}" data-label="{label}">')
        self.parts.append(f"<title>{escape(detail)}</title>")
        style = (TRAINABLE if state == "trainable" else FROZEN if state == "frozen"
                 else dict(stroke=border, stroke_width="1.6"))
        self.rect(x, y, w, h, fill, rx="12", **{"class": "module-bg"}, **style)
        if inner:
            inner()
        self.text(x + w / 2, y + title_y, title, "bold", "middle")
        for offset, value, cls in rows:
            self.text(x + w / 2, y + offset, value, cls, "middle")
        if tag:
            self.text(x + w / 2, y + h - 14, tag, "note", "middle", fill="#5A5A5A")
        if state:
            self.pill(x + 12, y - 16, state)
        self.end()

    # -- legend and notes -------------------------------------------------
    def legend_lines(self, x, y, kinds=("forward", "supervise", "gradient", "inherit"), step=None, labels=None):
        """One row of line samples; only list kinds the figure actually uses."""
        labels = {**LINE_LABELS, **(labels or {})}
        for kind in kinds:
            self.line([(x, y - 8), (x + 60, y - 8)], kind)
            self.text(x + 76, y, labels[kind], "body")
            x += step or (76 + text_width(labels[kind]) + 40)
        return x

    def legend_boxes(self, x, y, states=("trainable", "frozen"), modalities=None, labels=None):
        """Box-encoding legend: state borders, a neutral box, then the modality fills used."""
        labels = {**STATE_LABELS, **MODALITY_LABELS, "neutral": "数据 / 损失 / 运算", **(labels or {})}
        items = [(labels[s], dict(fill="#FFF", **(TRAINABLE if s == "trainable" else FROZEN))) for s in states]
        items.append((labels["neutral"], dict(fill="#FFF", stroke="#9AA5B1", stroke_width="1.6")))
        items += [(labels[k], dict(fill=FILLS[k][0], stroke=FILLS[k][1], stroke_width="1.4")) for k in modalities or ()]
        for label, style in items:
            self.rect(x, y - 24, 52, 30, rx="6", **style)
            self.text(x + 64, y, label, "body")
            x += 64 + text_width(label) + 36
        return x

    def notes(self, x, y, lines, leading=34):
        for k, line in enumerate(lines):
            self.text(x, y + leading * k, line, "note")

    # -- output -----------------------------------------------------------
    def svg(self) -> str:
        markers = "\n".join(
            f'<marker id="{kind}" markerUnits="userSpaceOnUse" viewBox="0 0 10 10" markerWidth="12" '
            f'markerHeight="12" refX="10" refY="5" orient="auto"><path d="M0 0L10 5L0 10Z" fill="{color}"/></marker>'
            for kind, color in LINE_COLORS.items())
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
                f'viewBox="0 0 {self.width} {self.height}" role="img" aria-labelledby="title desc">\n'
                f'<title id="title">{escape(self.title)}</title>\n<desc id="desc">{escape(self.desc)}</desc>\n'
                f"<defs>\n{markers}\n<style>\n{CSS}\n</style></defs>")
        return "\n".join([head, *self.parts, "</svg>"])

    def html(self, svg: str | None = None, intro: str = "") -> str:
        svg = svg or self.svg()
        buttons = ['<button data-view="all" aria-pressed="true">完整总览</button>'] + [
            f'<button data-view="{key}" aria-pressed="false">{escape(label)}</button>' for key, label in self.sections]

        def script_json(data):  # keep a "</script>" inside a string from closing the tag
            return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

        return (HTML_TEMPLATE.replace("__TITLE__", escape(self.title))
                .replace("__INTRO__", escape(intro or DEFAULT_INTRO)).replace("__HINT__", escape(HINT))
                .replace("__BUTTONS__", "\n".join(buttons)).replace("__SVG__", svg)
                .replace("__MODULES__", script_json(self.modules))
                .replace("__SUMMARIES__", script_json(self.summaries))
                .replace("__HINT_JSON__", script_json(HINT)))

    def save(self, directory, stem, intro: str = ""):
        directory = Path(directory)
        svg = self.svg()
        (directory / f"{stem}.svg").write_text(svg, encoding="utf-8")
        (directory / f"{stem}.html").write_text(self.html(svg, intro), encoding="utf-8")
        return directory / f"{stem}.svg", directory / f"{stem}.html"


HINT = "点击图中的任一模块，查看它的输入、运算、输出、更新状态和原文依据。"
DEFAULT_INTRO = ("点击图中的模块（或用 Tab 选中后按 Enter / 空格）查看模块说明；"
                 "用上方按钮切换视角，说明框会显示该分区的概要。")

HTML_TEMPLATE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
body{margin:0;padding:20px;font:17px/1.6 system-ui,sans-serif;color:#171717;background:white}
main{max-width:1500px;margin:auto}h1{font-size:25px;margin:0 0 8px}
nav{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
button{font:inherit;padding:6px 14px;border:1px solid #aab6c2;background:#edf3f9;border-radius:4px;cursor:pointer}
button[aria-pressed=true]{background:#dfe7f1;border-color:#1f3a5f}
button:focus-visible{outline:3px solid #1f3a5f;outline-offset:2px}
.scroll{overflow:auto;border:1px solid #ddd}.scroll svg{display:block;width:100%;min-width:1050px;height:auto}
[data-module]{cursor:pointer}#detail{padding:12px;border-left:3px solid #1f3a5f;background:#eef2f7;min-height:65px;overflow-wrap:anywhere}
.note{color:#555;font-size:14px}#test-result{white-space:pre-wrap}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}
</style></head><body><main>
<h1>__TITLE__</h1>
<p class="note">__INTRO__</p>
<nav aria-label="视角">
__BUTTONS__
</nav>
<p id="detail" role="status" aria-live="polite">__HINT__</p>
<div class="scroll" aria-label="可横向滚动的完整图">__SVG__</div>
<noscript><p>脚本未启用：上方静态图仍包含完整结构。</p></noscript>
<pre id="test-result" hidden></pre>
</main><script>
'use strict';
const descriptions = __MODULES__;
const summaries = __SUMMARIES__;
const HINT = __HINT_JSON__;
const buttons = [...document.querySelectorAll('[data-view]')];
const sections = [...document.querySelectorAll('[data-section]')];
const moduleNodes = [...document.querySelectorAll('[data-module]')];
const detail = document.getElementById('detail');
// Interactive semantics only exist here; the standalone SVG stays a plain image.
moduleNodes.forEach(n => {
  n.setAttribute('tabindex', '0');
  n.setAttribute('role', 'button');
  n.setAttribute('aria-label', n.dataset.label);
});
// Panel text for a view: its summary, or else the modules it contains.
function viewText(view) {
  const button = buttons.find(b => b.dataset.view === view);
  const name = button ? button.textContent.trim() : view;
  if (summaries[view]) return name + '：' + summaries[view] + ' ' + HINT;
  const section = sections.find(s => s.dataset.section === view);
  const labels = section ? [...section.querySelectorAll('[data-module]')].map(n => n.dataset.label) : [];
  return labels.length ? name + '包含：' + labels.join('、') + '。' + HINT : HINT;
}
function setView(view) {
  buttons.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.view === view)));
  sections.forEach(s => s.classList.toggle('dimmed', view !== 'all' && s.dataset.section !== view));
  moduleNodes.forEach(n => n.classList.remove('selected'));
  detail.textContent = viewText(view);
}
function selectModule(node) {
  moduleNodes.forEach(n => n.classList.toggle('selected', n === node));
  detail.textContent = descriptions[node.dataset.module];
}
buttons.forEach(b => b.addEventListener('click', () => setView(b.dataset.view)));
moduleNodes.forEach(n => {
  n.addEventListener('click', () => selectModule(n));
  n.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectModule(n); }
  });
});
if (new URLSearchParams(location.search).has('test')) {
  const checks = [];
  checks.push(detail.textContent === HINT);
  for (const b of buttons) {
    detail.textContent = '';
    b.click();
    checks.push(b.getAttribute('aria-pressed') === 'true' &&
      sections.every(s => s.classList.contains('dimmed') ===
        (b.dataset.view !== 'all' && s.dataset.section !== b.dataset.view)));
    // Every view must explain itself, not fall back to the bare hint.
    checks.push(detail.textContent === viewText(b.dataset.view) && detail.textContent !== HINT);
  }
  for (const n of moduleNodes) {
    n.dispatchEvent(new MouseEvent('click', {bubbles:true}));
    checks.push(detail.textContent === descriptions[n.dataset.module]);
    for (const key of ['Enter', ' ']) {
      detail.textContent = '';
      n.dispatchEvent(new KeyboardEvent('keydown', {key, bubbles:true}));
      checks.push(detail.textContent === descriptions[n.dataset.module]);
    }
  }
  checks.push(document.documentElement.scrollWidth <= innerWidth);
  setView('all');
  detail.textContent = HINT;
  const result = document.getElementById('test-result');
  result.hidden = false;
  result.textContent = checks.every(Boolean) ? 'SELFTEST PASS: '+checks.length+' checks' : 'SELFTEST FAIL';
  document.body.dataset.selfTest = checks.every(Boolean) ? 'pass' : 'fail';
}
</script></body></html>
"""
