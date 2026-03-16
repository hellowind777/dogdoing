---
name: dogdoing
description: "Manually summon Dogdoing (刀盾狗) to help with any task. Use /dogdoing or /dogdoing:dogdoing to invoke."
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch
---

# /dogdoing — 手动召唤刀盾狗

Launch the dogdoing subagent to help with the current task.

Use `Agent(subagent_type="dogdoing:dogdoing", ...)` to spawn it. If that fails, try `subagent_type="dogdoing"`.

- If `$ARGUMENTS` is provided, pass it as the task.
- If no arguments, analyze the recent conversation and find useful work: code review, tests, search, validation, or anything helpful.

Language rule: Chinese context → Chinese output. Otherwise → English.
