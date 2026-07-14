"""Windows、macOS 与 Linux 通知分支测试。"""

import io
import sys
import types
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock


PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "plugins" / "dogdoing"
SCRIPTS_DIR = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import notify  # noqa: E402


# 功能：验证每种桌面系统使用正确的通知和音频实现
class CrossPlatformNotifyTests(unittest.TestCase):
    # 功能：验证 Windows 桌面通知使用内置 Toast 实现
    def test_windows_desktop_uses_toast(self):
        with mock.patch.object(notify.sys, "platform", "win32"), mock.patch.object(
            notify,
            "_win_toast",
        ) as toast:
            notify.desktop_notify("完成")
        toast.assert_called_once()
        self.assertEqual("完成", toast.call_args.args[1])

    # 功能：验证 macOS 桌面通知调用 osascript
    def test_macos_desktop_uses_osascript(self):
        with mock.patch.object(notify.sys, "platform", "darwin"), mock.patch.object(
            notify.subprocess,
            "run",
        ) as run:
            notify.desktop_notify("done")
        self.assertEqual("osascript", run.call_args.args[0][0])

    # 功能：验证 Linux 桌面通知调用 notify-send 并携带图标
    def test_linux_desktop_uses_notify_send(self):
        completed = mock.Mock(returncode=0)
        with mock.patch.object(notify.sys, "platform", "linux"), mock.patch.object(
            notify.subprocess,
            "run",
            return_value=completed,
        ) as run:
            notify.desktop_notify("done")
        command = run.call_args.args[0]
        self.assertEqual("notify-send", command[0])
        self.assertIn("-i", command)

    # 功能：验证 Windows 音频使用 winsound 播放本地 WAV
    def test_windows_sound_uses_winsound(self):
        winsound = types.SimpleNamespace(
            SND_FILENAME=1,
            PlaySound=mock.Mock(),
        )
        with mock.patch.object(notify.sys, "platform", "win32"), mock.patch.dict(
            sys.modules,
            {"winsound": winsound},
        ):
            notify.play_sound("complete")
        winsound.PlaySound.assert_called_once()
        self.assertTrue(winsound.PlaySound.call_args.args[0].endswith("complete.wav"))

    # 功能：验证 macOS 音频使用 afplay 异步播放
    def test_macos_sound_uses_afplay(self):
        with mock.patch.object(notify.sys, "platform", "darwin"), mock.patch.object(
            notify.subprocess,
            "Popen",
        ) as popen:
            notify.play_sound("complete")
        self.assertEqual("afplay", popen.call_args.args[0][0])

    # 功能：验证 Linux 音频优先使用 aplay
    def test_linux_sound_prefers_aplay(self):
        with mock.patch.object(notify.sys, "platform", "linux"), mock.patch.object(
            notify.subprocess,
            "Popen",
        ) as popen:
            notify.play_sound("complete")
        self.assertEqual("aplay", popen.call_args.args[0][0])

    # 功能：验证 Linux 缺少 aplay 时会回退到 paplay
    def test_linux_sound_falls_back_to_paplay(self):
        with mock.patch.object(notify.sys, "platform", "linux"), mock.patch.object(
            notify.subprocess,
            "Popen",
            side_effect=[FileNotFoundError(), mock.Mock()],
        ) as popen:
            notify.play_sound("complete")
        self.assertEqual(2, popen.call_count)
        self.assertEqual("paplay", popen.call_args_list[1].args[0][0])

    # 功能：验证资源缺失时声音功能安全降级为终端响铃
    def test_missing_sound_falls_back_to_terminal_bell(self):
        output = io.StringIO()
        with mock.patch.object(notify, "_find_sound", return_value=None), redirect_stderr(output):
            notify.play_sound("complete")
        self.assertEqual("\a", output.getvalue())

    # 功能：验证未知声音事件不会启动任何系统进程
    def test_unknown_sound_event_is_ignored(self):
        with mock.patch.object(notify.subprocess, "Popen") as popen:
            notify.play_sound("unknown")
        popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
