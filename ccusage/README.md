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
Date        Day Total  Harness  Model               Consumed  Unit       Rate  Cost (USD)
----------  ---------  -------  ------------------  --------  -------  ------  ----------
-             $161.27  l3m      l3m-unknown            41.25  Mtok      $3.91     $161.27
2026-08-26  $2,494.15  claude   claude-opus-5       1,809.02  Mtok     $0.745   $1,347.96
                       codex    openai.gpt-5.6-sol     81.07  Mtok       $0.8      $64.87
                       codex    openai.gpt-5.4          2.06  Mtok      $1.43       $2.95
                       kiro     gpt-5.6-sol         5,062.78  credits  $0.151     $765.63
                       kiro     claude-opus-5       1,721.54  credits  $0.151     $260.34
```

**Cost = Consumed × Rate** on every row, and `Day Total` is that date's total
across all harnesses, shown once per day.

```fish
ccusage-all                                   # unified daily table
ccusage-all --since 2026-08-01 --until 2026-08-14
ccusage-all --online                          # refresh LiteLLM prices first
```


## Rate is a mix statistic, not a price

`Rate` is the **effective** blended $/Mtok — cost ÷ total tokens. It is **not**
comparable across harnesses. Within one model the list prices span 50×: opus-5
charges $0.50/Mtok for a cache read and $25.00/Mtok for output. So a 96%-cached
harness and a 49%-cached one show wildly different $/Mtok under *identical*
pricing.

Don't try to reconcile them — the spread is telling you about caching behaviour,
not about price. Cache-**write** is the term to watch: at 1.25× fresh input it is
12.5× a cache read, so a few percent of it outweighs a large swing in cache-read.

Measured cache-read / cache-write shares, for reference:

| harness | cache-read | cache-write |
|---|---|---|
| claude | 95.1% | 4.4% |
| opencode | 86.5% | 0.0% |
| l3m | 75.4% | 5.2% |
| codex | 75.9% | **unobservable** |

Cache-read share is a **harness** property, not a model one: the same
`claude-opus-5` measures 95.3% under Claude Code and 87.1% under l3m, while four
different models under Claude Code all land within 1.8 points of each other.

Codex's cache-write is unobservable rather than zero — its log carries no
cache-creation field across any of its 10,257 usage events, while `gpt-5.6-sol`
*is* billed for cache writes at $6.25/Mtok. So its cost here is a slight
underestimate. Each such row is labelled with a `partial` mix provenance.

## Kiro is the only harness that assumes a mix

Every other harness *counts* its cache reads and writes — they arrive in the API
response and go straight into a bucket, priced at its own published tier. No
estimate is involved. Kiro publishes no buckets at all, so its $/credit is a
primitive times an assumed mix:

```
$0.1512/credit  =  $0.7468 (fresh-input basis)  ×  0.2025
                                                   ^^^^^^ 90% cache-read / 5% cache-write / 5% fresh input
```

Cache-read share is a **harness** property, not a model one: the same
`claude-opus-5` measures 95.3% under Claude Code and 87.1% under l3m, while four
different models under Claude Code all land within 1.8 points of each other. So
there is no per-model mix to assign — only a per-harness one, and Kiro's cannot
be observed.

Measurable harnesses span 75.4%–95.1% cache-read, with Claude Code at the
ceiling. 90% sits inside that range rather than assuming Kiro caches best of all.
The numbers are round on purpose: this is a guess and should read as one, where
Claude Code's measured 95.1/4.4 would read as a measurement while being another
harness's measurement. Cache-**write** is the term that does the work — at 1.25×
fresh input it is 12.5× a cache read, so the 5% contributes more than the 10-point
drop in cache-read takes away.

To change it, edit `KIRO_DEFAULT_MIX`. There is no flag, which is what makes the
mix in that constant provably the one that priced every Kiro row.

Kiro's credits are reported exactly as scanned. `/usage` — Kiro's own
authoritative total, which does *not* clamp at the plan cap — showed the scan
running 5.1% low on 2026-08-27 (63,061.16 against 66,425.17). That is documented
rather than corrected: the gap was one aggregate measurement over one billing
period, and scaling every day and model by it spreads the miss proportionally
when its one known component (v1/v2-engine turns, ~0.4%) is not spread that way.
**Read the Kiro total as a floor, roughly 5% low**, on top of the −13%/+88% band
on its $/credit.

## Pricing

The trustworthy cost is always *real tokens × published list price*. Claude,
Codex, and opencode log real tokens, so their cost is near-exact — **if** the
price table has the model. Prices come from an embedded LiteLLM snapshot,
refreshable with `--online`; a model it doesn't know prices to $0 and is flagged
`(!)` on its row rather than quietly undercounted. OpenAI models are two-stage
priced: turns whose input exceeds 272K tokens bill entirely at long-context rates.

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
and match `/usage`'s plan counter.

That scan is known incomplete — `/usage` showed it 5.1% low on 2026-08-27 — and
is reported uncorrected. See above.

**l3m** burns Bedrock tokens too, but keeps no Claude-Code-shaped token log the
scanners above could read. Its rows come from l3m's own bookkeeping: every turn
boundary publishes the session sidecar (`last_state.json` — cumulative cents plus
per-wire token counters) to `refs/agents/state/<agent>/self` in the hub
(`$L3M_HUB`, settings `hub.path`, else `~/.l3m/hub.git`), so that ref's history is
a dated series of running totals, and differencing consecutive samples gives daily
usage. The dollars are l3m's own `cents`, never re-priced here: l3m
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
