# my_skill

个人 AI 助手技能仓库，收集可复用的任务指令、参考资料、输出模板和辅助脚本。当前包含 **Deep Paper Reader**，用于 AI / 机器学习论文的中文精读与讲解。

## 技能目录

| 技能 | 用途 | 入口 |
| --- | --- | --- |
| [deep-paper-reader](deep-paper-reader/README.md) | 论文速览、全文精读、公式与图表讲解、逐步带读，以及组会汇报和复现准备 | [SKILL.md](deep-paper-reader/SKILL.md) |

## Deep Paper Reader 能做什么

从 PDF、arXiv 链接或粘贴的论文正文出发，先讲问题和直觉，再解释方法、公式与实验。适用于 AI、机器学习、深度学习，以及以 ML 方法为核心的交叉领域论文，例如 EEG / 脑机接口、医学影像、稀疏学习和时序建模。

| 模式 | 适用场景 | 输出 |
| --- | --- | --- |
| `quick` 速览 | 了解论文主旨，判断是否值得精读 | 论文地图、核心想法、关键结果与建议阅读顺序 |
| `full` 精读 | 系统理解一篇论文 | 包含 10 节内容的中文 Markdown 笔记 `paper-<id>-deep-read.md` |
| `focused` 定向 | 理解指定公式、图表、模块或实验 | 结合必要上下文的聚焦解释 |
| `interactive` 带读 | 按学习进度逐步阅读 | 固定学习地图、逐单元讲解、理解检查与下一步选项 |

讲解区分 `[原文事实]`、`[解释性分析]`、`[背景知识]` 和 `[推测/待验证]`，关键论断附章节、公式、图表等原文定位。读取范围以 `complete`、`partial` 或 `abstract-only` 标明。

还提供笔记模板、架构图 SVG / HTML 生成工具，以及笔记结构和配图检查脚本。

## 获取与使用

```bash
git clone https://github.com/whg20001/my_skill.git
cd my_skill
```

将完整的 `deep-paper-reader/` 目录安装到所用 AI 助手支持的技能目录，保留 `references/`、`assets/`、`scripts/` 等子目录。不同助手的安装方式见 [技能安装说明](deep-paper-reader/README.md#安装)。

安装后，在对话中附上论文 PDF、提供可访问的 arXiv 链接，或粘贴正文，再说明阅读目标，例如：

```text
帮我看看这篇论文讲了什么，值不值得精读。
```

```text
请完整精读工作目录中的论文，重点讲清模型结构、关键公式和消融实验，
把中文笔记保存为 Markdown，并为关键结论标出原文位置。
```

```text
只解释 Eq.(7) 与 Fig.2 的对应关系，给出变量含义、张量形状和最小例子。
```

```text
我有机器学习基础，但不熟悉 Group LASSO。请带我一步步读这篇 EEG 解码论文。
```

`full` 模式默认保存笔记文件，在对话中返回核心结论和文件路径；其他模式直接在对话中讲解。详细行为以 [技能入口](deep-paper-reader/SKILL.md) 和 [输出规范](deep-paper-reader/references/output-contract.md) 为准。

## 项目结构

```text
my_skill/
├── README.md
├── .gitignore
└── deep-paper-reader/
    ├── SKILL.md                         # 技能入口与模式路由
    ├── README.md                        # 安装、使用与更新说明
    ├── agents/openai.yaml               # 助手界面配置
    ├── references/                      # 阅读流程、教学方法、公式与实验分析、配图规范
    ├── assets/                          # 精读笔记模板与架构图样例
    ├── scripts/
    │   ├── lint_report.py               # Markdown 笔记结构检查
    │   ├── svg_figure_kit.py            # SVG 与交互式 HTML 架构图生成工具
    │   └── check_figure.py              # SVG 检查、可选 PNG 渲染及 HTML 自检
    └── tests/                           # 自动测试、合成样例与手动验收提示词
```

## 本地检查

技能指令本身无需安装 Python 包。运行辅助脚本与自动测试需要 Python；本仓库在 Python 3.13 环境下验证。结构检查和 SVG 生成使用 Python 标准库；PNG 渲染与 HTML 自检需要可被脚本发现的 Edge / Chrome / Chromium，PNG 切片另需可选依赖 Pillow。

以下命令均在**仓库根目录**执行。

运行现有自动测试：

```bash
python -B -m unittest discover -s deep-paper-reader/tests -v
```

检查内置笔记样例和架构图：

```bash
python -B deep-paper-reader/scripts/lint_report.py deep-paper-reader/tests/fixtures/expected-mini-report.md --mode full
python -B deep-paper-reader/scripts/check_figure.py deep-paper-reader/assets/architecture-style-reference.svg
```

检查自己的笔记（将路径替换为实际文件）：

```bash
python -B deep-paper-reader/scripts/lint_report.py paper-example-deep-read.md --mode full
```

`--mode` 支持 `full`、`quick`、`focused`。笔记模板含待填写占位符，应完成填写后再检查。

配图生成接口参见 [svg_figure_kit.py](deep-paper-reader/scripts/svg_figure_kit.py)，渲染和自检参数可通过以下命令查看：

```bash
python -B deep-paper-reader/scripts/check_figure.py --help
```

手动验收场景与评分规则见 [tests/test-prompts.md](deep-paper-reader/tests/test-prompts.md)。

## 能力边界

- PDF 解析、页面图像读取、联网与文件保存依赖当前 AI 助手会话提供的工具。无法取得全文时，讲解应明确实际读取范围。
- 笔记检查脚本验证章节、覆盖状态、原文锚点和残留占位符；科学结论、公式、数值及引文仍需对照原文核实。
- 配图检查脚本验证 XML、引用、字号等机械规则；模型拓扑、训练状态和数据流仍需人工核对。

## 维护约定

每个技能使用独立目录，以 `SKILL.md` 为入口；按需添加参考资料、模板、脚本和测试。修改后同步对应技能的 README，并从仓库根目录运行相关检查。Python 缓存和本地虚拟环境由 `.gitignore` 排除。
