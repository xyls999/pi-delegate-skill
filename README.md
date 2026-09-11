# pi-delegate-skill

`pi-delegate` 让宿主 AI Agent 自动把适合拆分的工作交给本机 Pi Coding Agent，再把 Pi 的真实结果整合回当前任务。它不是让用户手工操作 Python，而是一份给 Agent 的自动委派协议；Python adapter 只负责跨平台捕获结果。

## 工作方式

```text
用户任务
  ↓
主 Agent 加载 pi-delegate
  ↓ 自动判断并构造自包含 prompt
pi --no-session -p "..."
  ↓
主 Agent 读取 stdout/stderr/exit code
  ↓
结合自身判断、验证并继续工作
```

Pi 是异构 worker：主 Agent 可以使用一个模型，Pi 使用另一个更便宜或更擅长编码的模型。

## 安装

将仓库中的 `.pi/skills/pi-delegate/` 放入目标项目的 `.pi/skills/`，或放入用户级 Skill 目录：

```text
~/.pi/agent/skills/pi-delegate/
```

在 Pi 中也可以直接安装本仓库：

```bash
pi install https://github.com/xyls999/pi-delegate-skill
```

目标环境需要 Pi 已在 PATH 中并已配置 provider：

```bash
pi --version
```

## 对用户的使用方式

安装后，不需要输入 Python 命令。向主 Agent 提出正常任务即可；当任务适合独立分析、Debug、Review、架构判断或明确的子任务时，主 Agent 应自动加载 `pi-delegate` 并调用 Pi。

主 Agent 的实际默认调用是：

```bash
pi --no-session -p "完整、自包含的任务描述"
```

分析/审查任务使用只读工具：

```bash
pi --no-session --tools read,grep,find,ls -p "分析任务。Do not modify files."
```

执行任务只有在明确授权修改文件时才开放默认工具。

## 适合委派的任务

- 独立分析 bug 和日志
- Code Review / Architecture Review
- 检查配置、依赖和潜在风险
- 对复杂方案提供第二意见
- 阅读当前项目并提出修改方案
- 完整且边界明确的 coding 子任务

## Agent 委派规范

主 Agent 必须：

1. 判断任务是否适合独立委派。
2. 生成包含背景、症状、文件范围、约束和输出格式的自包含 prompt。
3. 真正运行 `pi -p`，禁止模拟“Pi 可能会说什么”。
4. 读取完整 stdout、stderr、exit code 和执行状态。
5. 将 Pi 输出作为建议和证据，与自身判断结合。
6. 对重要结论自行验证。
7. 分析/Review 默认要求 `Do not modify files.`。

不要把主 Agent 全部聊天历史复制给 Pi，只传递完成子任务所需的信息，这比共享长会话更省 Token。默认 `--no-session` 保证每次 worker 上下文隔离。

## Python adapter（可选）

需要结构化捕获时使用：

```bash
python .pi/skills/pi-delegate/scripts/pi_delegate.py \
  --mode analyze \
  --prompt "Inspect the current project and identify likely bugs."
```

支持：

```text
--prompt TEXT       Prompt；优先于 stdin
--cwd PATH          Pi 工作目录，默认当前目录
--mode analyze|review|execute
--model MODEL       原样传给 Pi --model
--thinking LEVEL    原样传给 Pi --thinking
--timeout SECONDS   默认 600
```

stdin：

```bash
echo "Review the current code. Do not modify files." | \
  python .pi/skills/pi-delegate/scripts/pi_delegate.py
```

adapter 返回一个 JSON 对象：

```json
{"success":true,"status":"completed","exit_code":0,"stdout":"Pi answer","stderr":"","cwd":"/project"}
```

失败时保留 Pi 原始 stdout/stderr 和 exit code。找不到 Pi 时返回明确的 `Pi CLI is not installed or is not available in PATH.`。认证失败会保留原始 stderr 并增加配置提示。检测到 `PI_DELEGATE_ACTIVE=1` 时返回 `Nested pi-delegate invocation prevented.`，阻止递归委派。

## 效率策略

- 一次性独立任务：`pi -p --no-session`，隔离好、稳定、上下文成本低。
- 侦察/Review：`--tools read,grep,find,ls` + 低 thinking + 低成本模型。
- 复杂实现：明确授权后使用更强模型和更高 thinking。
- 多个连续任务：未来可增加持久 `pi --mode rpc` worker，减少进程启动开销；第一版不默认启用，避免会话污染和生命周期复杂度。

## 安全

不要在 prompt 中放 API key、token、密码或其他 secrets。Pi 是可能调用工具的 coding agent；不要让它执行 `rm -rf`、`git reset --hard`、`git clean -fd` 等破坏性操作，除非当前任务明确授权且环境允许。

## 已验证环境

本仓库已确认本机 Pi CLI 版本为 `0.85.1`，并依据 `pi --help` 使用真实存在的 `-p`、`--no-session`、`--tools`、`--model` 和 `--thinking` 参数。已验证：

- Pi 直接 print 调用返回 `PI_DELEGATE_OK`
- adapter 成功 JSON 返回
- 非零 exit code、stdout、stderr 原样保留
- command-not-found
- stdin 优先级
- cwd 传递
- analyze/review 只读工具参数
- 递归保护
- Python 语法检查

当前 provider 若返回上游不可用或认证错误，adapter 会返回 `success: false`，并保留真实错误信息；这表示 Pi 环境问题，不会被 Skill 隐藏。
