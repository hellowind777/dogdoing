#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将 Claude Code 与 Codex Hook 事件路由到共享 Dogdoing 逻辑。"""

import json
import os
import sys
from typing import List, Optional, TextIO

import notify
import runtime as shared_runtime
import tracker


_FAILURE_STATUSES = {"error", "errored", "fail", "failed", "failure", "denied", "cancelled"}
_CODEX_ENVIRONMENT_MARKERS = (
    "CODEX_PLUGIN_ROOT",
    "CODEX_THREAD_ID",
    "CODEX_INTERNAL_ORIGINATOR_OVERRIDE",
    "CODEX_CI",
    "CODEX_SHELL",
)
_CODEX_CONTEXT_EVENTS = {
    "session_start": "SessionStart",
    "prompt_submit": "UserPromptSubmit",
}


# 功能：递归判断工具结果对象是否明确表示执行失败
def is_tool_failure(payload: dict) -> bool:
    for key in ("success", "ok"):
        if key in payload and payload[key] is False:
            return True
    for key in ("is_error", "isError", "failed"):
        if payload.get(key) is True:
            return True
    status = payload.get("status") or payload.get("outcome")
    if isinstance(status, str) and status.lower() in _FAILURE_STATUSES:
        return True
    if payload.get("error") not in (None, "", False, {}):
        return True
    for key in ("exit_code", "exitCode", "returncode", "return_code"):
        value = payload.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value != 0:
            return True
    for key in ("tool_response", "tool_result", "response", "result", "output"):
        nested = payload.get(key)
        if isinstance(nested, dict) and is_tool_failure(nested):
            return True
    return False


# 功能：把一个归一化 Hook 事件交给注入、通知或追踪模块处理
def handle_event(event_name: str, payload: dict, platform: str) -> str:
    event = event_name.strip().lower().replace("-", "_")
    host = platform.strip().lower()
    if event == "session_start":
        return notify.build_injection(host)
    if event == "prompt_submit":
        return notify.handle_prompt(payload, host)
    if event == "post_tool_use":
        if is_tool_failure(payload):
            tracker.record_tool_failure(payload)
        else:
            tracker.record_tool_success(payload)
        return ""
    if event == "post_tool_failure":
        tracker.record_tool_failure(payload)
        return ""
    if event == "stop":
        notify.route_stop(payload)
        return ""
    raise ValueError(f"未知 Hook 事件：{event_name}")


# 功能：根据显式参数或宿主环境变量确定当前 Hook 平台
def _resolve_platform(arguments: List[str]) -> str:
    if len(arguments) > 1 and arguments[1].lower() in ("codex", "claude"):
        return arguments[1].lower()
    if any(os.environ.get(name) for name in _CODEX_ENVIRONMENT_MARKERS):
        return "codex"
    return "claude"


# 功能：执行 Hook CLI，输出模型上下文并用退出码报告配置错误
def main(arguments: Optional[List[str]] = None, stdin: Optional[TextIO] = None) -> int:
    args = list(sys.argv[1:] if arguments is None else arguments)
    if not args:
        print("缺少 Hook 事件", file=sys.stderr)
        return 2
    payload = shared_runtime.read_hook_payload(stdin)
    platform = _resolve_platform(args)
    try:
        output = handle_event(args[0], payload, platform)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    if output:
        if platform == "codex":
            event_name = _CODEX_CONTEXT_EVENTS[args[0].strip().lower().replace("-", "_")]
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": event_name,
                            "additionalContext": output,
                        }
                    },
                    ensure_ascii=False,
                )
            )
        else:
            print(output)
    return 0


if __name__ == "__main__":
    shared_runtime.configure_utf8_streams()
    raise SystemExit(main())
