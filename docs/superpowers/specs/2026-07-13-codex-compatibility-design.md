# Dogdoing Codex 全功能兼容设计

## 目标

在不破坏现有 Claude Code 插件能力的前提下，将 Dogdoing 改造成可被 Codex 原生安装和加载的双平台插件。Codex 版本必须覆盖自动分工、手动召唤、喝彩、通知、声音、成就、连击、错误追踪、Drog 彩蛋、自检、中英双语和跨平台运行等现有功能。

## 兼容范围

| 功能 | Claude Code | Codex |
|---|---|---|
| Marketplace 安装 | 保留 `.claude-plugin/marketplace.json` | 新增 `.agents/plugins/marketplace.json` |
| 插件清单 | 保留 `.claude-plugin/plugin.json` | 新增 `.codex-plugin/plugin.json` |
| 会话指令注入 | `SessionStart` Hook | `SessionStart` Hook |
| 每轮提醒与 Drog 检测 | `UserPromptSubmit` Hook | `UserPromptSubmit` Hook |
| 成功调用追踪 | `PostToolUse` Hook | `PostToolUse` Hook |
| 失败调用追踪 | `PostToolUseFailure` Hook | 从 Codex `PostToolUse` 结果归一化，必要时由可用失败事件补充 |
| 结束通知 | `Stop` Hook | `Stop` Hook |
| 自动子代理 | Claude `Agent` | Codex `collaboration.spawn_agent` |
| 手动技能 | `/dogdoing`、`/dogfood` | `$dogdoing`、`$dogfood` |
| 文本触发 | `~dogdoing`、`~drog` | `~dogdoing`、`~drog` |

## 架构

项目采用“Marketplace 在仓库根目录、插件实现在 `plugins/dogdoing`、运行逻辑共享”的标准仓库结构。Claude Code 与 Codex 分别使用各自原生清单和 Hook 配置，Python 脚本负责解析两种平台的输入并转换成统一事件。通知、声音、状态文件、成就规则和注入内容只有一份实现，避免双平台行为逐渐分叉。

### 插件元数据

- 仓库根目录 `.claude-plugin/marketplace.json` 继续提供 Claude Code Marketplace，入口改为标准的 `./plugins/dogdoing`。
- 仓库根目录 `.agents/plugins/marketplace.json` 提供 Codex 本地目录、Git 仓库和 Marketplace 安装入口，同样指向 `./plugins/dogdoing`。
- `plugins/dogdoing/.claude-plugin/plugin.json` 保留 Claude Code 插件清单。
- `plugins/dogdoing/.codex-plugin/plugin.json` 声明 Codex 插件名称、版本、技能和界面元数据；Codex 不接受在此清单中声明 `hooks`。
- `plugins/dogdoing/hooks.json` 由 Codex 自动发现，`plugins/dogdoing/hooks/hooks.json` 继续服务 Claude Code。
- `package.json` 同时打包两种清单、测试和共享资源，并更新产品描述与关键词。

### Hook 适配

新增统一 Hook 路由入口，接收事件名和标准输入 JSON。路由器完成以下工作：

1. 判断输入来自 Claude Code 还是 Codex。
2. 兼容两端的字段命名，提取用户输入、工具名称、工具参数、执行结果、失败原因和停止原因。
3. 将事件转换为 `session_start`、`prompt_submit`、`tool_success`、`tool_failure` 或 `turn_stop`。
4. 调用现有通知与追踪逻辑。

Codex 没有独立失败事件时，路由器从 `PostToolUse` 的结果状态判断成功或失败。无法识别结果时采用成功路径，避免把正常调用误计为错误；测试会固定当前 Codex 版本的实际载荷样本。

### 自动分工与手动召唤

会话注入内容改为平台中立的行为说明，并分别列出可用调用方式：

- Claude Code 使用 `Agent(subagent_type="dogdoing:dogdoing", ...)`。
- Codex 使用 `collaboration.spawn_agent(task_name="dogdoing", ...)`，在任务消息中携带完整刀盾狗人格与输出规则。
- 如果当前环境不提供多代理工具，主代理仍需完成任务，并在结尾输出刀盾狗贡献或喝彩，不因插件能力缺失阻断用户请求。

`dogdoing` Skill 根据当前可用工具选择调用方式。`dogfood` Skill 保持自检行为，但更新检查范围，使其同时检查 Claude 与 Codex 清单、Hook 和技能。

### 配置与状态

`settings.json` 继续作为用户可编辑配置。配置查找顺序为：

1. `CODEX_PLUGIN_ROOT`
2. `CLAUDE_PLUGIN_ROOT`
3. `CLAUDE_PLUGIN_DIR`
4. 脚本所在插件根目录

状态仍存储在 `~/.dogdoing/`，从而让同一用户在两种平台间共享成就和连击记录。写入采用临时文件替换，降低多个 Hook 并发写入时损坏 JSON 的风险。

### 通知与声音

桌面通知和声音继续支持 Windows、macOS、Linux。Hook 命令统一使用当前 Python 解释器发现策略，不硬编码仅在部分系统存在的 `python3`。通知失败只降级为终端响铃，不影响 Codex 或 Claude 的主任务。

## 错误处理

- Hook 标准输入为空、不是 JSON 或字段缺失时使用空载荷，不抛出异常到宿主进程。
- 配置文件损坏时回退默认值。
- 状态文件损坏时保留可恢复字段并回退默认状态。
- 桌面通知和声音播放器不存在时静默降级。
- 未知 Hook 事件返回非零退出码，便于开发阶段发现配置错误。
- 插件清单和 Marketplace 在发布前通过结构测试及 Codex CLI 实际加载验证。

## 测试策略

测试使用 Python 标准库 `unittest`，不增加运行时依赖：

- 清单测试：解析 Claude/Codex 插件清单、Marketplace 和 Hook JSON，验证路径与版本一致。
- Hook 路由测试：覆盖 Claude 与 Codex 的会话、提示、成功工具、失败工具和停止载荷。
- 注入测试：覆盖所有配置开关、深夜模式、`~drog` 和双平台代理指令。
- 追踪测试：覆盖连击阈值、失败重置、五项成就、状态损坏和关闭追踪。
- 通知测试：覆盖通知级别、停止原因和无播放器降级。
- 风格检查：确认所有 Python 函数和类上方都有中文功能注释。
- 集成验证：将当前目录作为本地 Codex Marketplace 添加，安装 Dogdoing，运行 `codex plugin list` 和真实 Hook 命令，再清理测试安装状态。

## 验收标准

1. Claude Code 原有清单与 Hook 仍可解析。
2. Codex 能从本地 Marketplace 发现、安装并启用 Dogdoing。
3. Codex 能发现 `$dogdoing` 与 `$dogfood` 两个 Skill。
4. Codex 会话启动、用户输入、工具成功、工具失败和任务结束均触发正确行为。
5. 自动分工在 Codex 使用原生多代理工具，无法分工时正确进入喝彩模式。
6. 五项成就、四级连击、连续三次错误提示和 Drog 彩蛋均有自动化证据。
7. Windows、macOS、Linux 通知命令均有可测试的选择逻辑。
8. README 同时提供 Claude Code 与 Codex 的安装、配置、使用和测试说明。
9. 全部自动化测试通过，Codex CLI 本地安装和插件列表验证通过。

## 非目标

- 不引入后台常驻服务。
- 不修改用户全局 `AGENTS.md`。
- 不要求用户手工编辑全局 `config.toml` 才能安装插件。
- 不删除 Claude Code 支持。
