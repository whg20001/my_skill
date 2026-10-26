# Deep Paper Reader · 论文精读与讲解 Skill

**用途**：让 AI 助手（Claude Code / Claude.ai / Codex）像一位严谨又会讲课的导师一样，带你读懂 AI、机器学习、深度学习论文，以及以 ML 方法为核心的交叉领域论文（EEG/脑机接口解码、医学影像、稀疏学习、信号处理等）。从 **PDF**、**arXiv 链接**或粘贴的正文出发，输出**中文 Markdown**：先讲直觉和全局，再讲公式与实验，所有关键论断带原文定位，并区分原文事实、解释、背景知识与推测。

本 Skill 不接入第三方知识库，不内置论文全文，也不保证运行环境可联网。若 arXiv 全文无法访问，它会要求上传 PDF；只读取到摘要时不会冒充全文分析。

## 四种模式

| 模式 | 适合 | 产出 |
|---|---|---|
| `quick` 速览 | 判断值不值得读、先有个整体印象 | 一屏论文地图 + 建议精读顺序 |
| `full` 精读 | 系统读懂一篇论文 | 10 节笔记文件 `paper-<id>-deep-read.md` |
| `focused` 定向 | 卡在某个公式/图/表/模块 | 直接、聚焦的解释 |
| `interactive` 带读 | 想被一步步带着学 | 每轮一个单元 + 理解检查 + 下一步选项 |

另外，提到“组会汇报”或“复现”时，会额外给出汇报提纲或复现信息清单。

## 内容清单

```text
deep-paper-reader/
├── SKILL.md                         入口：目标、底线、模式路由、讲解原则、证据纪律
├── agents/openai.yaml               Codex UI 名称、默认提示词与调用策略
├── references/
│   ├── teaching-playbook.md         讲解技法：直觉、类比、读图、分层、带读节奏、出题
│   ├── deep-reading-workflow.md     9 阶段深度阅读流程
│   ├── method-and-formula.md        方法/模型/算法/数学解释
│   ├── experiment-analysis.md       实验与消融证据审查
│   ├── critical-review.md           批判性评价与研究问题
│   ├── domain-patterns.md           子领域特化（含稀疏学习、EEG/BCI、时序）
│   ├── output-contract.md           四种模式的输出规范
│   ├── interactive-svg.md           增强型 Markdown + 交互式 SVG、公式微演示
│   └── architecture-style.md        架构 / 训练总览图规范、常见错误速查与验收清单
├── assets/
│   ├── reading-note-template.md     中文全文精读笔记模板
│   └── architecture-style-reference.svg     架构 / 训练总览图的完整样例（E²-LLM）
├── scripts/
│   ├── lint_report.py               本地 Markdown 结构校验（full / quick / focused）
│   ├── svg_figure_kit.py            架构图生成工具（状态编码、连线、公式标记、SVG + HTML）
│   └── check_figure.py              配图机械检查、PNG 渲染切片与 HTML 自检
└── tests/
    ├── test-prompts.md              15 个手动验收测试
    ├── test_lint_report.py          结构脚本自动测试
    ├── test_figure_tools.py         配图工具自动测试
    ├── test_skill_structure.py      资源一致性自动测试
    └── fixtures/
        ├── synthetic-mini-paper.md
        └── expected-mini-report.md
```

## 安装

- **Claude Code**：把 `deep-paper-reader/` 放到 `~/.claude/skills/`（全局）或项目的 `.claude/skills/`（项目级）。
- **Claude.ai / Claude 桌面版**：在 设置 → Capabilities → Skills 中上传打包好的 zip（zip 内顶层为 `deep-paper-reader/` 目录）。
- **Codex**：放到 `~/.codex/skills/`（全局）或项目仓库的 `.agents/skills/`，重启后用 `/skills` 或 `$` 确认已列出。

## 使用示例

