#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dogdoing Notification & Hook Router.

Sub-commands:
    python notify.py route          — Route Stop hook payload (reads stdin)
    python notify.py inject         — SessionStart hook: output INJECT.md if enabled
    python notify.py remind         — UserPromptSubmit hook: output reminder if enabled
    python notify.py desktop [msg]  — Desktop notification
    python notify.py sound <event>  — Play sound for event
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import runtime as shared_runtime

TITLE = "刀盾狗"
DEFAULT_MSG = "刀盾狗：任务已完成。"
SOUND_EVENTS = ("complete", "error", "combo", "drog")
_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_ICON = _PLUGIN_ROOT / "assets" / "icons" / "dogdoing.png"
_ICON_SMALL = _PLUGIN_ROOT / "assets" / "icons" / "dogdoing-64.png"


# ═══════════════════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════════════════

# 功能：从共享配置文件读取通知模块所需的单个配置项
def _read_setting(key: str, default=None):
    """Read a setting from settings.json."""
    return shared_runtime.read_setting(key, default)


# 功能：读取并校验 0 到 3 范围内的通知级别
def _read_notify_level() -> int:
    try:
        level = int(_read_setting("notify_level", 3))
    except (TypeError, ValueError):
        return 3
    return level if level in (0, 1, 2, 3) else 3


# ═══════════════════════════════════════════════════════════════════════════
# Desktop notification (cross-platform)
# ═══════════════════════════════════════════════════════════════════════════

# 功能：根据当前操作系统发送桌面通知并在失败时降级响铃
def desktop_notify(msg: str = DEFAULT_MSG):
    """Send a desktop notification. Works on Windows/macOS/Linux."""
    if sys.platform == "win32":
        _win_toast(TITLE, msg, str(_ICON_SMALL) if _ICON_SMALL.exists() else "", show_title=False)

    elif sys.platform == "darwin":
        try:
            subprocess.run(["osascript", "-e",
                            f'display notification "{msg}" with title "{TITLE}"'],
                           capture_output=True, timeout=5)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print("\a", end="", file=sys.stderr, flush=True)

    else:  # Linux
        try:
            cmd = ["notify-send", TITLE, msg]
            if _ICON.exists():
                cmd = ["notify-send", "-i", str(_ICON), TITLE, msg]
            r = subprocess.run(cmd, capture_output=True, timeout=5)
            if r.returncode == 0:
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        print("\a", end="", file=sys.stderr, flush=True)


# ─── Windows Toast (inline, zero-dep, based on winotify) ─────────────

