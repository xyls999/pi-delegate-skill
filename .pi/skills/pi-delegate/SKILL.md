---
name: pi-delegate
description: Delegate a task to the local Pi Coding Agent using pi -p and return Pi's result to the parent agent. Use when an independent Pi agent can analyze, review, debug, research code, or provide a second opinion on a task.
---

# pi-delegate

Use this skill to run the locally installed Pi Coding Agent as a non-interactive worker. **Actually invoke `pi -p`; never simulate what Pi might answer.** Capture and return the worker's complete result to the parent agent, which should treat it as an independent opinion rather than unquestionable truth.

## When to use

Delegate an independent analysis, second opinion, coding subtask, code or architecture review, bug hunt, log/code/config analysis, debugging hypothesis, or an explicitly scoped implementation task. Construct a complete, self-contained prompt: Pi does not have the parent's conversation context unless it is included in the prompt.

Prefer `analyze` for investigation and `review` for review work. Use `execute` only when the parent explicitly permits file changes. Pi runs in the caller's current project directory by default, so it can read project files and instructions.

## Invocation

From this skill directory:

```bash
python scripts/pi_delegate.py --prompt "Analyze the current project. Do not modify files. Return evidence and recommended fixes."
```

A prompt can also come from stdin:

```bash
echo "Review the current project; do not modify files." | python scripts/pi_delegate.py
```

Useful options:

```text
--cwd PATH       Run Pi in PATH instead of the caller's current directory
--mode MODE      analyze, review, or execute (adds explicit instructions)
--model MODEL    Pass the supported Pi --model option
--thinking LEVEL Pass the supported Pi --thinking option
--timeout SECS   Kill the worker after this many seconds (default: 600)
--pi-command CMD Override the executable name/path (useful for tests)
```

The wrapper uses only CLI options supported by the installed Pi version (`-p`, `--model`, and `--thinking`). It emits one JSON object on stdout:

```json
{"success":true,"status":"completed","exit_code":0,"stdout":"...","stderr":"","cwd":"..."}
```

For failures, `success` is false and both `stdout` and `stderr` are retained. A missing executable includes: `Pi CLI is not installed or is not available in PATH.` Authentication/configuration failures retain Pi's original stderr and add a diagnostic hint. The parent must read and reason over `stdout`, not merely report that Pi finished.

## Safety and recursion

Pi is a tool-using coding agent. Do not include secrets, API keys, tokens, passwords, or private credentials in prompts; the wrapper redacts common credential assignments before invocation. Do not ask Pi for destructive operations (`rm -rf`, `git reset --hard`, `git clean -fd`) unless the parent has explicitly authorized them in the current environment. Keep analysis/review prompts read-only.

The wrapper sets `PI_DELEGATE_ACTIVE=1` for the child. If that variable is already `1`, it returns `Nested pi-delegate invocation prevented.` without spawning another Pi process. This prevents recursive delegation loops.

## Prompt patterns

- Analyze: state the issue, relevant files/symptoms, constraints, requested evidence, and say `Do not modify files.`
- Review: state the diff/scope and ask for correctness, bugs, edge cases, architecture, and maintainability findings; say `Do not modify files.`
- Execute: state exact acceptance criteria, files in scope, tests to run, and whether changes are allowed.

The result is advisory. Validate important claims independently and combine them with the parent agent's own judgment.
