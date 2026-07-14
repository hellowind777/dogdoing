"""共享运行时配置、输入和状态文件测试。"""

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "plugins" / "dogdoing" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import runtime  # noqa: E402
import notify  # noqa: E402
import tracker  # noqa: E402


# 功能：验证双平台共享运行时的配置与文件操作
class RuntimeTests(unittest.TestCase):
    # 功能：为每项测试创建互不影响的插件目录
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.codex_root = self.root / "codex"
        self.generic_root = self.root / "generic"
        self.claude_root = self.root / "claude"
        for directory, source in (
            (self.codex_root, "codex"),
            (self.generic_root, "generic"),
            (self.claude_root, "claude"),
        ):
            directory.mkdir()
            (directory / "settings.json").write_text(
                json.dumps({"source": source, "enabled": False}),
                encoding="utf-8",
            )

    # 功能：清理测试期间创建的临时目录
    def tearDown(self):
        self.temporary.cleanup()

    # 功能：验证 Codex 插件根目录环境变量拥有最高优先级
    def test_codex_plugin_root_has_priority(self):
        values = {
            "CODEX_PLUGIN_ROOT": str(self.codex_root),
            "PLUGIN_ROOT": str(self.generic_root),
            "CLAUDE_PLUGIN_ROOT": str(self.claude_root),
        }
        with mock.patch.dict(os.environ, values, clear=False):
            self.assertEqual(self.codex_root.resolve(), runtime.find_plugin_root())
            self.assertEqual("codex", runtime.read_setting("source"))

    # 功能：验证通用插件根目录可供 Codex Hook 运行时使用
    def test_generic_plugin_root_is_supported(self):
        with mock.patch.dict(
            os.environ,
            {"PLUGIN_ROOT": str(self.generic_root)},
            clear=True,
        ):
            self.assertEqual(self.generic_root.resolve(), runtime.find_plugin_root())
            self.assertEqual("generic", runtime.read_setting("source"))

    # 功能：验证布尔值 false 不会被误当成缺失配置
    def test_false_setting_is_preserved(self):
        with mock.patch.dict(
            os.environ,
            {"CODEX_PLUGIN_ROOT": str(self.codex_root)},
            clear=True,
        ):
            self.assertIs(runtime.read_setting("enabled", True), False)

    # 功能：验证现有通知和追踪脚本都能读取 Codex 插件根目录配置
    def test_existing_scripts_use_codex_plugin_root(self):
        with mock.patch.dict(
            os.environ,
            {"CODEX_PLUGIN_ROOT": str(self.codex_root)},
            clear=True,
        ):
            self.assertEqual("codex", notify._read_setting("source", "missing"))
            self.assertEqual("codex", tracker._read_setting("source", "missing"))

    # 功能：验证损坏 JSON 文件会返回默认值的新副本
    def test_invalid_json_uses_defaults(self):
        state_file = self.root / "state.json"
        state_file.write_text("not-json", encoding="utf-8")
        defaults = {"combo": 0, "items": []}
        loaded = runtime.read_json(state_file, defaults)
        loaded["items"].append("changed")
        self.assertEqual({"combo": 0, "items": []}, defaults)

    # 功能：验证状态写入完成后不会遗留临时文件
    def test_atomic_json_write_replaces_target(self):
        state_file = self.root / "state" / "state.json"
        runtime.write_json_atomic(state_file, {"combo": 3})
        self.assertEqual({"combo": 3}, json.loads(state_file.read_text(encoding="utf-8")))
        self.assertEqual([], list(state_file.parent.glob("*.tmp")))

    # 功能：验证 Hook 输入可以从合法 JSON 对象中读取
    def test_read_hook_payload_accepts_object(self):
        stream = io.StringIO('{"tool_name":"exec_command"}')
        self.assertEqual(
            {"tool_name": "exec_command"},
            runtime.read_hook_payload(stream),
        )

    # 功能：验证空输入、非法 JSON 和非对象 JSON 都安全回退
    def test_read_hook_payload_rejects_unusable_input(self):
        for raw in ("", "not-json", "[]", '"text"'):
            with self.subTest(raw=raw):
                self.assertEqual({}, runtime.read_hook_payload(io.StringIO(raw)))

    # 功能：验证测试和高级用户可以覆盖状态目录
    def test_state_directory_can_be_overridden(self):
        custom_state = self.root / "custom-state"
        with mock.patch.dict(
            os.environ,
            {"DOGDOING_STATE_DIR": str(custom_state)},
            clear=False,
        ):
            self.assertEqual(custom_state.resolve(), runtime.get_state_dir())


if __name__ == "__main__":
    unittest.main()
