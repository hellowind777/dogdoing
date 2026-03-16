---
name: dogdoing
description: "Dogdoing (刀盾狗/我的刀盾) - Manually invoke the shield-dog to help with any task. It splits work, runs tests, reviews code, searches info, validates results. Use /dogdoing to summon it explicitly."
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch
---

# /dogdoing — 手动召唤刀盾狗

When the user explicitly invokes `/dogdoing`, launch the dogdoing subagent to help with the current task:

```
Agent(subagent_type="dogdoing", description="刀盾狗出击", prompt="<analyze current context and find useful work to do>")
```

If arguments are provided via `$ARGUMENTS`, pass them as the task description to the dogdoing agent.

If no arguments are provided, Dogdoing should analyze the recent conversation context and find something useful to contribute — a code review, a test, a search, a validation, or anything helpful.
