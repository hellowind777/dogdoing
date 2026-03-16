#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dogdoing Notification — Desktop + sound notifications.

Sub-commands:
    python notify.py route          — Route Stop hook payload (reads stdin)
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
SOUND_EVENTS = ("complete",)
_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_ICON = _PLUGIN_ROOT / "assets" / "icons" / "dogdoing.png"
_ICON_SMALL = _PLUGIN_ROOT / "assets" / "icons" / "dogdoing-64.png"


# ═══════════════════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════════════════

def _read_notify_level() -> int:
    """Read notify_level from settings.json. Priority:
    1. $CLAUDE_PLUGIN_ROOT/settings.json
    2. $CLAUDE_PLUGIN_DIR/settings.json
    3. Script-relative ../settings.json
    4. Default: 3
    """
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
            level = data.get("notify_level")
            if level is not None:
                return int(level)
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            continue
    return 3


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
    else:
        print(f"Usage: {sys.argv[0]} desktop [msg] | sound <event> | route")
        sys.exit(1)


if __name__ == "__main__":
    main()
