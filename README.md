# Dogdoing - 我的刀盾

Dogdoing 是同时兼容 **Codex** 与 **Claude Code** 的工作型插件。它会参与任务的自动分工与验证，并提供桌面通知、语音、成就、连击、错误追踪、Drog 彩蛋和自检 Skill。

V1 的目标是让原项目全部功能在 Codex 中可用，而不删除 Claude Code 支持。

## V1 功能

- **自动分工**：每轮任务为刀盾狗寻找真实子任务，例如测试、审查、检索、边界检查或结果验证。
- **原生多代理**：Codex 使用 `collaboration.spawn_agent`，Claude Code 使用已注册的 `Agent`。
- **喝彩模式**：没有适合并行的工作时，刀盾狗总结成果并喝彩。
- **桌面通知与语音**：任务结束时提醒，支持 Windows、macOS、Linux。
- **成就系统**：包含首次召唤、累计 10 次、5 连击、首次错误、Drog 觉醒五项成就。
- **连击系统**：连续成功 3、5、10、20 次触发四级提示。
- **错误追踪**：失败时连击归零，连续 3 次失败触发 `This is Fine`。
- **Drog 彩蛋**：`~drog` 触发一次蛙盾人格，凌晨 2:00-5:00 启用深夜模式。
- **自检 Skill**：检查两套插件清单、Marketplace、Hook、脚本、Skill 和测试。
- **全中文提示**：所有刀盾狗提示和输出使用简体中文，叫声统一使用“旺”。

## 环境要求

- Codex Desktop 优先使用应用自带的 Python 3；其他宿主需要 Python 3.9 或更高版本。
- Codex 需要支持 Plugin、Plugin Hook 与 Multi-agent 的版本。
- 桌面或终端环境需要允许执行本地 Hook 命令。

插件没有第三方 Python 运行时依赖。

Windows 会依次尝试 `DOGDOING_PYTHON`、Codex 自带 Python、PATH 中的 `python.exe` 或 `python3.exe`，最后尝试 `py.exe -3`。需要固定解释器时，可将 `DOGDOING_PYTHON` 设置为 Python 可执行文件的完整路径。

## Codex 安装

### 从 Git 仓库安装

先添加 Marketplace：

~~~bash
codex plugin marketplace add hellowind777/dogdoing
~~~

再安装插件：

~~~bash
codex plugin add dogdoing@dogdoing
~~~

首次安装或 Hook 命令发生变化后，请在 Codex 的 Hooks 管理页审查并信任 Dogdoing 的 4 个 Hook。`installed, enabled` 只表示插件已启用；Hooks 页显示 `Active 4`、不再显示待审查项，才表示文字注入、追踪和完成声音可以执行。

安装或更新完成后，请完全退出并重新启动 Codex Desktop，再新建任务验证。仅新建任务不会刷新已经启动的 app-server 插件快照；旧快照还可能继续引用更新时已删除的版本缓存。Codex CLI 用户退出当前进程后重新运行即可。

### 本地开发安装

在仓库根目录执行：

~~~bash
codex plugin marketplace add .
codex plugin add dogdoing@dogdoing
~~~

检查安装状态：

~~~bash
codex plugin list
~~~

预期看到 `dogdoing@dogdoing` 的状态为 `installed, enabled`。

本地重复安装时，开发脚本会给 Codex 清单追加一个 `+codex.<缓存标识>` 后缀；标识的具体格式由当前 Codex `plugin-creator` 决定，发布基线版本仍是 `1.1.0`。

## Claude Code 安装

### 从 Git 仓库安装

~~~bash
claude plugin marketplace add hellowind777/dogdoing
claude plugin install dogdoing
~~~

如存在同名插件，可显式指定 Marketplace：

~~~bash
claude plugin install dogdoing@dogdoing
~~~

### 本地开发加载

~~~bash
claude --plugin-dir /path/to/dogdoing/plugins/dogdoing
~~~

## 使用方式

| 功能 | Codex | Claude Code |
|---|---|---|
| 手动召唤 | `$dogdoing [主题]` | `/dogdoing [主题]` |
| 自我审查 | `$dogfood [bug/performance/compat/style]` | `/dogfood [方向]` |
| 文本召唤 | `~dogdoing [主题]` | `~dogdoing [主题]` |
| Drog 彩蛋 | `~drog` | `~drog` |
| 自动参与 | Codex 原生多代理 | Claude Agent 子代理 |

手动召唤会等待刀盾狗完成分析再返回。多代理能力不可用时，主代理执行同等检查，不会让用户任务失败。

## 仓库结构

