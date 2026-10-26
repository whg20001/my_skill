#!/usr/bin/env python3
"""Mechanical checks for a teaching SVG figure, plus optional headless rendering.

Checks: XML, root title/desc, unique ids, url(#id) references, interactive
attributes leaking into the static SVG, minimum printed font size, and in-figure
disclaimer text that belongs in the caption notes. It does NOT check whether the
figure matches the paper; compare modules, data flow and training states yourself.

Usage:
    python scripts/check_figure.py figure.svg
    python scripts/check_figure.py figure.svg --target-width-pt 241      # one-column figure
    python scripts/check_figure.py figure.svg --render out.png --slices 3 # PNG + slices to inspect
    python scripts/check_figure.py figure.svg --html figure.html          # run the HTML self-test
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Tuple

SVG_NS = "{http://www.w3.org/2000/svg}"
CLASS_RULE = re.compile(r"((?:\.[\w-]+\s*,?\s*)+)\{([^}]*)\}")
BASE_RULE = re.compile(r"(?:^|[}\s])text\s*\{([^}]*)\}")
FONT_SIZE = re.compile(r"font-size\s*:\s*([\d.]+)px")
# Negative asides inside module boxes ("非图像""不补造……") read as noise; move them to notes.
DISCLAIMER = re.compile(r"^(?:非|不是|并非)|不补造|不虚构|不臆造|不能据此|仅为?示意|机制示意，不是")
BROWSERS = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
)


def css_sizes(root: ET.Element) -> Tuple[Optional[float], dict]:
    css = "\n".join(el.text or "" for el in root.iter(f"{SVG_NS}style"))
    base = None
    match = BASE_RULE.search(css)
    if match and FONT_SIZE.search(match.group(1)):
        base = float(FONT_SIZE.search(match.group(1)).group(1))
    sizes = {}
    for selectors, body in CLASS_RULE.findall(css):
        size = FONT_SIZE.search(body)
        if size:
            for name in re.findall(r"\.([\w-]+)", selectors):
                sizes[name] = float(size.group(1))  # later rules win, as in CSS
    return base, sizes


def effective_size(el: ET.Element, base: Optional[float], sizes: dict) -> float:
    attr = el.get("font-size")
    if attr and attr.replace(".", "", 1).isdigit():
        return float(attr)
    found = [sizes[c] for c in (el.get("class") or "").split() if c in sizes]
    return found[-1] if found else (base or 16.0)


def check_svg(content: str, target_width_pt: float = 504, min_pt: float = 7) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        return [f"SVG 不是合法 XML：{exc}"], warnings

    viewbox = (root.get("viewBox") or "").split()
    try:
        width = float(viewbox[2]) if len(viewbox) == 4 else float(root.get("width", "0").rstrip("px"))
    except ValueError:
        width = 0.0
    if not width:
        errors.append("缺少 viewBox 或宽度，无法换算打印字号")

    children = [c.tag for c in root]
    if f"{SVG_NS}title" not in children or f"{SVG_NS}desc" not in children:
        warnings.append("根节点缺少 <title> 或 <desc>")

    ids = [el.get("id") for el in root.iter() if el.get("id")]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        errors.append("重复 id：" + "、".join(duplicates[:5]))
    known = set(ids)
    missing = sorted({ref for ref in re.findall(r"url\(#([^)]+)\)", content) if ref not in known})
    if missing:
        errors.append("引用了不存在的 id：" + "、".join(missing[:5]))

    leaked = [el for el in root.iter() if el is not root and (el.get("role") == "button" or el.get("tabindex"))]
    if leaked:
        errors.append(f"静态 SVG 中有 {len(leaked)} 个 role=button / tabindex 元素；"
                      "作为图片时它们无法交互，应改由 HTML 的脚本添加")

    if width:
        base, sizes = css_sizes(root)
        floor_px = min_pt * width / target_width_pt
        small = []
        for el in root.iter(f"{SVG_NS}text"):
            size = effective_size(el, base, sizes)
            if size < floor_px - 1e-6:
                small.append((size, "".join(el.itertext()).strip()[:24]))
        if small:
            size, sample = min(small)
            errors.append(f"{len(small)} 处文字缩放到 {target_width_pt:g} pt 宽时小于 {min_pt:g} pt "
                          f"（最小 {size:g}px ≈ {size * target_width_pt / width:.1f} pt，例如“{sample}”）；"
                          f"该画布宽度下正文至少 {floor_px:.1f}px（上下标按 70% 另计）")

    asides = []
    for group in root.iter(f"{SVG_NS}g"):
        if group.get("data-module") is None:
            continue
        for el in group.iter(f"{SVG_NS}text"):
            value = "".join(el.itertext()).strip()
            if DISCLAIMER.search(value):
                asides.append(value)
    if asides:
        warnings.append(f"模块框内有 {len(asides)} 条疑似免责/元注释（例如“{asides[0][:20]}”）；"
                        "建议移入图注或交互说明面板")

    texts = [el for el in root.iter(f"{SVG_NS}text")]
    if len(texts) > 0 and not any("注" in "".join(el.itertext())[:3] for el in texts):
        warnings.append("未发现图注（以“注”开头的文字）；未报告项、推断机制和省略项应集中写在图注里")
    return errors, warnings


def find_browser() -> Optional[str]:
    for name in ("msedge", "chrome", "google-chrome", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
    return next((p for p in BROWSERS if os.path.exists(p)), None)


def file_url(path: Path) -> str:
    return path.resolve().as_uri()


def render(svg: Path, out: Path, width: int, height: int, scale: float, slices: int) -> List[str]:
    browser = find_browser()
    if not browser:
        return ["未找到 Edge / Chrome，无法渲染；请用其他方式打开 SVG 目视检查"]
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    f"--force-device-scale-factor={scale}", f"--window-size={width},{height}",
                    f"--screenshot={out.resolve()}", file_url(svg)],
                   capture_output=True, timeout=120)
    if not out.exists():
        return [f"渲染失败：{browser} 没有生成 {out}"]
    notes = [f"已渲染：{out}"]
    if slices > 1:
        try:
            from PIL import Image
        except ImportError:
            return notes + ["未安装 Pillow，跳过切片；请直接查看整张 PNG"]
        image = Image.open(out)
        step = image.height / slices
        for k in range(slices):
            part = out.with_name(f"{out.stem}_part{k + 1}{out.suffix}")
            image.crop((0, int(k * step), image.width, int(min(image.height, (k + 1) * step + 20)))).save(part)
            notes.append(f"切片：{part}")
    return notes


def html_selftest(html: Path) -> str:
    browser = find_browser()
    if not browser:
        return "未找到 Edge / Chrome，无法运行 HTML 自检"
    result = subprocess.run([browser, "--headless=new", "--disable-gpu", "--window-size=1400,900",
                             "--virtual-time-budget=3000", "--dump-dom", file_url(html) + "?test"],
                            capture_output=True, timeout=120)
    dom = result.stdout.decode("utf-8", "replace")
    match = re.search(r'id="test-result"[^>]*>(SELFTEST [^<]*)<', dom)
    return match.group(1) if match else "未找到 SELFTEST 结果（页面可能没有内置自检）"


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("svg", type=Path)
    parser.add_argument("--target-width-pt", type=float, default=504,
                        help="排版宽度：504 = 双栏通栏 7 in（默认），241 = 单栏")
    parser.add_argument("--min-pt", type=float, default=7)
    parser.add_argument("--render", type=Path, help="渲染为 PNG 的输出路径")
    parser.add_argument("--scale", type=float, default=1)
    parser.add_argument("--slices", type=int, default=1, help="把 PNG 横切成几段，便于逐段查看")
    parser.add_argument("--html", type=Path, help="同时运行交互版 HTML 的 ?test 自检")
    args = parser.parse_args()
    try:
        content = args.svg.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: 无法读取 {args.svg}: {exc}")
        return 2

    errors, warnings = check_svg(content, args.target_width_pt, args.min_pt)
    for item in errors:
        print(f"ERROR: {item}")
    for item in warnings:
        print(f"WARN: {item}")
    if args.render and not errors:
        root = ET.fromstring(content)
        box = [float(v) for v in (root.get("viewBox") or "0 0 1600 1200").split()]
        for note in render(args.svg, args.render, int(box[2]), int(box[3]), args.scale, args.slices):
            print(f"INFO: {note}")
    if args.html:
        print(f"INFO: HTML 自检：{html_selftest(args.html)}")
    if errors:
        print("FAIL: 图形检查未通过。")
        return 1
    print("PASS: 机械检查通过。仍需渲染后目视检查，并逐项对照原文核对结构与训练状态。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
