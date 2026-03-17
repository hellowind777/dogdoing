# 🐕 Dogdoing — 我的刀盾

> 源自"我的刀盾"梗，一只永远不会缺席的工作犬。

Dogdoing 是一个 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 插件。安装后，刀盾狗会在你的每一个任务中"插上一爪"，帮你分活干。实在帮不上忙，就在一旁喝彩加油——因为好刀盾，永不离岗。

## 特性

- 🔧 **真干活** — 不是吉祥物，是工作犬。会读文件、写代码、跑命令、搜网页、review 代码
- 🐾 **插上一爪** — 自动拆分任务，作为子代理并行帮忙
- 👥 **Agent Team 支持** — 编排子代理团队时，刀盾狗必定在列
- 📣 **喝彩模式** — 实在没活干，就当啦啦队长，总结成果 + 旺旺旺
- 🔔 **任务通知** — 主代理完成时桌面通知 + 语音提醒，支持 Windows/macOS/Linux
- 🌏 **中英双语** — 中文环境全中文输出，其他环境英文输出
- 🎯 **旺旺旺 / Wow-wow-wow** — 中文用"旺"代替"汪"，谐音更旺；英文用"Wow"代替"Woof"，从"bow-wow"来，表示惊叹！

## 安装

### 方式一：从 Marketplace 安装

先添加 marketplace（只需一次）：

```bash
/plugin marketplace add hellowind777/dogdoing
```

然后安装插件：

```bash
/plugin install dogdoing
```

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
│       └── complete.wav   # 预生成语音
├── hooks/
│   └── hooks.json         # SessionStart + UserPromptSubmit + Stop hook
├── agents/
│   └── dogdoing.md        # 子代理定义，可被 Agent 工具编排
├── scripts/
│   ├── notify.py          # 通知脚本（桌面+语音+路由）
│   └── generate_sounds.py # 语音生成工具（开发用）
├── skills/
│   └── dogdoing/
│       └── SKILL.md       # /dogdoing 手动召唤技能
├── INJECT.md              # 核心指令，由 hook 注入每次会话
├── settings.json          # 通知级别配置
├── package.json           # npm 分发
└── .gitignore
```

## 工作原理

1. **SessionStart hook** — 会话启动时注入 `INJECT.md` 核心指令，确保刀盾狗始终在线
2. **UserPromptSubmit hook** — 每次用户发消息时轻量提醒，防止长对话中 Claude 遗忘
3. **agents/dogdoing.md** — 子代理定义，支持 `Agent(subagent_type="dogdoing:dogdoing")` 调用
4. **skills/dogdoing/SKILL.md** — 支持 `/dogdoing` 手动召唤
5. **Stop hook** — 主代理完成时触发桌面通知 + 语音提醒（子代理不触发）

## 配置

编辑插件根目录的 `settings.json`：

```json
{
  "notify_level": 3,
  "subagent_enabled": true,
  "cheer_enabled": true
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

> 两个开关独立控制。关闭后仍可通过 `/dogdoing` 或 `~dogdoing` 手动召唤，通知功能也不受影响。

手动测试：

```bash
# 桌面通知
python scripts/notify.py desktop "测试通知"

# 语音播放
python scripts/notify.py sound complete
```

### 生成/更新语音文件

语音文件已预生成随插件分发，无需额外操作。如需重新生成：

```bash
pip install edge-tts miniaudio
python scripts/generate_sounds.py
```

## 刀盾狗的三种模式

| 模式 | 触发条件 | 输出示例 |
|------|---------|---------|
| 🔧 干活 | 能找到可做的子任务 | `🐕 刀盾狗帮忙：` + 实际贡献 |
| 📣 喝彩 | Agent Team 中无法分配任务 | `🐕 刀盾狗喝彩：干得漂亮！旺、旺、旺旺旺旺……冲冲冲！` |
| 🐕 叫唤 | 穷尽所有方式仍无法帮忙 | `🐕 我的刀盾：旺、旺、旺旺旺旺……` |

## License

MIT
