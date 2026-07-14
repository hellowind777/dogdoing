"""通知、会话注入和 Drog 触发测试。"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "plugins" / "dogdoing"
SCRIPTS_DIR = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import notify  # noqa: E402


# 功能：验证通知路由和双平台提示注入行为
class NotifyTests(unittest.TestCase):
    # 功能：为每项测试隔离用户状态目录
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.temporary.name) / "state"
        self.environment = mock.patch.dict(
            os.environ,
            {
                "CODEX_PLUGIN_ROOT": str(PLUGIN_ROOT),
                "DOGDOING_STATE_DIR": str(self.state_dir),
            },
            clear=False,
        )
        self.environment.start()

    # 功能：移除测试环境变量并清理临时状态
    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    # 功能：验证 Codex 注入使用原生协作工具并包含手动 Skill 语法
    def test_codex_injection_mentions_spawn_agent(self):
        content = notify.build_injection(platform="codex", hour=12)
        self.assertIn("collaboration.spawn_agent", content)
        self.assertIn("$dogdoing", content)
        self.assertNotIn("run_in_background", content)

    # 功能：验证 Claude 注入继续保留已注册子代理调用方式
    def test_claude_injection_keeps_agent_call(self):
        content = notify.build_injection(platform="claude", hour=12)
        self.assertIn('Agent(subagent_type="dogdoing:dogdoing"', content)
        self.assertIn("run_in_background=true", content)

    # 功能：验证每轮提醒和默认桌面通知只使用中文提示
    def test_fixed_user_prompts_are_chinese(self):
        self.assertEqual("刀盾狗", notify.TITLE)
        self.assertEqual("刀盾狗：任务已完成。", notify.DEFAULT_MSG)
        for reminder in (
            notify._REMIND_SUBAGENT_CLAUDE,
            notify._REMIND_SUBAGENT_CODEX,
            notify._REMIND_CHEER,
        ):
            with self.subTest(reminder=reminder):
                self.assertIn("[刀盾狗]", reminder)
                self.assertNotIn("[Dogdoing]", reminder)

    # 功能：验证全部行为开关关闭时不注入额外上下文
    def test_disabled_features_produce_no_injection(self):
        with mock.patch.object(notify, "_read_setting", return_value=False):
            self.assertEqual("", notify.build_injection(platform="codex", hour=12))

    # 功能：验证关闭子代理后仍可独立启用喝彩提示
    def test_cheer_can_run_without_subagent(self):
        settings = {
            "subagent_enabled": False,
            "cheer_enabled": True,
            "drog_enabled": False,
        }
        with mock.patch.object(notify, "_read_setting", side_effect=lambda key, default: settings[key]):
            content = notify.build_injection(platform="codex", hour=12)
        self.assertIn("喝彩模式", content)
        self.assertNotIn("collaboration.spawn_agent", content)

    # 功能：验证非深夜时段会移除 Drog 深夜随机提示段
    def test_daytime_injection_strips_late_night_mode(self):
        content = notify.build_injection(platform="codex", hour=12)
        self.assertNotIn("[深夜模式]", content)

    # 功能：验证凌晨时段保留 Drog 深夜随机提示段
    def test_late_night_injection_keeps_late_night_mode(self):
        content = notify.build_injection(platform="codex", hour=3)
        self.assertIn("[深夜模式]", content)

    # 功能：验证 Codex 用户提示字段可以触发 Drog 成就状态
    def test_codex_prompt_detects_drog_trigger(self):
        reminder = notify.handle_prompt(
            {"prompt": "请让 ~drog 看一下"},
            platform="codex",
        )
        state = json.loads((self.state_dir / "state.json").read_text(encoding="utf-8"))
        self.assertTrue(state["drog_triggered"])
        self.assertIn("collaboration.spawn_agent", reminder)

    # 功能：验证正常用户提示不会创建 Drog 状态文件
    def test_regular_prompt_does_not_trigger_drog(self):
        notify.handle_prompt({"user_input": "普通任务"}, platform="claude")
        self.assertFalse((self.state_dir / "state.json").exists())

    # 功能：验证工具调用尚未结束时不会发送完成通知
    def test_tool_use_stop_reason_is_silent(self):
        with mock.patch.object(notify, "desktop_notify") as desktop, mock.patch.object(
            notify,
            "play_sound",
        ) as sound:
            notify.route_stop({"stop_reason": "tool_use"})
        desktop.assert_not_called()
        sound.assert_not_called()

    # 功能：验证 Codex 的继续执行状态同样不会发送完成通知
    def test_codex_in_progress_status_is_silent(self):
        with mock.patch.object(notify, "desktop_notify") as desktop, mock.patch.object(
            notify,
            "play_sound",
        ) as sound:
            notify.route_stop({"status": "in_progress"})
        desktop.assert_not_called()
        sound.assert_not_called()

    # 功能：验证四个通知级别分别调用正确的通知通道
    def test_notification_levels_route_expected_channels(self):
        expectations = {
            0: (0, 0),
            1: (1, 0),
            2: (0, 1),
            3: (1, 1),
        }
        for level, expected in expectations.items():
            with self.subTest(level=level), mock.patch.object(
                notify,
                "_read_notify_level",
                return_value=level,
            ), mock.patch.object(notify, "desktop_notify") as desktop, mock.patch.object(
                notify,
                "play_sound",
            ) as sound:
                notify.route_stop({"stop_reason": "end_turn"})
                self.assertEqual(expected[0], desktop.call_count)
                self.assertEqual(expected[1], sound.call_count)

    # 功能：验证无效通知级别安全回退到桌面加声音的默认级别
    def test_invalid_notification_level_uses_default(self):
        with mock.patch.object(notify, "_read_setting", return_value="loud"):
            self.assertEqual(3, notify._read_notify_level())


if __name__ == "__main__":
    unittest.main()
