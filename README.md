<div align="center">

# Harness 技能

**代码验证约束自动生成工具**

</div>

---

> 自动为 **Claude Code** 生成项目专属代码验证约束

## 概述

**Harness** 是一个 Claude Code 技能，自动分析你的项目，生成**自然语言规则**和**可执行验证脚本**，定义什么是有效的代码变更，持续提升 Claude Code 的输出精度。

## 特性

| 特性 | 说明 |
|------|------|
| 自动项目分析 | 自动检测语言、框架、lint、类型检查、测试命令 |
| 规则生成 | 在 `.claude/rules/harness.md` 中生成命名规范、禁止模式、验证条件 |
| 验证脚本 | `harness_check.py` 一键执行类型检查、lint、测试，JSON 格式输出 |
| 持续改进 | 基于错误和用户反馈自主更新约束 |

## 安装

**前提条件**

- [Claude Code](https://claude.ai/code) 已安装
- Python 3.10 或更高版本

**安装方式**

将 `harness-skill` 文件夹放入 `.claude/skills/` 目录下即可。

## 使用方法

### 首次初始化

在 Claude Code 对话中输入：

```
/harness-init
```

Harness 将分析项目并自动生成以下文件：

```
your-project/
├── .claude/
│   └── rules/
│       ├── harness.md          # 自然语言规则
│       └── harness_check.py    # 验证脚本
└── CLAUDE.md                   # 自动追加 harness.md 引用
```

### 更新约束

```
/harness-update
```

在以下时机执行（Claude Code 也会自主执行）：

- 出现类型错误、测试失败、lint 错误时
- 用户反馈"不对"、"我想要这样"时
- 代码生成任务完成后

### 运行验证脚本

```bash
# 验证指定文件
python .claude/rules/harness_check.py src/main.py src/utils.py

# 查看用法
python .claude/rules/harness_check.py --help
```

输出示例：

```json
{
  "passed": true,
  "results": {
    "typecheck": { "passed": true, "errors": [] },
    "lint":      { "passed": true, "errors": [] },
    "test":      { "passed": true, "errors": [] }
  }
}
```

## 许可证

MIT License
