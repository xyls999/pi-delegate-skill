---
name: pi-delegate
description: Automatically delegate independent analysis, debugging, code review, architecture review, or explicitly scoped coding tasks to the local Pi Coding Agent. Use when a second opinion or parallel worker can save time; invoke real `pi -p` and integrate its actual result into the current task.
---

# pi-delegate — automatic Pi worker protocol

This skill makes the local Pi Coding Agent an on-demand heterogeneous worker for the current parent agent. When this skill is active, the parent agent should **automatically delegate suitable independent subtasks** instead of asking the user to run a command.

## Required workflow

1. Decide whether the task is independent enough to delegate. Good candidates are investigation, debugging, review, architecture, log/config analysis, second opinions, and clearly bounded implementation subtasks.
2. Build a self-contained prompt in English or the user's language. Include goal, symptoms, relevant paths, constraints, expected output, and whether changes are allowed. Do not rely on hidden parent-chat context.
3. Actually run the local Pi in non-interactive print mode. The canonical command is:

   ```bash
   pi --no-session -p "<self-contained prompt>"
   ```

   Do not simulate Pi's answer and do not start the interactive TUI.
4. For analysis/review, prefer the read-only command:

   ```bash
   pi --no-session --tools read,grep,find,ls -p "<prompt>\nDo not modify files."
   ```

   For an explicitly authorized coding task, omit the read-only allowlist and state exact acceptance criteria.
5. Capture stdout, stderr, exit code, and execution status. The parent agent must read the complete stdout and use it as evidence.
6. Integrate Pi's result with the parent's own reasoning, validate important claims, and continue the task. Pi's opinion is advisory; do not blindly apply it.

The bundled `scripts/pi_delegate.py` is a cross-platform execution adapter. It runs the same `pi -p` flow, returns one JSON object, handles stdin/cwd/timeout/errors, and is an implementation detail. The parent agent may call it when structured capture is more convenient; the user should not need to manually invoke Python.

## Delegation policy

- **analyze**: read-only investigation; append `Analyze only. Do not modify files.`
- **review**: read-only correctness, bugs, edge cases, architecture, and maintainability review.
- **execute**: only when the parent explicitly allows changes; provide scope, tests, and acceptance criteria.
- Use `--no-session` by default so each worker gets a clean context and does not accumulate irrelevant history.
- Use a cheaper model and low thinking for reconnaissance; use a stronger model only for difficult reasoning or implementation.
- Do not pass secrets, API keys, tokens, passwords, or private credentials. The adapter performs basic redaction of inline credential assignments, but callers remain responsible for safe prompts.
- Do not delegate destructive commands unless explicitly authorized in the current environment.

## Result and failures

When using the adapter, its stdout is one JSON object:

```json
{"success":true,"status":"completed","exit_code":0,"stdout":"<Pi answer>","stderr":"","cwd":"<absolute cwd>"}
```

On failure, preserve all available fields. A missing executable must clearly say `Pi CLI is not installed or is not available in PATH.` Authentication/configuration failures must preserve Pi's original stderr. Report a non-zero exit code as a failed worker, not as a successful empty answer.

## Recursion protection

The adapter sets `PI_DELEGATE_ACTIVE=1` for the child. If that flag is already set, it returns `Nested pi-delegate invocation prevented.` and does not spawn another Pi. Never create an unbounded Pi → pi-delegate → Pi loop.

## Efficiency guidance

Use one-shot `pi -p --no-session` for independent tasks: it is isolated, observable, and usually cheaper in context than sharing a long session. Keep prompts focused and request concise structured output. A future persistent `pi --mode rpc` worker can reduce process startup overhead for many sequential subtasks, but is intentionally not the default because lifecycle and context isolation are more complex.
