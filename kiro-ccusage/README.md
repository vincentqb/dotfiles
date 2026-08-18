# kiro-ccusage

Report Kiro CLI consumption through [ccusage](https://github.com/ryoppippi/ccusage).

Kiro meters in **credits**, not tokens, and exposes no token counts locally, so
credits are what gets recorded and dollars are derived from them.
[FINDINGS.md](FINDINGS.md) documents why, and [calibrate.py](calibrate.py)
re-derives every constant from your own data.

## Usage

Run it with no arguments, like `ccusage`:

```fish
kiro-ccusage
```

```
╭──────────────────────────────────────────────────────────╮
│                                                          │
│   Kiro CLI Credit Usage & Cost Estimate Report - Daily   │
│                                                          │
╰──────────────────────────────────────────────────────────╯

┌────────────┬──────────────────┬─────────┬──────────┬─────────────────┐
│ Date       │ Models           │   Share │  Credits │ Est. Cost (USD) │
├────────────┼──────────────────┼─────────┼──────────┼─────────────────┤
│ 2026-08-06 │ - claude-fable-5 │  800.00 │ 1,000.00 │   $75 [65, 140] │
│            │ - claude-opus-5  │  150.00 │          │                 │
│            │ - gpt-5.6-sol    │   50.00 │          │                 │
├────────────┼──────────────────┼─────────┼──────────┼─────────────────┤
│ 2026-08-07 │ - claude-fable-5 │  500.00 │   500.00 │    $37 [32, 70] │
├────────────┼──────────────────┼─────────┼──────────┼─────────────────┤
│ Total      │                  │         │ 1,500.00 │  $112 [97, 211] │
└────────────┴──────────────────┴─────────┴──────────┴─────────────────┘
```

(Figures above are illustrative, not real usage.)

**Credits** are what Kiro records, already scaled by each model's rate
multiplier, so they are comparable and summable across models and match
`/usage`'s plan counter. **Est. Cost** is derived from them and moves with
`--credit-rate`; the credit figures never do.

```fish
kiro-ccusage --credits            # raw credits instead of dollars
kiro-ccusage --credit-rate=0.056  # output-heavy end of the estimate
kiro-ccusage --quiet              # refresh only, no table
kiro-ccusage --ccusage            # ccusage's own table instead
kiro-ccusage --out DIR            # export somewhere else
```

The table follows ccusage's style but carries the columns Kiro actually has.
`--ccusage` runs ccusage itself, which is the same data with five
structurally-zero token columns and a "Token Usage Report" title. Both read the
same export, so any other ccusage command works too:

```fish
CLAUDE_CONFIG_DIR=~/.local/share/kiro-ccusage ccusage claude monthly
```

The export refreshes automatically when a `kiro-cli chat` exits, via the
`kiro-cli` wrapper in `default/config/fish/functions/kiro-cli.fish`.

## All harnesses at once (`ccusage-all`)

`ccusage-all` puts Kiro, l3m, Claude Code, Codex (and anything else ccusage
detects) in one daily table: `Date | Day Total | Harness | Model | Consumed | Unit | Rate | Cost (USD)`,
where **Cost = Consumed × Rate** on every row and `Day Total` is that date's total
across all harnesses (shown once per day). It reuses
`ccusage daily --json --by-agent` for the token-metered harnesses, this tool for
Kiro's credits, and l3m's own hub for l3m, then re-prices.

```fish
ccusage-all                     # default: l3m rates, Kiro estimated
ccusage-all --rates litellm     # price everything the way ccusage does
ccusage-all --since 2026-08-01 --until 2026-08-14
ccusage-all --credit-rate .056  # output-heavy end of the Kiro estimate
ccusage-all --json              # rows + totals
ccusage-all --online            # let ccusage refresh LiteLLM prices (network)
```

The trustworthy cost is always *real tokens × published list price*. Claude and
Codex log real tokens, so their cost is near-exact — **if** the price table has
the model. ccusage's LiteLLM table has the breadth but prices any model it lacks
at a silent **$0**; here that zeroes `claude-opus-5`, the largest consumer.
l3m's curated snapshot covers exactly those frontier models. So the default
`--rates l3m` prices the Claude family from l3m and defers everything else to
LiteLLM; `--rates litellm` is pure ccusage, kept so the $0 gap stays visible.

Kiro is the exception: no token counts, only credits, so its dollars are the one
real *estimate* — the −13%/+88% band rides on the Kiro subtotal alone. The `Unit`
column names what `Consumed` counts — `credits` for Kiro (metered), `Mtok`
(millions of tokens) for Claude/Codex (logged) — so the two never masquerade as
one number; `Cost (USD)` is the only column comparable across harnesses.

l3m burns Bedrock tokens too, and ccusage cannot see it — it keeps no
Claude-Code-shaped log. Its rows come from l3m's own bookkeeping instead: every
turn boundary publishes the session sidecar (`last_state.json` — cumulative cents
plus per-wire token counters) to `refs/agents/state/<agent>/self` in the hub
(`$L3M_HUB`, settings `hub.path`, else `~/.l3m/hub.git`), so that ref's history is
a dated series of running totals, and differencing consecutive samples gives daily
usage. The dollars are l3m's own `cents`, so `--rates` does not move them: l3m
charges each call at the model that call actually used, which the per-wire
counters can no longer tell us. Two consequences to read the table with — the
`Model` cell is the session's *brain*, so a `consult_model` side call to another
model folds into its parent's row; and one row may carry no date (`-`), the
earliest sample in a ref, which is a conversation already under way whose spend is
real but whose days were never recorded (it is kept rather than dropped, so the
total stays right, and it ignores `--since`/`--until`). Sessions that never
publish to a hub aren't counted.

## Install

```fish
ln -sf ~/dotfiles/kiro-ccusage/kiro-ccusage ~/.local/bin/kiro-ccusage
ln -sf ~/dotfiles/kiro-ccusage/ccusage-all ~/.local/bin/ccusage-all
```

Needs `ccusage` on PATH (in the Brewfile) and Python 3.9+.

## How it works

Reads per-turn credits from `~/.kiro/sessions/*/sess_*/messages.jsonl` and writes
JSONL that ccusage's Claude reader accepts:

```
~/.local/share/kiro-ccusage/projects/<workspace>/<session-uuid>.jsonl
```

ccusage groups by *path*, not by record contents, so the workspace name becomes
the project and the filename becomes the session. The dollar figure goes in
`costUSD`, which overrides ccusage's own pricing, and the recorded credits are
kept verbatim in a `kiroCredits` field that ccusage ignores — so re-pricing never
has to touch the source logs. Records key on Kiro's stable `executionId`, so
re-exporting is idempotent.

Model attribution joins `assistant.reasoningModelId` to the credit record on
`executionId` — per turn, so it stays correct when a session switches models,
unlike `session.json`'s single `modelId`.

## Caveats

- Credits are measured; dollar figures are estimates and carry their own
  interval, rounded to whole dollars to avoid implying false precision.
- Under `--ccusage` the five token columns read 0, since Kiro reports no tokens.
- v1/v2-engine turns are not counted (~0.4% of spend). Use `--v3`.
- Per-model splits carry ~15% attribution error from subagents running a
  different model than their parent; totals are unaffected.

Cross-check totals with `/usage` inside a Kiro session.