_WIN_TOAST_TEMPLATE = r"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
[Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$Template = @"
<toast duration="short">
    <visual>
        <binding template="ToastImageAndText02">
            <image id="1" src="{icon}" />
            <text id="1"><![CDATA[{title}]]></text>
            <text id="2"><![CDATA[{msg}]]></text>
        </binding>
    </visual>
    <actions></actions>
    <audio silent="true" />
</toast>
"@
$SerializedXml = New-Object Windows.Data.Xml.Dom.XmlDocument
$SerializedXml.LoadXml($Template)
$Toast = [Windows.UI.Notifications.ToastNotification]::new($SerializedXml)
$Toast.Tag = "{tag}"
$Toast.Group = "{group}"
$Notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{app_id}")
$Notifier.Show($Toast);
"""


# 功能：通过 Windows Runtime 和 PowerShell 异步显示 Toast 通知
def _win_toast(title: str, msg: str, icon: str = "", show_title: bool = True):
    """Show a Windows toast notification (inline, no external deps)."""
    script = _WIN_TOAST_TEMPLATE.format(
        app_id=title,
        title=title if show_title else msg,
        msg=msg if show_title else " ",
        icon=icon,
        tag=title,
        group=title,
    )
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.Popen(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-Command", script],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=si,
        )
    except Exception:
        print("\a", end="", file=sys.stderr, flush=True)


# ═══════════════════════════════════════════════════════════════════════════
# Sound player (cross-platform)
# ═══════════════════════════════════════════════════════════════════════════

# 功能：查找指定事件对应的本地 WAV 音频资源
def _find_sound(event: str) -> "Path | None":
    wav = _PLUGIN_ROOT / "assets" / "sounds" / f"{event}.wav"
    return wav if wav.exists() else None


# 功能：使用当前操作系统可用的播放器播放指定事件声音
def play_sound(event: str):
    if event not in SOUND_EVENTS:
        return
    wav = _find_sound(event)
    if not wav:
        print("\a", end="", file=sys.stderr, flush=True)
        return
    try:
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(str(wav), winsound.SND_FILENAME)
        elif sys.platform == "darwin":
            subprocess.Popen(["afplay", str(wav)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:  # Linux: aplay -> paplay fallback
            for cmd in (["aplay", "-q"], ["paplay"]):
                try:
                    subprocess.Popen(cmd + [str(wav)],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
                except FileNotFoundError:
                    continue
            print("\a", end="", file=sys.stderr, flush=True)
    except Exception:
        print("\a", end="", file=sys.stderr, flush=True)


# ═══════════════════════════════════════════════════════════════════════════
# Route (Stop hook)
# ═══════════════════════════════════════════════════════════════════════════

# 功能：根据结束事件载荷选择桌面通知和完成声音
def route_stop(payload: dict) -> None:
    stop_reason = str(payload.get("stop_reason") or payload.get("reason") or "").lower()
    status = str(payload.get("status") or "").lower()
    if stop_reason in ("tool_use", "in_progress") or status in ("tool_use", "in_progress"):
        return

    level = _read_notify_level()
    if level <= 0:
        return
    if level in (1, 3):
        desktop_notify()
    if level in (2, 3):
        play_sound("complete")


# 功能：兼容旧通知 CLI，从标准输入读取停止事件并转交数据 API
def _route():
    route_stop(shared_runtime.read_hook_payload())


# ═══════════════════════════════════════════════════════════════════════════
# Hook output (SessionStart / UserPromptSubmit)
# ═══════════════════════════════════════════════════════════════════════════

_REMIND_SUBAGENT_CLAUDE = (
    "[刀盾狗] 本次回复必须包含刀盾狗。请使用 Agent 工具和 "
    "subagent_type dogdoing:dogdoing（不可用时使用 dogdoing）启动可并行的具体工作，"
    "并在最终回复前等待结果；工具不可用时，由主代理完成同等验证并附上刀盾狗贡献。"
    "所有刀盾狗提示必须使用简体中文，叫声使用“旺”，不能使用“汪”。"
)

_REMIND_SUBAGENT_CODEX = (
    "[刀盾狗] 本次回复必须包含刀盾狗。请使用 collaboration.spawn_agent，"
    "并设置 task_name 为 dogdoing，启动可并行的具体工作；最终回复前必须等待并汇总结果。"
    "协作工具不可用时，由主代理完成同等验证并附上刀盾狗贡献。"
    "所有刀盾狗提示必须使用简体中文，叫声使用“旺”，不能使用“汪”。"
)

_REMIND_CHEER = (
    "[刀盾狗] 请在回复末尾附上刀盾狗喝彩或叫声。"
    "所有提示必须使用简体中文，叫声使用“旺”，不能使用“汪”。"
)


# 功能：读取插件内一段注入指令，文件缺失时返回空文本
def _read_injection_file(name: str) -> str:
    path = _PLUGIN_ROOT / name
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return ""


# 功能：按照宿主平台、配置开关和时间生成完整会话注入文本
def build_injection(platform: str, hour: "int | None" = None) -> str:
    subagent = _read_setting("subagent_enabled", True)
    cheer = _read_setting("cheer_enabled", True)
    drog = _read_setting("drog_enabled", True)
    if not subagent and not cheer and not drog:
        return ""

    sections = [_read_injection_file("INJECT.md")]
    if subagent:
        name = "INJECT_SUBAGENT_CODEX.md" if platform.lower() == "codex" else "INJECT_SUBAGENT.md"
        sections.append(_read_injection_file(name))
    if cheer:
        sections.append(_read_injection_file("INJECT_CHEER.md"))
    if drog:
        drog_content = _read_injection_file("INJECT_DROG.md")
        current_hour = datetime.now().hour if hour is None else hour
        if not 2 <= current_hour < 5:
            marker = "## [深夜模式]"
            marker_index = drog_content.find(marker)
            if marker_index >= 0:
                drog_content = drog_content[:marker_index].rstrip()
        sections.append(drog_content)
    return "\n\n".join(section for section in sections if section)


# 功能：兼容旧注入 CLI，输出指定平台的会话上下文
def _inject(platform: str = "claude"):
    shared_runtime.read_hook_payload()
    content = build_injection(platform)
    if content:
        print(content)


# 功能：从 Claude 或 Codex 的提示载荷中提取用户输入文本
def _extract_user_input(payload: dict) -> str:
    for key in ("user_input", "prompt", "user_prompt", "message", "input"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return ""


# 功能：处理每轮用户提示，记录 Drog 触发并返回宿主对应的提醒文本
def handle_prompt(payload: dict, platform: str) -> str:
    user_input = _extract_user_input(payload)
    if _read_setting("drog_enabled", True) and "~drog" in user_input.lower():
            _set_drog_triggered()
    subagent = _read_setting("subagent_enabled", True)
    cheer = _read_setting("cheer_enabled", True)
    if subagent:
        if platform.lower() == "codex":
            return _REMIND_SUBAGENT_CODEX
        return _REMIND_SUBAGENT_CLAUDE
    return _REMIND_CHEER if cheer else ""


# 功能：兼容旧提醒 CLI，从标准输入读取提示并输出提醒文本
def _remind(platform: str = "claude"):
    reminder = handle_prompt(shared_runtime.read_hook_payload(), platform)
    if reminder:
        print(reminder)


# 功能：在共享状态文件中记录 Drog 已被用户触发
def _set_drog_triggered():
    """Write drog_triggered=true to state.json for tracker to pick up."""
    state_file = shared_runtime.get_state_dir() / "state.json"
    data = shared_runtime.read_json(state_file, {})
    data["drog_triggered"] = True
    shared_runtime.write_json_atomic(state_file, data)


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

# 功能：解析通知脚本的兼容 CLI 子命令并执行对应操作
def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "desktop"
    if cmd == "desktop":
        msg = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_MSG
        try:
            sys.stdin.read()
        except Exception:
            pass
        desktop_notify(msg)
    elif cmd == "sound" and len(sys.argv) > 2:
        play_sound(sys.argv[2])
    elif cmd == "route":
        _route()
    elif cmd == "inject":
        _inject()
    elif cmd == "remind":
        _remind()
    else:
        print(f"用法：{sys.argv[0]} route|inject|remind|desktop [消息]|sound <事件>")
        sys.exit(1)


if __name__ == "__main__":
    shared_runtime.configure_utf8_streams()
    main()
