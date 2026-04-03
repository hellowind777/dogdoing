# 🐕 Dogdoing — 我的刀盾

> 源自"我的刀盾"梗，一只永远不会缺席的工作犬。

Dogdoing 是一个 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 插件。安装后，刀盾狗会在你的每一个任务中"插上一爪"，帮你分活干。实在帮不上忙，就在一旁喝彩加油——因为好刀盾，永不离岗。

## 特性

- 🔧 **真干活** — 不是吉祥物，是工作犬。会读文件、写代码、跑命令、搜网页、review 代码
- 🐾 **插上一爪** — 自动拆分任务，作为子代理并行帮忙
- 👥 **Agent Team 支持** — 编排子代理团队时，刀盾狗必定在列
- 📣 **喝彩模式** — 实在没活干，就当啦啦队长，总结成果 + 旺旺旺
- 🔔 **任务通知** — 主代理完成时桌面通知 + 语音提醒，支持 Windows/macOS/Linux
- 🏆 **成就系统** — 5 个可解锁成就，追踪你的刀盾狗之旅
- 🔥 **连击系统** — 连续成功操作触发 combo，旺声越来越响
- 🐸 **Drog 彩蛋** — 输入 `~drog` 召唤蛙盾，混沌但有用的 Cheems 蛙分身
- 🐕 **This is Fine** — 连续 3 次错误时，刀盾狗淡定安慰："一切正常。旺。"
- 🔍 **/dogfood 自检** — 让刀盾狗 review 自己的代码，dogfooding！
- 🌏 **中英双语** — 中文环境全中文输出，其他环境英文输出
- 🎯 **旺旺旺 / Wow-wow-wow** — 中文用"旺"代替"汪"，谐音更旺；英文用"Wow"代替"Woof"，从"bow-wow"来，表示惊叹！

## 安装

### 方式一：从 Marketplace 安装

先添加 marketplace（只需一次）：

```bash
claude plugin marketplace add hellowind777/dogdoing
```

然后安装插件：

```bash
claude plugin install dogdoing
```

如果你是在 Claude Code 会话内执行，也可以使用等价的 slash command：

```bash
/plugin marketplace add hellowind777/dogdoing
/plugin install dogdoing
```

如果你的环境里存在同名插件，可显式指定 marketplace：

```bash
claude plugin install dogdoing@dogdoing
```
安装后，需要重启claude code生效。

### 方式二：本地加载（开发/测试用）

```bash
claude --plugin-dir /path/to/dogdoing
```

## 插件结构

```
dogdoing/
├── .claude-plugin/
│   └── plugin.json        # 插件清单
├── assets/
│   └── sounds/
│       ├── complete.wav   # "我的刀盾"
│       ├── error.wav      # "呜"
│       ├── combo.wav      # "旺旺旺"
│       └── drog.wav       # "呱"
├── hooks/
│   └── hooks.json         # SessionStart + UserPromptSubmit + PostToolUse + PostToolUseFailure + Stop
├── agents/
│   └── dogdoing.md        # 子代理定义
├── scripts/
│   ├── notify.py          # 通知脚本（桌面+语音+路由）
│   └── tracker.py         # 游戏引擎（成就+连击+错误追踪）
├── skills/
│   ├── dogdoing/
│   │   └── SKILL.md       # /dogdoing 手动召唤技能
│   └── dogfood/
│       └── SKILL.md       # /dogfood 自我审查技能
├── INJECT.md              # 核心指令
├── INJECT_DROG.md         # Drog 蛙盾彩蛋指令
├── settings.json          # 配置
├── package.json           # npm 分发
└── .gitignore
```

## 工作原理

1. **SessionStart hook** — 会话启动时注入 `INJECT.md` + `INJECT_DROG.md` 核心指令
2. **UserPromptSubmit hook** — 每次用户发消息时轻量提醒 + 检测 `~drog` 触发
3. **PostToolUse hook** — 工具成功后更新连击计数、检查成就
4. **PostToolUseFailure hook** — 工具失败后重置连击、累计错误、触发 "This is Fine"
5. **agents/dogdoing.md** — 子代理定义，支持 `Agent(subagent_type="dogdoing:dogdoing")` 调用
6. **skills/dogdoing/SKILL.md** — 支持 `/dogdoing` 手动召唤
7. **skills/dogfood/SKILL.md** — 支持 `/dogfood` 自我审查
8. **Stop hook** — 主代理完成时触发桌面通知 + 语音提醒

