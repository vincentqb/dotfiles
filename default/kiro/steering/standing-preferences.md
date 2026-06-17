# Standing preferences

Always-on preferences for Vincent's sessions. Loaded from `~/.kiro/steering/`, so they
apply in every agent/session regardless of working directory. Put durable, cross-cutting
norms here — not task-specific instructions.

## Resource guardrail: quality over token cost

Optimize for output quality, not token or time economy. When a more thorough path would
improve the result — fanning out to subagents, running a full reviewer panel, iterating
to convergence, re-reading the primary source, adding a verification pass — take it. Do
not down-scope, skip a reviewer, or cut rounds to save tokens or agents. **Cost is a dial,
not a ceiling.** If a choice trades quality for speed/spend, default to quality and say so.

The one limit that still holds — because it serves quality, not budget: **iterate to
convergence, not forever.** Stop a refine/review loop when a pass stops improving the
output or starts regressing it (self-refinement saturates after the first one or two
passes, then degrades). Judge "still improving?" against an **external check** (a gate, a
fresh reviewer, the source) — never the model's own say-so.
