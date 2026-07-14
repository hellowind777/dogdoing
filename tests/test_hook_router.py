"""Claude Code 与 Codex Hook 事件路由测试。"""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "plugins" / "dogdoing"
SCRIPTS_DIR = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import hook_router  # noqa: E402


# 功能：验证双平台 Hook 载荷会进入正确的业务处理路径
class HookRouterTests(unittest.TestCase):
    # 功能：验证 Codex 的显式失败结果进入错误追踪路径
    def test_codex_failed_post_tool_use_routes_to_failure(self):
        payload = {
            "tool_name": "exec_command",
            "tool_response": {"success": False, "error": "denied"},
        }
        with mock.patch.object(hook_router.tracker, "record_tool_failure") as failure, mock.patch.object(
            hook_router.tracker,
            "record_tool_success",
        ) as success:
            hook_router.handle_event("post_tool_use", payload, "codex")
        failure.assert_called_once_with(payload)
        success.assert_not_called()

    # 功能：验证非零退出码会被 Codex 路由识别为工具失败
    def test_codex_nonzero_exit_code_routes_to_failure(self):
        payload = {
            "tool_name": "exec_command",
            "tool_result": {"exit_code": 1, "output": "failed"},
        }
        with mock.patch.object(hook_router.tracker, "record_tool_failure") as failure:
            hook_router.handle_event("post_tool_use", payload, "codex")
        failure.assert_called_once_with(payload)

    # 功能：验证成功结果只增加成功追踪状态
    def test_successful_post_tool_use_routes_to_success(self):
        payload = {
            "tool_name": "exec_command",
            "tool_response": {"success": True, "exit_code": 0},
        }
        with mock.patch.object(hook_router.tracker, "record_tool_success") as success, mock.patch.object(
            hook_router.tracker,
            "record_tool_failure",
        ) as failure:
            hook_router.handle_event("post_tool_use", payload, "codex")
        success.assert_called_once_with(payload)
        failure.assert_not_called()

    # 功能：验证 Claude 的独立失败事件无条件进入失败追踪
    def test_claude_failure_event_routes_to_failure(self):
        payload = {"tool_name": "Bash", "error": "tool failed"}
        with mock.patch.object(hook_router.tracker, "record_tool_failure") as failure:
            hook_router.handle_event("post_tool_failure", payload, "claude")
        failure.assert_called_once_with(payload)

    # 功能：验证会话开始事件返回对应平台的完整注入文本
    def test_session_start_returns_platform_injection(self):
        with mock.patch.object(
            hook_router.notify,
            "build_injection",
            return_value="codex injection",
        ) as build:
            result = hook_router.handle_event("session_start", {}, "codex")
        self.assertEqual("codex injection", result)
        build.assert_called_once_with("codex")

    # 功能：验证用户提示事件把载荷和平台传给提示处理器
    def test_prompt_submit_returns_reminder(self):
        payload = {"prompt": "hello"}
        with mock.patch.object(
            hook_router.notify,
            "handle_prompt",
            return_value="remember",
        ) as remind:
            result = hook_router.handle_event("prompt_submit", payload, "codex")
        self.assertEqual("remember", result)
        remind.assert_called_once_with(payload, "codex")

    # 功能：验证停止事件调用通知路由且不产生模型上下文文本
    def test_stop_event_routes_notification(self):
        payload = {"stop_reason": "end_turn"}
        with mock.patch.object(hook_router.notify, "route_stop") as route:
            result = hook_router.handle_event("stop", payload, "codex")
        self.assertEqual("", result)
        route.assert_called_once_with(payload)

    # 功能：验证未知事件返回非零状态并写入可诊断错误
    def test_unknown_event_returns_nonzero(self):
        error = io.StringIO()
        with redirect_stderr(error):
            exit_code = hook_router.main(["unknown"], stdin=io.StringIO("{}"))
        self.assertEqual(2, exit_code)
        self.assertIn("未知 Hook 事件", error.getvalue())

    # 功能：验证 Codex 会收到符合 Hook 协议的结构化附加上下文
    def test_main_prints_codex_hook_context_as_json(self):
        output = io.StringIO()
        with mock.patch.object(hook_router, "handle_event", return_value="context"), redirect_stdout(output):
            exit_code = hook_router.main(
                ["session_start", "codex"],
                stdin=io.StringIO("{}"),
            )
        self.assertEqual(0, exit_code)
        self.assertEqual(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": "context",
                }
            },
            json.loads(output.getvalue()),
        )

    # 功能：验证 Claude Code 继续接收原有的纯文本 Hook 上下文
    def test_main_prints_claude_hook_context_as_text(self):
        output = io.StringIO()
        with mock.patch.object(hook_router, "handle_event", return_value="context"), redirect_stdout(output):
            exit_code = hook_router.main(
                ["session_start", "claude"],
                stdin=io.StringIO("{}"),
            )
        self.assertEqual(0, exit_code)
        self.assertEqual("context\n", output.getvalue())

    # 功能：验证 Codex Hook 没有专用根目录变量时仍能通过会话环境识别宿主
    def test_resolve_platform_detects_codex_session_environment(self):
        with mock.patch.dict(os.environ, {"CODEX_THREAD_ID": "thread-1"}, clear=True):
            self.assertEqual("codex", hook_router._resolve_platform(["session_start"]))

    # 功能：验证不存在 Codex 环境标记时共享 Hook 默认按 Claude Code 处理
    def test_resolve_platform_defaults_to_claude(self):
        with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT)}, clear=True):
            self.assertEqual("claude", hook_router._resolve_platform(["session_start"]))

    # 功能：验证通用插件根目录变量不会把 Claude Code 误判为 Codex
    def test_resolve_platform_ignores_generic_plugin_root(self):
        environment = {
            "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT),
            "PLUGIN_ROOT": str(PLUGIN_ROOT),
        }
        with mock.patch.dict(os.environ, environment, clear=True):
            self.assertEqual("claude", hook_router._resolve_platform(["session_start"]))

    # 功能：验证路由脚本在独立 Python 进程中导入所有模块后仍可写标准输出
    def test_router_runs_as_standalone_process(self):
        with tempfile.TemporaryDirectory() as state_dir:
            environment = {
                **os.environ,
                "CODEX_PLUGIN_ROOT": str(PLUGIN_ROOT),
                "DOGDOING_STATE_DIR": state_dir,
            }
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "hook_router.py"),
                    "session_start",
                    "codex",
                ],
                input="{}",
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                env=environment,
                timeout=10,
                check=False,
            )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("collaboration.spawn_agent", completed.stdout)

    # 功能：验证全部 Windows Hook 通过统一入口启动，避免依赖裸 Python 命令
    def test_windows_hook_configs_use_shared_runner(self):
        config_paths = (
            PLUGIN_ROOT / "hooks.json",
            PLUGIN_ROOT / "hooks" / "hooks.json",
            PLUGIN_ROOT / "hooks" / "claude-failure.json",
        )
        for path in config_paths:
            hooks = json.loads(path.read_text(encoding="utf-8"))["hooks"]
            for event_name, groups in hooks.items():
                with self.subTest(path=path, event_name=event_name):
                    command = groups[0]["hooks"][0]["command_windows"]
                    self.assertIn("scripts/hook_router_windows.cmd", command.replace("\\", "/"))
                    self.assertNotRegex(command, r"^\s*(?:python|python3)(?:\.exe)?\s")

    # 功能：验证 Windows 入口使用显式 Python 执行真实 Hook 路由
    def test_windows_hook_runner_uses_explicit_python(self):
        if os.name != "nt":
            self.skipTest("仅在 Windows 验证批处理入口")
        runner = SCRIPTS_DIR / "hook_router_windows.cmd"
        comspec = os.environ.get("ComSpec", r"C:\Windows\System32\cmd.exe")
        command = subprocess.list2cmdline([str(runner), "session_start", "codex"])
        with tempfile.TemporaryDirectory() as state_dir:
            environment = {
                **os.environ,
                "DOGDOING_PYTHON": sys.executable,
                "DOGDOING_STATE_DIR": state_dir,
            }
            completed = subprocess.run(
                [comspec, "/d", "/c", command],
                input="{}",
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                env=environment,
                timeout=10,
                check=False,
            )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("collaboration.spawn_agent", completed.stdout)

    # 功能：验证显式 Python 路径无效时返回可定位错误
    def test_windows_hook_runner_rejects_missing_explicit_python(self):
        if os.name != "nt":
            self.skipTest("仅在 Windows 验证批处理入口")
        runner = SCRIPTS_DIR / "hook_router_windows.cmd"
        comspec = os.environ.get("ComSpec", r"C:\Windows\System32\cmd.exe")
        command = subprocess.list2cmdline([str(runner), "session_start", "codex"])
        environment = {**os.environ, "DOGDOING_PYTHON": str(SCRIPTS_DIR / "missing-python.exe")}
        completed = subprocess.run(
            [comspec, "/d", "/c", command],
            input="{}",
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=environment,
            timeout=10,
            check=False,
        )
        self.assertNotEqual(0, completed.returncode)
        self.assertIn("[刀盾狗]", completed.stderr)
        self.assertIn("DOGDOING_PYTHON", completed.stderr)

    # 功能：验证 Codex 实际发现的共享 Hook 配置包含跨平台公共事件和 Windows 命令
    def test_codex_hook_config_uses_router(self):
        path = PLUGIN_ROOT / "hooks" / "hooks.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        hooks = data["hooks"]
        common_events = {"SessionStart", "UserPromptSubmit", "PostToolUse", "Stop"}
        self.assertEqual(common_events, set(hooks))
        for event_name in common_events:
            groups = hooks[event_name]
            with self.subTest(event_name=event_name):
                self.assertNotIn("matcher", groups[0])
                command = groups[0]["hooks"][0]["command"]
                self.assertIn("scripts/hook_router.py", command.replace("\\", "/"))
                windows_command = groups[0]["hooks"][0]["command_windows"]
                self.assertIn("scripts/hook_router_windows.cmd", windows_command.replace("\\", "/"))
                self.assertNotIn(" claude", command)
                self.assertNotIn(" codex", command)
                self.assertNotIn(" claude", windows_command)
                self.assertNotIn(" codex", windows_command)

    # 功能：验证旧版 Codex 兼容清单同样不会用空 matcher 禁用事件
    def test_legacy_codex_hook_config_has_no_empty_matchers(self):
        path = PLUGIN_ROOT / "hooks.json"
        hooks = json.loads(path.read_text(encoding="utf-8"))["hooks"]
        for event_name, groups in hooks.items():
            with self.subTest(event_name=event_name):
                self.assertNotEqual("", groups[0].get("matcher"))

    # 功能：验证 Claude 清单把独立失败事件追加到共享 Hook 配置
    def test_claude_hook_config_uses_router(self):
        manifest_path = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        path = PLUGIN_ROOT / manifest["hooks"]
        hooks = json.loads(path.read_text(encoding="utf-8"))["hooks"]
        self.assertEqual({"PostToolUseFailure"}, set(hooks))
        for event_name, groups in hooks.items():
            with self.subTest(event_name=event_name):
                command = groups[0]["hooks"][0]["command"]
                self.assertIn("hook_router.py", command)


if __name__ == "__main__":
    unittest.main()
