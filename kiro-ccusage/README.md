# ccusage-all

One usage table across every coding harness on this box — Kiro, l3m, Claude Code,
Codex, opencode — through [ccusage](https://github.com/ryoppippi/ccusage) where it
can see the logs and each harness's own bookkeeping where it can't.

```fish
ccusage-all
```

```
Date        Day Total  Harness  Model              Consumed  Unit        Rate  Cost (USD)
----------  ---------  -------  -----------------  --------  -------  -------  ----------
-             $161.27  l3m      l3m-unknown           41.25  Mtok       $3.91     $161.27
2026-08-17  $1,560.24  claude   claude-opus-5      1,660.29  Mtok      $0.893   $1,483.21
                       claude   claude-fable-5         7.68  Mtok       $3.11      $23.91
                       kiro     claude-opus-5        266.68  credits  $0.0747      $19.92
                       l3m      claude-opus-5          4.20  Mtok       $1.25       $5.23
```

**Cost = Consumed × Rate** on every row, and `Day Total` is that date's total
across all harnesses, shown once per day.

```fish
ccusage-all                     # default: l3m rates, Kiro estimated
ccusage-all --rates litellm     # price everything the way ccusage does
ccusage-all --since 2026-08-01 --until 2026-08-14
ccusage-all --credit-rate .056  # output-heavy end of the Kiro estimate
ccusage-all --json              # rows + totals + the settings in force
ccusage-all --online            # let ccusage refresh LiteLLM prices (network)
```

## Pricing

The trustworthy cost is always *real tokens × published list price*. Claude and
Codex log real tokens, so their cost is near-exact — **if** the price table has
the model. ccusage's LiteLLM table has the breadth but prices any model it lacks
at a silent **$0**; here that zeroes `claude-opus-5`, the largest consumer.
l3m's curated snapshot covers exactly those frontier models. So the default
`--rates l3m` prices the Claude family from l3m and defers everything else to
LiteLLM; `--rates litellm` is pure ccusage, kept so the $0 gap stays visible.
A model whose tokens still price to $0 is flagged `(!)` on its row rather than
quietly undercounted.

Kiro is the exception: no token counts, only credits, so its dollars are the one
real *estimate* — the −13%/+88% band rides on the Kiro subtotal alone. The `Unit`
column names what `Consumed` counts — `credits` for Kiro (metered), `Mtok`
(millions of tokens) for the token-logged harnesses — so the two never masquerade
as one number; `Cost (USD)` is the only column comparable across harnesses.

## How each harness is read

**Claude Code, Codex, opencode** — `ccusage daily --json --by-agent`, which is the
token ground truth, then re-priced as above.

**Kiro** meters in credits and exposes no token counts locally, so credits are
what gets recorded and dollars are derived from them.
[FINDINGS.md](FINDINGS.md) documents why, and [calibrate.py](calibrate.py)
re-derives every constant from your own data. The source is the v3 session log:

```
~/.kiro/sessions/<workspace-hash>/sess_<uuid>/messages.jsonl
```

Each completed turn appends a `usage_summary` record carrying that turn's
credits. Model attribution joins the `assistant` records sharing the turn's
`executionId` — per turn, so it stays correct when a session switches models,
unlike `session.json`'s single `modelId`, which is only the fallback. Turns key on
`executionId`, so a turn recorded twice counts once. Credits are already scaled by
each model's rate multiplier, so they are comparable and summable across models
and match `/usage`'s plan counter; the dollar figure moves with `--credit-rate`
and the credits never do.

**l3m** burns Bedrock tokens too, and ccusage cannot see it — it keeps no
Claude-Code-shaped log. Its rows come from l3m's own bookkeeping: every turn
boundary publishes the session sidecar (`last_state.json` — cumulative cents plus
per-wire token counters) to `refs/agents/state/<agent>/self` in the hub
(`$L3M_HUB`, settings `hub.path`, else `~/.l3m/hub.git`), so that ref's history is
a dated series of running totals, and differencing consecutive samples gives daily
usage. The dollars are l3m's own `cents`, so `--rates` does not move them: l3m
charges each call at the model that call actually used, which the per-wire
counters can no longer tell us.

## Install

```fish
ln -sf ~/dotfiles/kiro-ccusage/ccusage-all ~/.local/bin/ccusage-all
```

Needs `ccusage` on PATH (in the Brewfile) and Python 3.9+.

## Caveats

- Kiro credits are measured; its dollar figures are estimates and carry their own
  interval, rounded to whole dollars to avoid implying false precision.
- Only v3-engine Kiro turns write `usage_summary`; v1/v2 turns land in SQLite
  instead and are not counted (~0.4% of spend). Run `kiro-cli --v3`.
- Kiro per-model splits carry ~15% attribution error from subagents running a
  different model than their parent; totals are unaffected.
- For l3m the `Model` cell is the session's *brain*, so a `consult_model` side
  call to another model folds into its parent's row; and one row may carry no date
  (`-`) — the earliest sample in a ref, a conversation already under way whose
  spend is real but whose days were never recorded. It is kept rather than dropped
  so the total stays right, and it ignores `--since`/`--until`. l3m sessions that
  never publish to a hub aren't counted.

Cross-check Kiro totals with `/usage` inside a Kiro session.
