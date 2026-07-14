"""成就、连击和错误追踪测试。"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "plugins" / "dogdoing"
SCRIPTS_DIR = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import runtime  # noqa: E402
import tracker  # noqa: E402


# 功能：验证 Dogdoing 的成就、连击和失败状态机
class TrackerTests(unittest.TestCase):
    # 功能：为每项追踪测试创建隔离状态并关闭系统级副作用
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
        self.sound = mock.patch.object(tracker, "_play_sound")
        self.process = mock.patch.object(tracker.subprocess, "Popen")
        self.sound.start()
        self.process.start()

    # 功能：清理追踪测试的补丁和临时状态目录
    def tearDown(self):
        self.process.stop()
        self.sound.stop()
        self.environment.stop()
        self.temporary.cleanup()

    # 功能：验证四个连击阈值会映射到正确级别
    def test_combo_levels_cover_all_thresholds(self):
        expectations = {
            0: 0,
            2: 0,
            3: 1,
            5: 2,
            10: 3,
            20: 4,
            99: 4,
        }
        for combo, level in expectations.items():
            with self.subTest(combo=combo):
                self.assertEqual(level, tracker._combo_level_for(combo))

    # 功能：验证连续成功五次会达到二级连击并解锁连旺
    def test_five_successes_unlock_combo_achievement(self):
        for _ in range(5):
            tracker.record_tool_success({"tool_name": "exec_command", "tool_input": {}})
        state = tracker.load_state()
        achievements = tracker.load_achievements()
        self.assertEqual(5, state["combo"])
        self.assertEqual(2, state["combo_level"])
        self.assertIsNotNone(achievements["combo_5"])

    # 功能：验证连续成功十次会解锁累计任务成就
    def test_ten_successes_unlock_ten_tasks_achievement(self):
        for _ in range(10):
            tracker.record_tool_success({"tool_name": "exec_command", "tool_input": {}})
        self.assertIsNotNone(tracker.load_achievements()["ten_tasks"])

    # 功能：验证 Claude Agent 调用会解锁首次召唤成就
    def test_claude_agent_unlocks_first_summon(self):
        tracker.record_tool_success(
            {
                "tool_name": "Agent",
                "tool_input": {"subagent_type": "dogdoing:dogdoing"},
            }
        )
        self.assertEqual(1, tracker.load_state()["summon_count"])
        self.assertIsNotNone(tracker.load_achievements()["first_summon"])

    # 功能：验证 Codex 协作工具调用会解锁首次召唤成就
    def test_codex_agent_unlocks_first_summon(self):
        tracker.record_tool_success(
            {
                "tool_name": "collaboration.spawn_agent",
                "tool_input": {"task_name": "dogdoing", "message": "验证改动"},
            }
        )
        self.assertEqual(1, tracker.load_state()["summon_count"])
        self.assertIsNotNone(tracker.load_achievements()["first_summon"])

    # 功能：验证首次失败解锁错误成就并重置连击
    def test_failure_unlocks_bug_found_and_resets_combo(self):
        tracker.record_tool_success({"tool_name": "exec_command"})
        tracker.record_tool_failure({"error": "boom"})
        state = tracker.load_state()
        self.assertEqual(0, state["combo"])
        self.assertEqual(1, state["error_streak"])
        self.assertIsNotNone(tracker.load_achievements()["bug_found"])

    # 功能：验证连续失败三次触发纯中文安慰文本
    def test_three_failures_trigger_this_is_fine(self):
        output = io.StringIO()
        with redirect_stderr(output):
            for _ in range(3):
                tracker.record_tool_failure({"error": "boom"})
        self.assertIn("一切正常。旺。", output.getvalue())
        self.assertNotIn("This is fine", output.getvalue())

    # 功能：验证全部成就名称都使用中文说明
    def test_achievement_messages_are_chinese(self):
        for achievement_id, message in tracker.ACHIEVEMENTS.items():
            with self.subTest(achievement_id=achievement_id):
                self.assertFalse(any("A" <= char <= "z" for char in message))

    # 功能：验证 Drog 提示状态会在下一次成功事件解锁并消费
    def test_drog_trigger_unlocks_achievement_once(self):
        runtime.write_json_atomic(self.state_dir / "state.json", {"drog_triggered": True})
        tracker.record_tool_success({"tool_name": "exec_command"})
        self.assertFalse(tracker.load_state()["drog_triggered"])
        self.assertIsNotNone(tracker.load_achievements()["drog_awakened"])

    # 功能：验证关闭追踪后不会创建任何状态文件
    def test_disabled_tracker_does_not_write_state(self):
        with mock.patch.object(tracker, "_is_enabled", return_value=False):
            tracker.record_tool_success({"tool_name": "exec_command"})
            tracker.record_tool_failure({"error": "boom"})
        self.assertFalse(self.state_dir.exists())

    # 功能：验证损坏和不完整的状态文件会与默认状态合并
    def test_state_loading_recovers_defaults(self):
        self.state_dir.mkdir(parents=True)
        (self.state_dir / "state.json").write_text('{"combo": 7}', encoding="utf-8")
        state = tracker.load_state()
        self.assertEqual(7, state["combo"])
        self.assertEqual(0, state["error_streak"])
        (self.state_dir / "achievements.json").write_text("not-json", encoding="utf-8")
        self.assertEqual(set(tracker.ACHIEVEMENTS), set(tracker.load_achievements()))


if __name__ == "__main__":
    unittest.main()
