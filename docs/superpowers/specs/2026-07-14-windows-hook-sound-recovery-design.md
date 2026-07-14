# 刀盾狗 Windows Hook 声音恢复设计

## 目标

恢复 Codex Desktop 中刀盾狗的完成声音，并让 Windows 安装不再只依赖 PATH 中的裸 `python` 命令。保留现有提示文字、通知等级和 `complete.wav` 原始音频。

## 已确认根因

1. Codex 重启后重新生成了用户配置，Dogdoing Marketplace、插件启用项和 Hook 信任记录不再存在，旧缓存仍在但不会自动激活。
2. 两份 Hook 配置的 Windows 命令都直接调用 `python`。当前系统没有该命令，真实 Hook 命令以退出码 1 失败，`hook_router.py` 和声音播放逻辑没有机会执行。

## 方案

新增一个仅负责选择 Python 解释器的 Windows 批处理入口。选择顺序如下：

1. 显式配置的 `DOGDOING_PYTHON`，便于诊断和企业环境固定运行时。
2. Codex Desktop 自带的 primary runtime Python。
3. PATH 中可用的 `python.exe` 或 `python3.exe`。
4. 已注册 Python 3 的 Windows `py.exe -3`。

入口找到解释器后，将标准输入、Hook 事件名、宿主参数和退出码原样交给现有 `hook_router.py`。找不到解释器时，向标准错误输出简体中文原因并返回非零退出码。批处理入口不承载通知、声音、注入或追踪业务逻辑，避免 Windows 和其他平台产生两份实现。

Codex 根级 `hooks.json` 与共享 `hooks/hooks.json` 的 `command_windows` 都改为调用该入口；非 Windows 命令保持不变。

## 数据流

Codex Hook 载荷通过标准输入进入 Windows 入口，入口选择解释器后启动 `hook_router.py`。路由器继续解析事件：`SessionStart` 和 `UserPromptSubmit` 返回中文上下文，`PostToolUse` 更新追踪状态，`Stop` 根据 `notify_level` 发送桌面通知并同步播放原始 `complete.wav`。

## 测试

先添加会在当前代码上失败的测试，覆盖以下行为：

- 两份 Hook 配置不再使用裸 `python`，而是引用 Windows 入口。
- 指定 `DOGDOING_PYTHON` 后，入口能接收真实 JSON 标准输入并成功执行路由器。
- 没有可用解释器时返回非零退出码，并输出可定位的中文错误。

实现后运行相关单元测试、完整测试集和 Codex 插件校验器。然后使用插件缓存版本更新脚本生成新版本，重新添加本地 Marketplace、安装插件，并通过 `codex plugin list` 确认启用状态。

## 验收标准

- `dogdoing@dogdoing` 显示为 `installed, enabled`。
- Codex Hooks 管理页能发现 4 个 Hook；命令变化后由用户完成信任确认。
- Windows 在没有 PATH `python` 的当前环境中仍能执行真实 Stop Hook。
- Stop Hook 返回 0，并播放未经修改的原始完成语音。
