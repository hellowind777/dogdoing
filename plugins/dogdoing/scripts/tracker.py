#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""刀盾狗追踪器：成就系统、连击系统和错误追踪。

CLI:
    python tracker.py post_tool_use       # PostToolUse hook
    python tracker.py post_tool_failure   # PostToolUseFailure hook
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import runtime as shared_runtime

_PLUGIN_ROOT = Path(__file__).resolve().parent.parent

# ── 连击级别 ──────────────────────────────────────────────────────────
COMBO_LEVELS = [
    (3,  "🐕 旺！"),
    (5,  "🐕 旺旺！"),
    (10, "🐕 旺旺旺旺！"),
    (20, "🐕 旺旺旺旺旺旺旺旺！！！冲冲冲！"),
]

# ── 成就定义 ──────────────────────────────────────────────────────────
ACHIEVEMENTS = {
    "first_summon":  "🗡️ 初出茅庐：首次召唤刀盾狗！",
    "ten_tasks":     "🛡️ 刀盾合璧：已完成十次任务！",
    "combo_5":       "🔥 连旺：达成五连击！",
    "bug_found":     "💀 狗头保命：首次检测到错误！",
    "drog_awakened": "🐸 蛙盾觉醒：蛙盾已苏醒！",
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

# 功能：从共享配置文件读取追踪模块所需的单个配置项
def _read_setting(key: str, default=None):
    return shared_runtime.read_setting(key, default)


# 功能：判断成就、连击和错误追踪功能是否启用
def _is_enabled() -> bool:
    return bool(_read_setting("tracker_enabled", True))


# ── 状态读写 ──────────────────────────────────────────────────────────

# 功能：读取当前用户状态并补齐新版本增加的默认字段
def load_state() -> dict:
    state_file = shared_runtime.get_state_dir() / "state.json"
    data = shared_runtime.read_json(state_file, _DEFAULT_STATE)
    return {**_DEFAULT_STATE, **data}


# 功能：原子保存连击、错误、累计调用和 Drog 状态
def save_state(state: dict) -> None:
    state_file = shared_runtime.get_state_dir() / "state.json"
    shared_runtime.write_json_atomic(state_file, state)


# 功能：读取成就解锁时间并补齐尚未出现的成就项
def load_achievements() -> dict:
    achievements_file = shared_runtime.get_state_dir() / "achievements.json"
    data = shared_runtime.read_json(achievements_file, _DEFAULT_ACHIEVEMENTS)
    return {**_DEFAULT_ACHIEVEMENTS, **data}


# 功能：原子保存全部成就的解锁时间
def save_achievements(achievements: dict) -> None:
    achievements_file = shared_runtime.get_state_dir() / "achievements.json"
    shared_runtime.write_json_atomic(achievements_file, achievements)


# ── 声音播放 ──────────────────────────────────────────────────────────

# 功能：通过通知脚本非阻塞播放成就或连击声音
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

# 功能：首次解锁指定成就并发送提示与桌面通知
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

# 功能：根据连续成功次数计算当前连击等级
def _combo_level_for(combo: int) -> int:
    """Return the combo level (0-4) for a given combo count."""
    level = 0
    for i, (threshold, _) in enumerate(COMBO_LEVELS):
        if combo >= threshold:
            level = i + 1
    return level


# ── PostToolUse 处理 ──────────────────────────────────────────────────

# 功能：判断一次 Claude 或 Codex 工具调用是否召唤了刀盾狗
def _is_dogdoing_summon(data: dict) -> bool:
    tool_name = str(data.get("tool_name") or data.get("tool") or "").lower()
    tool_input = data.get("tool_input") or data.get("input") or data.get("arguments") or {}
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except (json.JSONDecodeError, ValueError, TypeError):
            tool_input = {}
    if not isinstance(tool_input, dict):
        return False
    if tool_name == "agent":
        return "dogdoing" in str(tool_input.get("subagent_type", "")).lower()
    if "spawn_agent" in tool_name:
        identity = " ".join(
            str(tool_input.get(key, ""))
            for key in ("task_name", "name", "message", "prompt")
        )
        return "dogdoing" in identity.lower() or "刀盾狗" in identity
    return False


# 功能：记录一次成功工具调用并计算连击、召唤次数和相关成就
def record_tool_success(data: dict) -> None:
    if not _is_enabled():
        return

    state = load_state()
    achievements = load_achievements()

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
    if _is_dogdoing_summon(data):
        state["summon_count"] = state.get("summon_count", 0) + 1
        _unlock(achievements, "first_summon")

    # Check ten_tasks
    if state["total_tasks"] >= 10:
        _unlock(achievements, "ten_tasks")

    # Check combo_5
    if state["combo"] >= 5:
        _unlock(achievements, "combo_5")

    # Check drog_triggered
    if state.get("drog_triggered"):
        _unlock(achievements, "drog_awakened")
        state["drog_triggered"] = False

    save_state(state)
    save_achievements(achievements)


# 功能：兼容旧 PostToolUse CLI，从标准输入读取成功事件
def post_tool_use():
    record_tool_success(shared_runtime.read_hook_payload())

# ── PostToolUseFailure 处理 ────────────────────────────────────────────

# 功能：记录一次失败工具调用并重置连击、累计错误和解锁错误成就
def record_tool_failure(data: dict) -> None:
    if not _is_enabled():
        return

    state = load_state()
    achievements = load_achievements()

    # Reset combo
    state["combo"] = 0
    state["combo_level"] = 0

    # Error streak
    state["error_streak"] = state.get("error_streak", 0) + 1
    _play_sound("error")

    # bug_found achievement
    _unlock(achievements, "bug_found")

    # This is Fine mode
    if state["error_streak"] >= 3:
        print(
            "\n🐕 刀盾狗：一切正常。旺。\n",
            file=sys.stderr,
        )

    save_state(state)
    save_achievements(achievements)


# 功能：兼容旧 PostToolUseFailure CLI，从标准输入读取失败事件
def post_tool_failure():
    record_tool_failure(shared_runtime.read_hook_payload())


# ── CLI ───────────────────────────────────────────────────────────────

# 功能：解析追踪脚本的兼容 CLI 子命令并处理标准输入事件
def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "post_tool_use":
        post_tool_use()
    elif cmd == "post_tool_failure":
        post_tool_failure()
    else:
        print(f"用法：{sys.argv[0]} post_tool_use|post_tool_failure", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    shared_runtime.configure_utf8_streams()
    main()
