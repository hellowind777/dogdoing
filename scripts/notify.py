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

import json
import subprocess
import sys
import io
from pathlib import Path

if sys.platform == 'win32':
    for stream_name in ('stdin', 'stdout', 'stderr'):
        stream = getattr(sys, stream_name)
        if hasattr(stream, 'buffer'):
            setattr(sys, stream_name,
                    io.TextIOWrapper(stream.buffer, encoding='utf-8', errors='replace'))

TITLE = "Dogdoing"
DEFAULT_MSG = "What the dog doing???"
SOUND_EVENTS = ("complete", "error", "combo", "drog")
_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_ICON = _PLUGIN_ROOT / "assets" / "icons" / "dogdoing.png"
_ICON_SMALL = _PLUGIN_ROOT / "assets" / "icons" / "dogdoing-64.png"


# ═══════════════════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════════════════

def _read_setting(key: str, default=None):
    """Read a setting from settings.json."""
    import os
    candidates = []
    for env_var in ("CLAUDE_PLUGIN_ROOT", "CLAUDE_PLUGIN_DIR"):
        val = os.environ.get(env_var)
        if val:
            candidates.append(Path(val) / "settings.json")
    candidates.append(_PLUGIN_ROOT / "settings.json")

    for p in candidates:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            val = data.get(key)
            if val is not None:
                return val
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            continue
    return default


def _read_notify_level() -> int:
    return int(_read_setting("notify_level", 3))


# ═══════════════════════════════════════════════════════════════════════════
# Desktop notification (cross-platform)
# ═══════════════════════════════════════════════════════════════════════════

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

def _find_sound(event: str) -> "Path | None":
    wav = _PLUGIN_ROOT / "assets" / "sounds" / f"{event}.wav"
    return wav if wav.exists() else None


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

def _route():
    """Route Stop hook payload to sound + desktop notification."""
    try:
        raw = sys.stdin.read()
    except Exception:
        return

    # Parse stop_reason
    stop_reason = ""
    if raw.strip():
        try:
            data = json.loads(raw)
            stop_reason = data.get("stop_reason", "")
        except (json.JSONDecodeError, ValueError):
            pass

    # Silent on tool_use — agent is still working
    if stop_reason == "tool_use":
        return

    level = _read_notify_level()
    if level <= 0:
        return
    if level in (1, 3):
        desktop_notify()
    if level in (2, 3):
        play_sound("complete")


# ═══════════════════════════════════════════════════════════════════════════
# Hook output (SessionStart / UserPromptSubmit)
# ═══════════════════════════════════════════════════════════════════════════

_REMIND_SUBAGENT = (
    "[Dogdoing] You MUST include Dogdoing in this response. "
    "Use Agent tool with subagent_type dogdoing:dogdoing (or dogdoing) to launch parallel work, "
    "OR append a Dogdoing section at the end. "
    "Chinese context = Chinese output. Bark sounds: CN use 旺 (NOT 汪), EN use Wow (NOT Woof)."
)

_REMIND_CHEER = (
    "[Dogdoing] Append a Dogdoing cheer or bark at the end of your response. "
    "Chinese context = Chinese output. CN use 旺 (NOT 汪), EN use Wow (NOT Woof)."
)


def _inject():
    """SessionStart hook: output INJECT*.md based on config."""
    try:
        sys.stdin.read()
    except Exception:
        pass
    subagent = _read_setting("subagent_enabled", True)
    cheer = _read_setting("cheer_enabled", True)
    drog = _read_setting("drog_enabled", True)
    if not subagent and not cheer and not drog:
        return
    # Base
    base = _PLUGIN_ROOT / "INJECT.md"
    if base.exists():
        print(base.read_text(encoding="utf-8"))
    # Subagent section
    if subagent:
        f = _PLUGIN_ROOT / "INJECT_SUBAGENT.md"
        if f.exists():
            print(f.read_text(encoding="utf-8"))
    # Cheer section
    if cheer:
        f = _PLUGIN_ROOT / "INJECT_CHEER.md"
        if f.exists():
            print(f.read_text(encoding="utf-8"))
    # Drog section
    if drog:
        f = _PLUGIN_ROOT / "INJECT_DROG.md"
        if f.exists():
            content = f.read_text(encoding="utf-8")
            # Strip late night section unless 2:00-5:00
            from datetime import datetime
            hour = datetime.now().hour
            if 2 <= hour < 5:
                print(content)
            else:
                # Remove [LATE NIGHT MODE] section
                marker = "## [LATE NIGHT MODE]"
                idx = content.find(marker)
                if idx >= 0:
                    print(content[:idx].rstrip())
                else:
                    print(content)


def _remind():
    """UserPromptSubmit hook: output reminder based on config + detect ~drog."""
    try:
        raw = sys.stdin.read()
    except Exception:
        raw = ""
    # Detect ~drog trigger
    if raw.strip():
        try:
            payload = json.loads(raw)
            user_input = payload.get("user_input", "")
        except (json.JSONDecodeError, ValueError):
            user_input = raw
        if "~drog" in user_input.lower():
            _set_drog_triggered()
    subagent = _read_setting("subagent_enabled", True)
    cheer = _read_setting("cheer_enabled", True)
    if subagent:
        print(_REMIND_SUBAGENT)
    elif cheer:
        print(_REMIND_CHEER)


def _set_drog_triggered():
    """Write drog_triggered=true to state.json for tracker to pick up."""
    state_dir = Path.home() / ".dogdoing"
    state_file = state_dir / "state.json"
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    data["drog_triggered"] = True
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

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
        print(f"Usage: {sys.argv[0]} route|inject|remind|desktop [msg]|sound <event>")
        sys.exit(1)


if __name__ == "__main__":
    main()
