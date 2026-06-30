---
name: harness-init
description: |
  Harness 首次初始化命令。
  解析项目并自动生成 .claude/rules/harness.md（自然语言规则）和
  .claude/rules/harness_check.py（验证脚本），并配置
  PostToolUse 钩子实现验证自动执行（强制层）。
  用户输入 /harness-init 时触发。
---

# `/harness-init` — Harness 首次初始化

解析项目并生成约束。

约束由两层构成：
- **描述层**: `.claude/rules/harness.md`（自然语言规则）通过 CLAUDE.md 的 `@import` 加载。Claude 参照但不保证遵守（建议性质）。
- **强制层**: `.claude/rules/harness_check.py` 通过 PostToolUse 钩子在每次编辑后执行，将验证结果返回给 Agent。确定性执行（强制性质）。

## 步骤

### Step 1: 项目分析（并行执行）

检查以下内容：

```
- 语言/框架: package.json / pyproject.toml / Cargo.toml / go.mod 等
- 测试命令: scripts、Makefile、README
- Lint 工具: .eslintrc、.flake8、ruff.toml、biome.json 等
- 类型检查: tsconfig.json、mypy.ini、pyrightconfig.json 等
- 构建命令: CI 配置（.github/workflows/、.gitlab-ci.yml）
- 命名规范/文件结构: 采样数个已有代码文件的模式
- CLAUDE.md: 如有已有规则则读取
- 已有钩子: 读取 .claude/settings.json 的 hooks 配置（避免覆盖）
```

### Step 2: 约束规则生成

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

### Step 3: 验证脚本生成

生成 `.claude/rules/harness_check.py`。此脚本需支持 **两种执行模式**。

**(A) 独立/CI 模式**（手动执行/CI 集成用）
- 通过 `python .claude/rules/harness_check.py [目标文件路径...]` 执行
- 内部调用项目的类型检查、lint、测试
- 以 JSON 格式输出结果到 stdout（`{"passed": true/false, "errors": [...], "warnings": [...]}`）
- 验证失败时以非0退出码退出（CI 可用作门禁）

**(B) PostToolUse 钩子模式**（Claude Code 自动执行用）
- 无参数启动时，从 stdin 读取 Claude Code 的钩子输入 JSON
  （包含 `tool_name` / `tool_input.file_path` / `tool_input.new_string` 等）
- `tool_name` 不是 `Edit` / `Write` / `MultiEdit` 时，直接以退出码0退出
- 对编辑目标文件执行与 (A) 相同的验证
- **验证结果需符合钩子输出约定**：
  - 退出码0 + stdout 输出 JSON
  - 有问题时通过 `additionalContext` 返回验证结果，使 Agent 能在同一轮次修正：
    ```json
    {"hookSpecificOutput": {"hookEventName": "PostToolUse",
     "additionalContext": "harness_check: <文件> 发现类型错误2项、lint错误1项。详情: ..."}}
    ```
  - 严重违规需强制阻止时可返回 `{"decision": "block", "reason": "<原因>"}`
  - 无问题时 stdout 不输出内容（或输出空 JSON），以退出码0退出
- 注意：stdout 只能输出 JSON。不要将调试输出混入 stdout
  （否则会破坏 JSON 解析。如需日志请输出到 stderr）

> 模式判定通过「是否有参数」或「stdin 是否为 tty」来判断。
> 验证逻辑本体共用，仅输出格式按模式切换。

脚本本体注释和 docstring 用中文编写，函数附带类型注解。

### Step 4: CLAUDE.md 引用追加（描述层）

在 `CLAUDE.md` 末尾追加以下内容（保留已有内容）：

```markdown
## Harness

@.claude/rules/harness.md

本项目的代码验证规则见 `.claude/rules/harness.md`（描述层）。
代码变更通过 PostToolUse 钩子由 `harness_check.py` 自动验证（强制层）。
手动验证可通过 `python .claude/rules/harness_check.py <文件>` 执行。
```

> `@.claude/rules/harness.md` 语法是 Claude Code 的官方功能（CLAUDE.md 的递归导入，最多5层）。
> 规则集中在此，CLAUDE.md 主体保持精简（节省 Token 消耗）。

### Step 4.5: PostToolUse 钩子配置（强制层）

在 `.claude/settings.json` 中注册 PostToolUse 钩子。**这是约束强制层的核心**。
用途为「每次编辑后必定执行验证」，因此放在项目全局的 `.claude/settings.json` 中
而非技能单独的钩子配置中。

如已有 `hooks` 配置则 **追加而非覆盖**。注册前需向用户确认
（钩子以用户权限执行脚本）。

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/rules/harness_check.py"
          }
        ]
      }
    ]
  }
}
```

> 配置后，代码生成/编辑后会立即触发验证，结果以 `additionalContext` 形式
> 返回到 Agent 的上下文中。这实现了「执行 → 环境反馈 → 修正」
> 循环（通过验证函数排除非法操作）在 Claude Code 上的复现。
> 若不使用钩子而仅依赖 CLAUDE.md 的描述，验证只是建议性质，执行无法保证。

### Step 5: 完成报告

向用户报告：
- 生成/变更的文件列表（`harness.md` / `harness_check.py` / `CLAUDE.md` / `.claude/settings.json`）
- 检测到的主要约束（类型检查工具名、测试命令等）
- 已注册 PostToolUse 钩子（每次编辑自动验证），如需禁用可从 `.claude/settings.json` 中移除对应条目
- 通过 `python .claude/rules/harness_check.py --help` 可查看用法
