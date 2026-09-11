#!/usr/bin/env python3
"""Run the local Pi Coding Agent as a non-interactive worker and emit JSON."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_TIMEOUT = 600.0
SECRET_RE = re.compile(
    r"(?i)(\b(?:api[_-]?key|token|password|passwd|secret|auth(?:entication)?[_-]?token)\b\s*[:=]\s*)([^\s,;]+)"
)


def redact_prompt(prompt: str) -> str:
    """Redact common inline credential assignments without changing other context."""
    return SECRET_RE.sub(r"\1[REDACTED]", prompt)


def result(success: bool, status: str, exit_code: int | None, stdout: str, stderr: str, cwd: str, **extra: str) -> dict:
    value = {
        "success": success,
        "status": status,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "cwd": cwd,
    }
    value.update(extra)
    return value


def emit(value: dict) -> int:
    sys.stdout.write(json.dumps(value, ensure_ascii=False) + "\n")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delegate a self-contained task to local Pi")
    parser.add_argument("mode_positional", nargs="?", choices=("analyze", "review", "execute"), help="optional prompt mode")
    parser.add_argument("prompt_positional", nargs="?", help="prompt, when --prompt is not used")
    parser.add_argument("--prompt", help="complete self-contained task prompt")
    parser.add_argument("--cwd", help="Pi working directory (default: current directory)")
    parser.add_argument("--mode", choices=("analyze", "review", "execute"), default=None)
    parser.add_argument("--model", help="Pi model passed through to --model")
    parser.add_argument("--thinking", choices=("off", "minimal", "low", "medium", "high", "xhigh", "max"))
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--pi-command", default="pi", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cwd = os.path.abspath(args.cwd or os.getcwd())
    mode = args.mode or args.mode_positional

    if os.environ.get("PI_DELEGATE_ACTIVE") == "1":
        return emit(result(False, "recursion_prevented", None, "", "Nested pi-delegate invocation prevented.", cwd))
    if not os.path.isdir(cwd):
        return emit(result(False, "invalid_cwd", None, "", f"Working directory does not exist: {cwd}", cwd))
    if args.timeout <= 0:
        return emit(result(False, "invalid_timeout", None, "", "Timeout must be greater than zero.", cwd))

    prompt = args.prompt
    if prompt is None and args.prompt_positional is not None:
        prompt = args.prompt_positional
    if prompt is None and not sys.stdin.isatty():
        prompt = sys.stdin.read()
    if not prompt or not prompt.strip():
        return emit(result(False, "invalid_prompt", None, "", "A prompt is required via --prompt, argument, or stdin.", cwd))

    prompt = redact_prompt(prompt)
    if mode == "analyze":
        prompt += "\n\nAnalyze only. Do not modify files."
    elif mode == "review":
        prompt += "\n\nReview relevant code for correctness, bugs, edge cases, architecture, and maintainability. Do not modify files."
    elif mode == "execute":
        prompt += "\n\nYou may modify files only as required by this explicitly delegated task."

    executable = shutil.which(args.pi_command) if not os.path.isabs(args.pi_command) else args.pi_command
    if not executable:
        return emit(result(False, "command_not_found", None, "", "Pi CLI is not installed or is not available in PATH. Check `which pi` and `pi --version`.", cwd))

    command = [executable, "--no-session"]
    if mode in ("analyze", "review"):
        command.extend(("--tools", "read,grep,find,ls"))
    command.extend(("-p", prompt))
    if args.model:
        command.extend(("--model", args.model))
    if args.thinking:
        command.extend(("--thinking", args.thinking))
    child_env = os.environ.copy()
    child_env["PI_DELEGATE_ACTIVE"] = "1"
    try:
        completed = subprocess.run(
            command, cwd=cwd, env=child_env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=args.timeout, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes): stdout = stdout.decode("utf-8", "replace")
        if isinstance(stderr, bytes): stderr = stderr.decode("utf-8", "replace")
        return emit(result(False, "timeout", None, stdout, stderr, cwd, error=f"Pi timed out after {args.timeout:g} seconds."))
    except OSError as exc:
        return emit(result(False, "spawn_failed", getattr(exc, "errno", None), "", str(exc), cwd))

    status = "completed" if completed.returncode == 0 else "failed"
    extra = {}
    if completed.returncode != 0 and re.search(r"(?i)(auth|credential|api.?key|unauthori[sz]ed)", completed.stderr):
        extra["hint"] = "Pi invocation failed because the local Pi environment is not authenticated/configured."
    return emit(result(completed.returncode == 0, status, completed.returncode, completed.stdout, completed.stderr, cwd, **extra))


if __name__ == "__main__":
    raise SystemExit(main())
