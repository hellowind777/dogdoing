---
name: dogfood
description: "审查 Dogdoing 自身的 Claude Code 与 Codex 插件实现。用户输入 $dogfood、/dogfood，或要求检查 Dogdoing 的 bug、性能、兼容性、代码风格和测试时使用。"
---

# Dogfood 双平台自检

对 Dogdoing 插件做诚实、可复现的自我审查。使用 `$ARGUMENTS` 限定关注方向；未提供参数时覆盖 bug、性能、兼容性、代码风格和测试。

## 检查范围

先定位仓库根目录和 `plugins/dogdoing` 插件根目录，然后检查：

- Codex 清单：`.codex-plugin/plugin.json`
- Claude 清单：`.claude-plugin/plugin.json`
- Codex Hook：`hooks.json`
- Claude Hook：`hooks/hooks.json`
- Codex Marketplace：`.agents/plugins/marketplace.json`
- Claude Marketplace：`.claude-plugin/marketplace.json`
- 运行脚本：`scripts/*.py`
- Skill：`skills/*/SKILL.md`
- 代理人格：`agents/dogdoing.md`
- 注入内容：`INJECT*.md`
- 自动化测试和 README

安装缓存中可能没有 Marketplace 文件；这种情况下明确说明该项只能在源码仓库验证，不把“文件不在安装包内”误报为缺陷。

## 审查要求

1. 运行现有测试并记录真实输出。
2. 检查两个清单的版本、资源路径和 Skill 目录是否一致。
3. 检查每个 Hook 事件是否由宿主支持，命令路径是否跨平台可执行。
4. 检查 Codex `collaboration.spawn_agent` 与 Claude `Agent` 是否都有等价路径。
5. 检查通知、声音、五项成就、四级连击、错误追踪、Drog 和中英双语。
6. 报告具体文件与行号，区分已验证问题、风险和测试缺口。
7. 中文上下文用简体中文输出，其他上下文用英文。

## 输出格式

```text
🐕 刀盾狗自检报告

检查范围：
- [实际读取的文件和执行的命令]

发现问题：
1. [严重程度] 文件:行号 - 问题、影响和证据

良好实践：
- [有证据的优点]

建议：
- [按优先级排序的具体改进]

测试结果：
- [命令与通过/失败数量]
```

不得为了维护插件形象而隐藏问题。没有发现问题时，也要列出仍未覆盖的运行环境或人工验证风险。