~~~text
dogdoing/
|-- .agents/plugins/marketplace.json       # Codex Marketplace
|-- .claude-plugin/marketplace.json        # Claude Marketplace
|-- plugins/dogdoing/
|   |-- .codex-plugin/plugin.json          # Codex 插件清单
|   |-- .claude-plugin/plugin.json         # Claude 插件清单与附加 Hook 路径
|   |-- hooks.json                         # 旧版 Codex 兼容 Hook
|   |-- hooks/hooks.json                   # Codex 与 Claude 共享 Hook
|   |-- hooks/claude-failure.json          # Claude 独有失败事件
|   |-- agents/dogdoing.md                 # Claude 注册代理人格
|   |-- skills/
|   |   |-- dogdoing/SKILL.md
|   |   `-- dogfood/SKILL.md
|   |-- scripts/
|   |   |-- runtime.py                     # 共享配置和状态 I/O
|   |   |-- hook_router.py                 # 双平台事件路由
|   |   |-- hook_router_windows.cmd        # Windows Python 入口
|   |   |-- hook_router_windows_error.txt  # Windows 中文启动错误
|   |   |-- notify.py                      # 通知、声音、注入与 Drog
|   |   `-- tracker.py                     # 成就、连击和错误追踪
|   |-- assets/icons/
|   |-- assets/sounds/
|   |-- INJECT.md
|   |-- INJECT_SUBAGENT.md
|   |-- INJECT_SUBAGENT_CODEX.md
|   |-- INJECT_CHEER.md
|   |-- INJECT_DROG.md
|   `-- settings.json
|-- tests/
`-- package.json
~~~

## Hook 映射

| 行为 | Codex | Claude Code |
|---|---|---|
| 会话注入 | `SessionStart` | `SessionStart` |
| 用户提示与 Drog 检测 | `UserPromptSubmit` | `UserPromptSubmit` |
| 成功追踪 | `PostToolUse` | `PostToolUse` |
| 失败追踪 | 从 `PostToolUse` 结果状态与退出码判断 | `PostToolUseFailure` |
| 完成通知 | `Stop` | `Stop` |

Codex 与 Claude Code 都从 `hooks/hooks.json` 加载公共 Hook，并调用 `scripts/hook_router.py`。Claude 插件清单再从 `hooks/claude-failure.json` 追加 `PostToolUseFailure`；该事件不进入 Codex 清单，避免整个插件 Hook 因未知事件加载失败。路由器根据当前会话环境识别宿主，并按宿主输出对应协议；无法解析的载荷会安全回退为空对象，未知事件返回非零退出码，方便定位错误配置。根目录 `hooks.json` 仅保留给仍使用旧发现路径的 Codex 版本。

Hook 在 Windows 使用 `command_windows` 调用统一入口，由入口寻找可用的 Python 3 并执行同一个 `hook_router.py`；在 macOS/Linux 使用 `command` 调用 `python3`。Windows 入口会保留 Hook 标准输入、事件参数和退出码，找不到解释器时输出简体中文错误。

## 配置

编辑插件目录中的 `plugins/dogdoing/settings.json`：

~~~json
{
  "notify_level": 3,
  "subagent_enabled": true,
  "cheer_enabled": true,
  "tracker_enabled": true,
  "drog_enabled": true
}
~~~

| 配置 | 默认值 | 作用 |
|---|---:|---|
| `notify_level` | `3` | `0` 关闭，`1` 仅桌面，`2` 仅语音，`3` 桌面加语音 |
| `subagent_enabled` | `true` | 自动分配刀盾狗子任务 |
| `cheer_enabled` | `true` | 无并行任务时启用喝彩 |
| `tracker_enabled` | `true` | 启用成就、连击和错误追踪 |
| `drog_enabled` | `true` | 启用 `~drog` 和深夜模式 |

所有开关独立生效。关闭自动分工后，仍可通过 `$dogdoing`、`/dogdoing` 或 `~dogdoing` 手动调用。

## 成就与连击

成就状态保存在 `~/.dogdoing/achievements.json`，运行状态保存在 `~/.dogdoing/state.json`。

| 成就 | 条件 |
|---|---|
| 初出茅庐 | 首次召唤刀盾狗子代理 |
| 刀盾合璧 | 累计 10 次成功工具事件 |
| 连旺 | 连续 5 次成功 |
| 狗头保命 | 首次工具失败 |
| Drog 觉醒 | 触发 `~drog` 后产生下一次成功事件 |

| 连击数 | 提示 |
|---:|---|
| 3 | 旺 |
| 5 | 旺旺 |
| 10 | 旺旺旺旺 |
| 20 | 旺旺旺旺旺旺旺旺，冲冲冲 |

## 跨平台通知

- Windows：Windows Runtime Toast 与 `winsound`。
- macOS：`osascript` 与 `afplay`。
- Linux：`notify-send`，声音依次尝试 `aplay`、`paplay`。
- 系统通知工具不可用时降级为终端响铃，不阻断 Codex 或 Claude Code。

手动检查通知：

~~~bash
python plugins/dogdoing/scripts/notify.py desktop "测试通知"
python plugins/dogdoing/scripts/notify.py sound complete
~~~

## 测试与校验

运行全部自动化测试：

~~~bash
python -m unittest discover -s tests -v
~~~

校验 Codex 插件清单：

~~~bash
python /path/to/plugin-creator/scripts/validate_plugin.py plugins/dogdoing
~~~

实际发布前还应执行本地 Marketplace 安装，并通过 `codex plugin list` 确认版本与启用状态。

## License

MIT