## 配置

编辑插件根目录的 `settings.json`：
```
cd ~/.claude/plugins/marketplaces/dogdoing
vim settings.json
```
其中的配置如下：

```json
{
  "notify_level": 3,
  "subagent_enabled": true,
  "cheer_enabled": true,
  "tracker_enabled": true,
  "drog_enabled": true
}
```

### notify_level — 通知级别

| 级别 | 效果 |
|------|------|
| `0` | 无通知 |
| `1` | 仅桌面通知 |
| `2` | 仅语音通知 |
| `3` | 桌面 + 语音（默认） |

### subagent_enabled — 子代理编排开关

| 值 | 效果 |
|------|------|
| `true` | 刀盾狗自动参与每个任务（默认） |
| `false` | 关闭自动编排，Claude 不会自动拉刀盾狗干活 |

### cheer_enabled — 喝彩/叫唤开关

| 值 | 效果 |
|------|------|
| `true` | 没活干时喝彩或叫唤（默认） |
| `false` | 关闭喝彩，安安静静 |

### tracker_enabled — 成就/连击追踪开关

| 值 | 效果 |
|------|------|
| `true` | 启用成就系统、连击系统、错误追踪（默认） |
| `false` | 关闭追踪，安静模式 |

### drog_enabled — Drog 蛙盾彩蛋开关

| 值 | 效果 |
|------|------|
| `true` | 启用 `~drog` 彩蛋 + 深夜模式（默认） |
| `false` | 关闭 Drog 彩蛋 |

> 所有开关独立控制。关闭后仍可通过 `/dogdoing` 或 `~dogdoing` 手动召唤，通知功能也不受影响。

手动测试：

```bash
# 桌面通知
python scripts/notify.py desktop "测试通知"

# 语音播放
python scripts/notify.py sound complete
```

## 刀盾狗的三种模式

| 模式 | 触发条件 | 输出示例 |
|------|---------|---------|
| 🔧 干活 | 能找到可做的子任务 | `🐕 刀盾狗帮忙：` + 实际贡献 |
| 📣 喝彩 | Agent Team 中无法分配任务 | `🐕 刀盾狗喝彩：干得漂亮！旺、旺、旺旺旺旺……冲冲冲！` |
| 🐕 叫唤 | 穷尽所有方式仍无法帮忙 | `🐕 我的刀盾：旺、旺、旺旺旺旺……` |

## 成就系统

| 成就 | 条件 |
|------|------|
| 🗡️ 初出茅庐 | 首次召唤刀盾狗子代理 |
| 🛡️ 刀盾合璧 | 刀盾狗参与 10 个任务 |
| 🔥 连旺 | 连续 5 次成功（combo streak） |
| 💀 狗头保命 | 首次检测到工具执行错误 |
| 🐸 Drog 觉醒 | 触发 Drog 彩蛋 |

成就数据存储在 `~/.dogdoing/achievements.json`，解锁时弹桌面通知。

## 连击系统

连续成功的工具调用会触发 combo：

| 连击数 | 输出 |
|--------|------|
| 3 | 🐕 旺！ |
| 5 | 🐕 旺旺！ |
| 10 | 🐕 旺旺旺旺！ |
| 20 | 🐕 旺旺旺旺旺旺旺旺！！！冲冲冲！ |

工具执行失败时连击归零。连续 3 次失败触发 "This is Fine" 模式。

## Drog 蛙盾彩蛋

输入 `~drog` 召唤 Drog（蛙盾）——刀盾狗的混沌分身，一只 Cheems 蛙。所有"旺"变"呱"，混乱但有用。凌晨 2-5 点 Drog 偶尔自动出现。

## License

MIT
