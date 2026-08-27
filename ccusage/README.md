# ccusage-all

One usage table across every coding harness on this box — Kiro, l3m, Claude Code,
Codex, opencode — reading each harness's own logs natively. (The name is
historical: it used to shell out to
[ccusage](https://github.com/ccusage/ccusage); the native parsers transcribe
ccusage's rules and were validated token-for-token against it, then it was
dropped as a dependency.)

```fish
ccusage-all
```

```
Date        Day Total  Harness  Model                Consumed  Unit        Rate  Cached     Std   Eff  Cost (USD)
----------  ---------  -------  ------------------  ---------  -------  -------  ------  ------  ----  ----------
-             $161.27  l3m      l3m-unknown             41.25  Mtok       $3.91     28%       -     -     $161.27
2026-08-26  $1,995.02  claude   claude-opus-5        1,809.02  Mtok      $0.745     96%  $0.813  0.92   $1,347.96
                       codex    openai.gpt-5.6-sol      81.07  Mtok       $1.02     91%  $0.825  1.24      $83.02
                       codex    openai.gpt-5.4           2.06  Mtok       $1.43     49%  $0.299  4.78       $2.95
                       kiro     gpt-5.6-sol          5,332.86  credits  $0.0747       -       -     -     $398.36
```

**Cost = Consumed × Rate** on every row, and `Day Total` is that date's total
across all harnesses, shown once per day.

```fish
ccusage-all                     # default: l3m rates, Kiro calibrated + estimated
ccusage-all --rates litellm     # price everything from the LiteLLM table
ccusage-all --since 2026-08-01 --until 2026-08-14
ccusage-all --credit-rate .056  # output-heavy end of the Kiro estimate
ccusage-all --raw-credits       # Kiro credits exactly as scanned, uncalibrated
ccusage-all --since 2026-08-01 --verify-credits 66425.17   # re-check the scan
ccusage-all --json              # rows + totals + reference mix + settings in force
ccusage-all --online            # refresh LiteLLM prices over the network
```

## Comparing rates across harnesses

`Rate` is the **effective** blended $/Mtok — cost ÷ total tokens. It is a mix
statistic, not a price, and it is **not** comparable across harnesses. Within one
model the list prices span 50×: opus-5 charges $0.50/Mtok for a cache read and
$25.00/Mtok for output. So a 96%-cached harness and a 49%-cached one show wildly
different $/Mtok under *identical* pricing, as `codex` does against itself above.

Don't try to reconcile them. Both price tables already agree exactly (`--rates
l3m` and `--rates litellm` return the same totals), so the spread is real and
carries information. Three columns make the comparison valid instead by holding
the mix fixed:

- **`Cached`** — the row's cache-read share, which drives most of the spread.
- **`Std`** — the row re-priced at the *pooled* mix of every token-logged row in
  the window, so it varies only by model. This is the standardized cost.
- **`Eff`** — `Rate / Std`: how favourable that row's own mix was. Below 1.00 is
  cheaper than this box's average, above is dearer. `gpt-5.4` at 4.78 is not an
  expensive model, it's a badly-cached one.

A model no price table lists gets no `Std`. Kiro gets none of the three: it logs
no token buckets, and its $/credit already embeds an *assumed* mix (a flat ×0.1
cache-read factor — see [FINDINGS.md](FINDINGS.md)), which is exactly why it
can't join that column honestly.

## Pricing

The trustworthy cost is always *real tokens × published list price*. Claude,
Codex, and opencode log real tokens, so their cost is near-exact — **if** the
price table has the model. Two tables transcribe the same published list
prices: l3m's Lean-proof-pinned snapshot (Claude family) and an embedded
LiteLLM snapshot for the rest, refreshable with `--online`. The default
`--rates l3m` prices the Claude family from l3m and defers everything else to
LiteLLM; `--rates litellm` prices everything from the LiteLLM table. A model
neither table knows prices to $0 and is flagged `(!)` on its row rather than
quietly undercounted. OpenAI models are two-stage priced: turns whose input
exceeds 272K tokens bill entirely at the long-context rates.

Kiro is the exception: no token counts, only credits, so its dollars are the one
real *estimate* — the −13%/+88% band rides on the Kiro subtotal alone. The `Unit`
column names what `Consumed` counts — `credits` for Kiro (metered), `Mtok`
(millions of tokens) for the token-logged harnesses — so the two never masquerade
as one number; `Cost (USD)` is the only column comparable across harnesses.

## How each harness is read

**Claude Code, Codex, opencode** — read natively from their own logs
(`~/.claude/projects/**/*.jsonl`, `~/.codex/sessions/**/*.jsonl`, opencode's
SQLite db). The parsing rules — streaming/sidechain dedup for Claude,
cumulative-advance filtering and fork-replay skipping for Codex — are
transcribed from ccusage's Rust adapters and were validated token-for-token
against its output. Results are cached incrementally under
`~/.cache/ccusage-all/`, keyed by file stat signatures, so a run re-parses only
the session files that changed since the last one: typical runs take well under
a second and are always current, with no cold-scan penalty after the first
build (~15s over 3.5GB of logs). One known deliberate divergence from ccusage:
it applies a 200K long-context boundary to `openai.gpt-5.5` because its pricing
entry for that key lacks tier data; this tool uses the published 272K boundary
for the whole GPT family.

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

That scan is measurably incomplete, so the credits it finds are calibrated
against `/usage` — the one authoritative total Kiro publishes, and which does
*not* clamp at the plan cap (it reports 664.3% on an org seat, and the true
figure). Measured 2026-08-27 the scan read **5.1% low**, so credits are scaled by
`KIRO_COMPLETENESS` = 1.0533. That corrects the count, not the price: the
−13%/+88% band still rides on the `$`/credit conversion alone. `--raw-credits`
reports the uncorrected scan; `--verify-credits <total>` re-measures the factor
against a fresh `/usage` reading and warns if it has drifted more than 2%.

**l3m** burns Bedrock tokens too, but keeps no Claude-Code-shaped token log the
scanners above could read. Its rows come from l3m's own bookkeeping: every turn
boundary publishes the session sidecar (`last_state.json` — cumulative cents plus
per-wire token counters) to `refs/agents/state/<agent>/self` in the hub
(`$L3M_HUB`, settings `hub.path`, else `~/.l3m/hub.git`), so that ref's history is
a dated series of running totals, and differencing consecutive samples gives daily
usage. The dollars are l3m's own `cents`, so `--rates` does not move them: l3m
charges each call at the model that call actually used, which the per-wire
counters can no longer tell us.

## Install

```fish
ln -sf ~/dotfiles/ccusage/ccusage-all ~/.local/bin/ccusage-all
```

Needs Python 3.9+; no other dependencies.

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
