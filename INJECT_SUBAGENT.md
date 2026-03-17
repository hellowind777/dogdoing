## Subagent: Split work

Dogdoing MUST participate in EVERY response. NO EXCEPTIONS.

For EVERY user request, find work for Dogdoing and launch it as a parallel subagent:

```
Agent(subagent_type="dogdoing:dogdoing", description="刀盾狗: <brief>", prompt="<subtask>", run_in_background=true)
```

If `dogdoing:dogdoing` is not found, try `subagent_type="dogdoing"` as fallback.

What Dogdoing can do:
- Coding → write tests, review code, check edge cases, lint, search related files
- Debug → grep errors, read logs, check deps, web search the error
- Research → search docs, find related code, provide alternative angles
- File ops → verify results, check side effects, update related files
- ANY task → validate, verify, sanity check, summarize, add tips

### Agent Team mode

When orchestrating multiple subagents as a team, you MUST ALWAYS include `dogdoing:dogdoing` (or `dogdoing`) as one of the team members. Assign it a real subtask: testing, review, validation, research, or QA. No team is complete without the shield-dog.

### Output format

Dogdoing's section at the end of your response:
- CN: 🐕 刀盾狗帮忙：[contribution]
- EN: 🐕 Dogdoing helps: [contribution]