- `帮我看看这篇论文讲了什么，值不值得精读。`（附 PDF）→ `quick`
- `请深度精读工作目录里的这篇论文，重点讲清公式和实验。` → `full`
- `只解释 Eq.(7) 和 Fig.2 怎么对应，给出张量形状和一个小例子。` → `focused`
- `我有 ML 基础但没接触过 Group LASSO，带我一步步读这篇 EEG 解码论文。` → `interactive`
- `请深度精读 https://arxiv.org/abs/1706.03762 ，先确认能读到的全文范围和版本。`

`full` 模式默认把笔记写入工作目录，对话中只返回覆盖说明和核心结论；如要在对话中直接输出全文，请在提示词中说明。

## 验收与维护

- **手动测试提示词与评分规则**：`tests/test-prompts.md`。
- **自动结构测试**：在本目录执行 `python -m unittest discover -s tests -v`。
- **笔记结构检查**：`python scripts/lint_report.py 你的笔记.md --mode full`（或 `quick` / `focused`）。`assets/` 模板含 `{{...}}` 占位符，直接检查必然报错，属预期。
- **配图检查**：`python scripts/check_figure.py 图.svg --render 预览.png --slices 3 --html 图.html`。会检查 XML、id 引用、7 pt 字号下限、静态 SVG 中残留的交互属性和框内免责注释，并输出渲染切片，供逐段目视检查（渲染需要本机装有 Edge 或 Chrome）。
- **科学真实性检查**：手动对照原文复核关键公式、数值、图表、消融和论文版本；结构检查无法取代原文核查。

## 范围限制

本 Skill 是一套阅读与讲解指令和模板，**不是离线论文解析器**，也不是论文数据库。PDF 图表识别、联网和文件保存依赖当前会话可用的工具（原生 PDF 读取、pdftotext / pdftoppm、网络权限等）；缺少能力时会降级并说明，而不编造结果。

## 更新记录

**v3：架构图绘制**
- `architecture-style.md` 重写：填充色表示模态，可训练 / 冻结用边框加标签表示；新增监督线，梯度线要穿过冻结模块；模型区标注推理时使用的权重来源；各阶段同一模块同列；每组继承参数都画继承线；结果区优先放基线与消融；字号按 7 pt 换算；免责注释移入编号图注；统一语言和记号，上下标用 `tspan dy`；新增“常见错误速查”。这些规则来自对 E²-LLM 架构图的 17 条审查意见。
- 新增 `scripts/svg_figure_kit.py`（生成工具）、`scripts/check_figure.py`（检查与渲染）、`tests/test_figure_tools.py`，并用按新规范绘制的 E²-LLM 图覆盖 `assets/architecture-style-reference.svg`（原 BLA 样例已移除）。
- `interactive-svg.md` 同步：选中高亮改为深蓝描边（橙色已表示可训练），交互属性只由 HTML 脚本添加。

**v2**
- 新增 `quick` 速览模式；未指明需求时先速览，再询问是否精读或带读。
- 新增 `references/teaching-playbook.md`：“卡点 → 直觉 → 形式 → 例子 → 回到原文 → 边界”讲解骨架、读者分层、前置知识桥接、类比规范、读图法、带读节奏、理解检查题设计、组会汇报与复现视角。
- 新增 `[背景知识]` 标签，区分通识补充与论文内容，解决“讲前置概念”与“不得编造原文”之间的冲突。
- `domain-patterns.md` 新增稀疏/正则化模型与凸优化、EEG/脑机接口/生理信号解码、时序建模三节（重点：被试内/跨被试协议、时间相关泄漏、组结构依据）。
- 笔记模板新增术语表、模块“卡点/一句话直觉”、复现要点表、理解检验答题要点。
- SKILL.md 重写：去除与 references 重复的规则，用“为什么”代替生硬禁令；PDF 读取改为环境自适应（原生 PDF 读取优先，其次 pdftotext / PyMuPDF）；描述扩展触发场景并补充交叉领域。
- `lint_report.py`：修复 Windows 控制台输出中文时的 `UnicodeEncodeError`；新增 `--mode quick`；新增证据索引条数不足、“提升 X%”歧义表述的警告。
