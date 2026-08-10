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

## Install

```fish
ln -sf ~/dotfiles/kiro-ccusage/kiro-ccusage ~/.local/bin/kiro-ccusage
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
