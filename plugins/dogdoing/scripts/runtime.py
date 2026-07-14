#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dogdoing 在 Claude Code 与 Codex 间共享的轻量运行时。"""

import copy
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping, Optional, TextIO


_ENV_PLUGIN_ROOTS = (
    "CODEX_PLUGIN_ROOT",
    "PLUGIN_ROOT",
    "CLAUDE_PLUGIN_ROOT",
    "CLAUDE_PLUGIN_DIR",
)


# 功能：按宿主优先级定位当前 Dogdoing 插件根目录
def find_plugin_root() -> Path:
    for variable_name in _ENV_PLUGIN_ROOTS:
        value = os.environ.get(variable_name)
        if value:
            return Path(value).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


# 功能：读取 JSON 对象，文件缺失或损坏时返回默认值的独立副本
def read_json(path: Path, default: Mapping[str, Any]) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError):
        pass
    return copy.deepcopy(dict(default))


# 功能：通过同目录临时文件原子替换目标 JSON，避免留下不完整状态
def write_json_atomic(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    try:
        temporary.write_text(
            json.dumps(dict(data), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


# 功能：从当前插件的 settings.json 读取一个配置项并保留 false 等有效值
def read_setting(key: str, default: Any = None, plugin_root: Optional[Path] = None) -> Any:
    root = plugin_root.resolve() if plugin_root else find_plugin_root()
    settings = read_json(root / "settings.json", {})
    return settings[key] if key in settings else default


# 功能：从 Hook 标准输入读取 JSON 对象，无法使用的输入安全回退为空对象
def read_hook_payload(stream: Optional[TextIO] = None) -> dict:
    source = stream if stream is not None else sys.stdin
    try:
        raw = source.read()
        if not raw.strip():
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError):
        return {}


# 功能：返回用户状态目录，并允许测试或高级配置通过环境变量覆盖
def get_state_dir() -> Path:
    custom = os.environ.get("DOGDOING_STATE_DIR")
    if custom:
        return Path(custom).expanduser().resolve()
    return Path.home() / ".dogdoing"


# 功能：在 Windows CLI 入口原地调整标准流编码且不替换底层缓冲区
def configure_utf8_streams() -> None:
    if sys.platform != "win32":
        return
    for stream_name in ("stdin", "stdout", "stderr"):
        stream = getattr(sys, stream_name)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass
