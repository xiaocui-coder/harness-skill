---
name: harness
description: |
  Harness — 自动生成项目专属代码验证约束，持续提升 Claude Code 代码生成精度。
  将「什么是本项目中的有效代码变更」以自然语言规则和可执行验证脚本双重形式自动生成。

  使用时机：
  - `/harness-init` — 用户输入此命令时，执行项目首次初始化
  - `/harness-update` — 代码生成任务结束后、出现类型错误/测试失败/lint错误时、
    收到用户反馈（"不对"、"我想要这样"、"我们这里用XXX"等）时、
    或用户显式输入 /harness-update 时。
    无需用户输入命令，检测到上述信号时应自主执行。
---

# Harness 技能

## 概念

通过自动生成代码验证约束，防止 Claude Code 产生「无效代码变更」。

在 Claude Code 中，「无效变更」指的是：
- 导致类型错误/编译错误的代码
- 破坏测试的代码
- 违反 lint 规则的代码
- 违反项目特有命名规范/结构规则的代码

为防止这些问题，需要同时生成和维护：
1. **自然语言规则**（`.claude/rules/harness.md`）— Claude Code 参照并内化
2. **验证脚本**（本技能的 `scripts/generate_harness_check.py`）— 实际执行代码进行验证

---

## 命令: `/harness-init`

**目的:** 首次解析项目并生成约束

### 步骤

#### Step 1: 项目分析

检查以下内容（并行执行）：

```
- 语言/框架: package.json / pyproject.toml / Cargo.toml / go.mod 等
- 测试命令: scripts、Makefile、README
- Lint 工具: .eslintrc、.flake8、ruff.toml、biome.json 等
- 类型检查: tsconfig.json、mypy.ini、pyrightconfig.json 等
- 构建命令: CI 配置（.github/workflows/、.gitlab-ci.yml）
- 命名规范/文件结构: 采样数个已有代码文件的模式
- CLAUDE.md: 如有已有规则则读取
```

#### Step 2: 约束规则生成

根据分析结果生成 `.claude/rules/harness.md`，包含以下章节：

```markdown
# Harness 规则

## 验证命令
本项目用于验证代码正确性的命令：
- 类型检查: `<命令>`
- 测试: `<命令>`
- Lint: `<命令>`
- 构建: `<命令>`

## 有效代码变更的条件 (is_legal_change)
1. ...
2. ...

## 命名规范
- 文件名: ...
- 函数名: ...
- 变量名: ...

## 禁止模式
- ...

## 项目特有注意事项
- ...
```

#### Step 3: 验证脚本生成

生成 `.claude/rules/harness_check.py`，该脚本：
- 通过 `python .claude/rules/harness_check.py [目标文件路径...]` 执行
- 内部调用项目的类型检查、lint、测试
- 以 JSON 格式输出结果（`{"passed": true/false, "errors": [...], "warnings": [...]}`）

脚本实现参考 `scripts/generate_harness_check.py` 模板（详见后文）。

#### Step 4: CLAUDE.md 引用追加

在 `CLAUDE.md` 末尾追加以下内容（保留已有内容）：

```markdown
## Harness

@.claude/rules/harness.md

本项目的代码验证规则见 `.claude/rules/harness.md`。
代码变更前后可通过 `python .claude/rules/harness_check.py <文件>` 执行验证。
```

#### Step 5: 完成报告

向用户报告：
- 生成的文件列表
- 检测到的主要约束（类型检查工具名、测试命令等）
- 通过 `python .claude/rules/harness_check.py --help` 可查看用法

---

## 命令: `/harness-update`

**目的:** 基于反馈和失败结果改进约束

此命令在以下场景使用：
- 用户显式输入 `/harness-update`
- 代码生成后出现类型错误、测试失败、lint 错误
- 用户表示"这个输出有问题"、"不对"、"我想要这样"

### 步骤

#### Step 1: 失败分析

从当前对话、错误消息、差异中确定「什么失败了」：

```
- 错误类型（类型错误 / 测试失败 / lint / 逻辑错误 / 风格违规）
- 失败的文件和行号
- 根本原因（规则缺失 / 规则模糊 / 脚本未覆盖）
```

#### Step 2: 约束弱点识别

按精炼循环的思路进行思考：

> 验证返回「通过」但实际是非法操作 → 验证函数有遗漏
> 验证返回「失败」但实际是合法操作 → 验证函数过度约束

在 Claude Code 的上下文中：
- 规则中已有但生成了违规代码 → 规则说明不够明确
- 规则中未涉及的失败场景 → 需要新增规则
- 脚本未能检测到 → 需要增强脚本

#### Step 3: 约束更新

更新 `.claude/rules/harness.md` 和 `.claude/rules/harness_check.py`：
- 模糊的规则用具体示例重写
- 补充缺失的规则
- 在脚本中添加新的检查项

更新时需以注释形式留下 **为什么需要这个变更**。

#### Step 4: 完成报告

- 变更内容（以 diff 格式简要展示）
- 新增规则的意图
- 提示「通过反复执行 `/harness-update` 可以持续改进约束」

---

## 脚本: `scripts/generate_harness_check.py`

此脚本放在技能目录内，不依赖具体项目。
在 `/harness-init` 的 Step 3 中，将此脚本作为 **参考模板读取**，
填入项目特定内容后生成 `.claude/rules/harness_check.py`。

生成脚本的规格：

```python
# .claude/rules/harness_check.py
# 本文件由 harness-init 自动生成，可通过 harness-update 更新。

import subprocess, sys, json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent  # 从 .claude/rules/ 向上3层

CHECKS = {
    "typecheck": "<类型检查命令>",
    "lint": "<lint命令>",
    "test": "<测试命令>",  # 指定文件时将其作为参数
}

def run_check(name, cmd, files=None):
    ...

def main():
    files = sys.argv[1:] if len(sys.argv) > 1 else []
    results = {}
    for name, cmd in CHECKS.items():
        results[name] = run_check(name, cmd, files)
    passed = all(r["passed"] for r in results.values())
    print(json.dumps({"passed": passed, "results": results}, indent=2, ensure_ascii=False))
    sys.exit(0 if passed else 1)
```

---

## 设计原则

**核心概念对应关系：**

| 概念 | 本技能中的对应 |
|---|---|
| 合法性验证 | `harness_check.py` 的各项检查 |
| 代码生成 | Claude Code 的代码生成 |
| 精炼循环 | `/harness-update` 的迭代调用 |
| 环境反馈 | 错误消息和测试结果 |

**重要设计决策：**
- `harness_check.py` 放在项目的 `.claude/rules/` 中而非技能的 `scripts/` 中
  — 因为每个项目的内容不同
- 技能的 `scripts/generate_harness_check.py` 仅作为模板生成参考
  — 不依赖项目的通用逻辑集中在此
- 规则文件放在 `.claude/rules/` 中以便 Claude Code 每次引用
  — 通过 `CLAUDE.md` 的引用自动进入上下文
