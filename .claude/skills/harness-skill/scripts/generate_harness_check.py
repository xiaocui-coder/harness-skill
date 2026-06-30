"""
Harness 技能用模板脚本
本文件在 /harness-init 的 Step 3 中作为参考读取，
填入项目特定内容后生成 .claude/rules/harness_check.py。

Claude Code 不会直接执行此文件。
作为生成 harness_check.py 的模板使用。
"""

import subprocess
import sys
import json
from pathlib import Path

# 自动检测项目根目录（从 .claude/rules/ 向上3层）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------
# 项目特定配置（/harness-init 时自动填入）
# ---------------------------------------------------------------
CHECKS = {
    # 示例: "typecheck": "npx tsc --noEmit"
    # 示例: "typecheck": "mypy ."
    "typecheck": None,

    # 示例: "lint": "npx eslint ."
    # 示例: "lint": "ruff check ."
    "lint": None,

    # 示例: "test": "npm test"
    # 示例: "test": "pytest"
    "test": None,

    # 示例: "build": "npm run build"
    "build": None,
}

# 过滤掉未配置的检查项
CHECKS = {k: v for k, v in CHECKS.items() if v is not None}

# ---------------------------------------------------------------
# 执行逻辑（无需修改）
# ---------------------------------------------------------------

def run_check(name: str, cmd: str, files: list[str] | None = None) -> dict:
    """执行命令并返回结果"""
    # 支持文件参数的检查（lint、typecheck）将文件追加到命令后
    full_cmd = cmd
    if files and name in ("lint", "typecheck"):
        full_cmd = f"{cmd} {' '.join(files)}"

    try:
        result = subprocess.run(
            full_cmd,
            shell=True,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        passed = result.returncode == 0
        return {
            "passed": passed,
            "command": full_cmd,
            "stdout": result.stdout.strip()[-2000:] if result.stdout else "",
            "stderr": result.stderr.strip()[-2000:] if result.stderr else "",
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "command": full_cmd,
            "stdout": "",
            "stderr": "超时（60秒）",
            "returncode": -1,
        }
    except Exception as e:
        return {
            "passed": False,
            "command": full_cmd,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
        }


def main():
    files = sys.argv[1:] if len(sys.argv) > 1 else []

    if "--help" in files or "-h" in files:
        print("用法: python .claude/rules/harness_check.py [文件路径...]")
        print("")
        print("  无参数: 检查整个项目")
        print("  指定文件: 对该文件执行 lint/typecheck")
        print("")
        print("已配置的检查项:")
        for name, cmd in CHECKS.items():
            print(f"  {name}: {cmd}")
        sys.exit(0)

    if not CHECKS:
        print(json.dumps({
            "passed": False,
            "error": "未配置检查项。请执行 /harness-init。",
            "results": {}
        }, indent=2, ensure_ascii=False))
        sys.exit(1)

    results = {}
    for name, cmd in CHECKS.items():
        print(f"[harness] 正在执行 {name}...", file=sys.stderr)
        results[name] = run_check(name, str(cmd), files)

    passed = all(r["passed"] for r in results.values())
    failed = [name for name, r in results.items() if not r["passed"]]

    output = {
        "passed": passed,
        "failed_checks": failed,
        "results": results,
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
