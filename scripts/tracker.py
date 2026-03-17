#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dogdoing Tracker — 成就系统 / 连击系统 / 错误追踪 / This is Fine

CLI:
    python tracker.py post_tool_use       # PostToolUse hook
    python tracker.py post_tool_failure   # PostToolUseFailure hook
"""

import json
import subprocess
import sys
import io
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    for stream_name in ("stdin", "stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if hasattr(stream, "buffer"):
            setattr(sys, stream_name,
                    io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace"))

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_STATE_DIR = Path.home() / ".dogdoing"
_STATE_FILE = _STATE_DIR / "state.json"
_ACHIEVEMENTS_FILE = _STATE_DIR / "achievements.json"

# ── 连击级别 ──────────────────────────────────────────────────────────
COMBO_LEVELS = [
    (3,  "🐕 旺！"),
    (5,  "🐕 旺旺！"),
    (10, "🐕 旺旺旺旺！"),
    (20, "🐕 旺旺旺旺旺旺旺旺！！！冲冲冲！"),
]

# ── 成就定义 ──────────────────────────────────────────────────────────
ACHIEVEMENTS = {
    "first_summon":  "🗡️ 初出茅庐 — First summon!",
    "ten_tasks":     "🛡️ 刀盾合璧 — 10 tasks completed!",
    "combo_5":       "🔥 连旺 — 5x combo streak!",
    "bug_found":     "💀 狗头保命 — First error detected!",
    "drog_awakened": "🐸 Drog 觉醒 — Drog awakened!",
}

# ── 默认状态 ──────────────────────────────────────────────────────────
_DEFAULT_STATE = {
    "combo": 0,
    "combo_level": 0,
    "error_streak": 0,
    "total_tasks": 0,
    "summon_count": 0,
    "drog_triggered": False,
}
_DEFAULT_ACHIEVEMENTS = {k: None for k in ACHIEVEMENTS}


# ── 配置读取 ──────────────────────────────────────────────────────────

def _read_setting(key: str, default=None):
    import os
    for env_var in ("CLAUDE_PLUGIN_ROOT", "CLAUDE_PLUGIN_DIR"):
        val = os.environ.get(env_var)
        if val:
            try:
                data = json.loads((Path(val) / "settings.json").read_text(encoding="utf-8"))
                v = data.get(key)
                if v is not None:
                    return v
            except (OSError, json.JSONDecodeError):
                pass
    try:
        data = json.loads((_PLUGIN_ROOT / "settings.json").read_text(encoding="utf-8"))
        return data.get(key, default)
    except (OSError, json.JSONDecodeError):
        return default


def _is_enabled() -> bool:
    return bool(_read_setting("tracker_enabled", True))


# ── 状态读写 ──────────────────────────────────────────────────────────

def _load_state() -> dict:
    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        merged = {**_DEFAULT_STATE, **data}
        return merged
    except (OSError, json.JSONDecodeError):
        return dict(_DEFAULT_STATE)


def _save_state(state: dict):
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_achievements() -> dict:
    try:
        data = json.loads(_ACHIEVEMENTS_FILE.read_text(encoding="utf-8"))
        merged = {**_DEFAULT_ACHIEVEMENTS, **data}
        return merged
    except (OSError, json.JSONDecodeError):
        return dict(_DEFAULT_ACHIEVEMENTS)


def _save_achievements(ach: dict):
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    _ACHIEVEMENTS_FILE.write_text(json.dumps(ach, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 声音播放 ──────────────────────────────────────────────────────────

def _play_sound(event: str):
    """Non-blocking sound play via notify.py."""
    script = _PLUGIN_ROOT / "scripts" / "notify.py"
    try:
        subprocess.Popen(
            [sys.executable, str(script), "sound", event],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass

# ── 成就解锁 ──────────────────────────────────────────────────────────

def _unlock(ach: dict, achievement_id: str) -> bool:
    """Unlock an achievement if not already unlocked. Returns True if newly unlocked."""
    if ach.get(achievement_id) is not None:
        return False
    ach[achievement_id] = datetime.now(timezone.utc).isoformat()
    name = ACHIEVEMENTS.get(achievement_id, achievement_id)
    print(f"\n🏆 成就解锁: {name}\n", file=sys.stderr)
    # Desktop notification
    try:
        script = _PLUGIN_ROOT / "scripts" / "notify.py"
        subprocess.Popen(
            [sys.executable, str(script), "desktop", f"🏆 {name}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass
    return True


# ── 连击级别计算 ──────────────────────────────────────────────────────

def _combo_level_for(combo: int) -> int:
    """Return the combo level (0-4) for a given combo count."""
    level = 0
    for i, (threshold, _) in enumerate(COMBO_LEVELS):
        if combo >= threshold:
            level = i + 1
    return level


# ── PostToolUse 处理 ──────────────────────────────────────────────────

def post_tool_use():
    if not _is_enabled():
        return
    # Read stdin
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, Exception):
        data = {}

    state = _load_state()
    ach = _load_achievements()

    # Reset error streak
    state["error_streak"] = 0
    state["total_tasks"] = state.get("total_tasks", 0) + 1

    # Combo
    state["combo"] = state.get("combo", 0) + 1
    old_level = state.get("combo_level", 0)
    new_level = _combo_level_for(state["combo"])
    if new_level > old_level:
        state["combo_level"] = new_level
        msg = COMBO_LEVELS[new_level - 1][1]
        print(msg, file=sys.stderr)
        _play_sound("combo")

    # Check dogdoing subagent summon
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except (json.JSONDecodeError, ValueError):
            tool_input = {}
    subagent_type = tool_input.get("subagent_type", "") if isinstance(tool_input, dict) else ""
    if tool_name == "Agent" and "dogdoing" in str(subagent_type).lower():
        state["summon_count"] = state.get("summon_count", 0) + 1
        _unlock(ach, "first_summon")

    # Check ten_tasks
    if state["total_tasks"] >= 10:
        _unlock(ach, "ten_tasks")

    # Check combo_5
    if state["combo"] >= 5:
        _unlock(ach, "combo_5")

    # Check drog_triggered
    if state.get("drog_triggered"):
        _unlock(ach, "drog_awakened")
        state["drog_triggered"] = False

    _save_state(state)
    _save_achievements(ach)

# ── PostToolUseFailure 处理 ────────────────────────────────────────────

def post_tool_failure():
    if not _is_enabled():
        return
    # Read stdin
    try:
        raw = sys.stdin.read()
    except Exception:
        pass

    state = _load_state()
    ach = _load_achievements()

    # Reset combo
    state["combo"] = 0
    state["combo_level"] = 0

    # Error streak
    state["error_streak"] = state.get("error_streak", 0) + 1
    _play_sound("error")

    # bug_found achievement
    _unlock(ach, "bug_found")

    # This is Fine mode
    if state["error_streak"] >= 3:
        print(
            "\n🐕 刀盾狗：一切正常。旺。(This is fine. Wow.)\n",
            file=sys.stderr,
        )

    _save_state(state)
    _save_achievements(ach)


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "post_tool_use":
        post_tool_use()
    elif cmd == "post_tool_failure":
        post_tool_failure()
    else:
        print(f"Usage: {sys.argv[0]} post_tool_use|post_tool_failure", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
