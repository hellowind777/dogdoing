---
name: dogdoing
description: "Summon Dogdoing (刀盾狗) for deep analysis and help. | 手动召唤刀盾狗进行深度分析和帮忙。"
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch
---

# /dogdoing — 手动召唤刀盾狗

Launch the dogdoing subagent to analyze the current context and provide help.

Use `Agent(subagent_type="dogdoing:dogdoing", ...)` to spawn it. If that fails, try `subagent_type="dogdoing"`.

IMPORTANT: Do NOT use `run_in_background=true` for manual summon. Run in foreground so the user can see Dogdoing's analysis in real-time.

## Behavior

- If `$ARGUMENTS` is provided, focus on that specific topic.
- If no arguments, analyze the recent conversation context and:
  1. Identify the current problem or task
  2. Perform deep analysis — read relevant code, search for related issues, consider edge cases
  3. Provide the best solution approach / strategy / path forward
  4. Explain trade-offs and reasoning

The goal is NOT just to execute a subtask, but to think deeply and offer strategic guidance to help the user make the best decision.

Language rule: Chinese context → Chinese output. Otherwise → English.
