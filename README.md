# pi-delegate-skill

将本机已安装的 [Pi Coding Agent](https://github.com/badlogic/pi-mono) 作为独立、非交互式 worker 委派给其他 AI Agent。

## 目录

```text
.pi/skills/pi-delegate/
├── SKILL.md
└── scripts/
    └── pi_delegate.py
```

## 安装

将 `.pi/skills/pi-delegate` 复制到目标项目，或复制到 Pi/Agent Skills 能发现的 skills 目录。调用环境需要：

- Pi CLI 已安装并可在 `PATH` 中找到（`pi --version`）
- Python 3.9+
- Pi provider 已完成认证/配置

## 手工调用

```bash
python .pi/skills/pi-delegate/scripts/pi_delegate.py \
  --prompt "Analyze the current project. Do not modify files. Return evidence and recommended fixes."
```

默认 cwd 是命令执行时的当前目录。指定项目目录：

```bash
python .pi/skills/pi-delegate/scripts/pi_delegate.py \
  --cwd /path/to/project \
  --prompt "Inspect this project and describe its architecture. Do not modify files."
```

也支持 stdin（`--prompt` 优先于 stdin）：

```bash
echo "Review the current code. Do not modify files." | \
  python .pi/skills/pi-delegate/scripts/pi_delegate.py
```

### 模式与可选参数

```bash
# 默认建议：只分析
python .pi/skills/pi-delegate/scripts/pi_delegate.py --mode analyze --prompt "..."

# 代码审查（自动追加只读审查要求）
python .pi/skills/pi-delegate/scripts/pi_delegate.py --mode review --prompt "Review the authentication module."

# 明确允许修改文件
python .pi/skills/pi-delegate/scripts/pi_delegate.py --mode execute --prompt "Implement the requested fix and run tests."

# 仅传递当前 Pi 版本 help 中确认存在的参数
python .pi/skills/pi-delegate/scripts/pi_delegate.py \
  --model provider/model --thinking high --timeout 120 --prompt "..."
```

`--timeout` 单位为秒，默认 600。第一版刻意不做并发；未来可由上层 Agent 启动多个相互独立的进程。

## 返回格式

stdout 始终输出一个 JSON 对象，便于 Agent 解析：

```json
{
  "success": true,
  "status": "completed",
  "exit_code": 0,
  "stdout": "Pi's complete answer",
  "stderr": "",
  "cwd": "/absolute/project/path"
}
```

失败时 `success` 为 `false`，同时保留 stdout、stderr 和 exit code（超时/启动失败可能没有 exit code）。command not found 会返回：`Pi CLI is not installed or is not available in PATH.`；认证失败会保留原始 stderr 并附加配置提示。父 Agent 必须读取 `stdout` 并结合自身判断，而不是只报告“Pi 已完成”。

## 给其他 AI Agent 的调用规则

1. 构造自包含 prompt：背景、症状、范围、约束、期望输出都写清楚。
2. 不要假设 Pi 知道父 Agent 的聊天上下文。
3. 分析/审查任务明确写 `Do not modify files.`，执行任务明确验收标准和允许改动范围。
4. 真正运行 wrapper，并把 JSON 中的 `stdout`、`stderr`、`success`、`exit_code` 带回上下文；禁止手工模拟 Pi 的回答。
5. 将 Pi 视为可能调用工具的独立 Agent，不要默认其意见正确。
6. 避免在 prompt 中放入 API key、token、密码等秘密；wrapper 会对常见的内联凭证赋值做基本脱敏，但这不是秘密管理方案。

示例：

```bash
python .pi/skills/pi-delegate/scripts/pi_delegate.py --mode analyze --prompt \
'Analyze why the training reward collapses after 2000 iterations. Focus on observation dimensions, reward, termination, PPO configuration, action clipping, and NaN sources. Return likely causes, evidence, files, and fixes. Do not modify files.'
```

## 递归保护

wrapper 在 Pi 子进程环境中设置 `PI_DELEGATE_ACTIVE=1`。若当前调用已经继承该值，wrapper 返回 `recursion_prevented` 和 `Nested pi-delegate invocation prevented.`，不会启动新的 Pi，避免 Pi → pi-delegate → Pi 无限递归。

## 验证记录

在实现前确认了本机 Pi CLI：

```text
pi --version  → 0.85.1
```

`pi --help` 显示并因此采用了 `-p/--print`、`--model`、`--thinking`、`--no-session`；没有假设不存在的 CLI 参数。真实调用：

```text
pi -p "Reply with exactly: PI_DELEGATE_OK" --no-session
→ PI_DELEGATE_OK
```

此外已检查脚本的 command-not-found、stdin 和递归保护设计。当前执行环境的 `python`/`python3` 仅映射到 Microsoft Store alias，未提供可执行 Python 解释器，因此无法在此 shell 中完成 `py_compile` 和 wrapper 端到端测试；在具备 Python 3 的机器上请按下列命令补跑：

```bash
python -m py_compile .pi/skills/pi-delegate/scripts/pi_delegate.py
python .pi/skills/pi-delegate/scripts/pi_delegate.py --prompt "Reply with exactly: PI_DELEGATE_OK"
python .pi/skills/pi-delegate/scripts/pi_delegate.py --cwd . --prompt "Describe this project in one sentence. Do not modify files."
python .pi/skills/pi-delegate/scripts/pi_delegate.py --pi-command definitely-not-real --prompt test
PI_DELEGATE_ACTIVE=1 python .pi/skills/pi-delegate/scripts/pi_delegate.py --prompt test
```
