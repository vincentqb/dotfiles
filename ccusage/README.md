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
2026-08-26  $2,569.83  claude   claude-opus-5       1,809.02  Mtok     $0.745   $1,347.96
                       codex    openai.gpt-5.6-sol     81.07  Mtok      $1.02      $83.02
                       codex    openai.gpt-5.4          2.06  Mtok      $1.43       $2.95
                       kiro     gpt-5.6-sol         5,332.86  credits  $0.151     $806.47
                       kiro     claude-opus-5       1,813.37  credits  $0.151     $274.23
```

**Cost = Consumed × Rate** on every row, and `Day Total` is that date's total
across all harnesses, shown once per day.

```fish
ccusage-all                     # default: l3m rates, Kiro calibrated + estimated
ccusage-all --rates litellm     # price everything from the LiteLLM table
ccusage-all --kiro-mix 95/5     # price Kiro at Claude Code's measured token mix
ccusage-all --since 2026-08-01 --until 2026-08-14
ccusage-all --credit-rate .056  # output-heavy end of the Kiro estimate
ccusage-all --raw-credits       # Kiro credits exactly as scanned, uncalibrated
ccusage-all --since 2026-08-01 --verify-credits 66425.17   # re-check the scan
ccusage-all --json              # rows + totals + reference mix + settings in force
ccusage-all --online            # refresh LiteLLM prices over the network
```

## Rate is a mix statistic, not a price

`Rate` is the **effective** blended $/Mtok — cost ÷ total tokens. It is **not**
comparable across harnesses. Within one model the list prices span 50×: opus-5
charges $0.50/Mtok for a cache read and $25.00/Mtok for output. So a 96%-cached
harness and a 49%-cached one show wildly different $/Mtok under *identical*
pricing.

Don't try to reconcile them. Both price tables already agree exactly (`--rates
l3m` and `--rates litellm` return the same totals), so the spread is real: it is
telling you about caching behaviour, not about price. The per-bucket token counts
that drive it are in `--json`. Cache-**write** is the term to watch — it costs
1.25× fresh input, so 12.5× a cache read, and a few percent of it outweighs a
large swing in cache-read.

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
underestimate. `--json` records this as a `partial` mix provenance.

## Kiro is the only harness that assumes a mix

Every other harness *counts* its cache reads and writes — they arrive in the API
response and go straight into a bucket, priced at their own published tier. No
estimate is involved. Kiro logs no buckets, so its $/credit is a primitive times
an assumed mix:

```
$0.1512/credit  =  $0.7468 (fresh-input basis)  ×  0.2025
                                                   ^^^^^^ 90% cache-read / 5% cache-write / 5% fresh input
```

`--json` carries the assumed mix on every Kiro row, so the claim is inspectable
even though the table no longer has a column for it.

That default is more caching than any harness here actually achieves.
`--kiro-mix 95/5` substitutes Claude Code's measured 95.1%/4.4% instead — the
defensible proxy, since Kiro is an Anthropic-model agentic CLI with automatic
cache management and architecturally its twin. It gives **$0.1176/credit, +57%**,
and lands 70% of the way up the existing −13%/+88% band, which is corroboration:
that band's lopsided upper half was absorbing exactly this bias.

Note what drives it. At 95/5 the cache-read term is `0.95 × 0.10 = 0.095`, which
is *below* the current 0.100 — dropping from 100% to 95% caching on its own makes
Kiro **cheaper**. The correction comes almost entirely from the 5% cache-write at
`0.05 × 1.25 = 0.0625`, i.e. 40% of the factor from 5% of the tokens. `90/10`
breaks out of the band entirely, which is the signal it's too aggressive.

Output is deliberately excluded from that mix: `k` was calibrated on context
tokens, which are input-side, so correcting the input-side mix doesn't
double-count — whereas [FINDINGS.md](FINDINGS.md) argues the 1.80× bimodality in
`k` already *is* unreported output.

## Provenance

Every row states how each quantity it reports is *known*, and the table derives
its markers from those labels alone — it never re-infers provenance from whether
a field happens to be present. One vocabulary, four slots per row:

| slot | values |
|---|---|
| `consumed` | `counted` (summed token buckets) · `metered` (a scalar the harness computed) |
| `cost` | the price source: `l3m` · `litellm` · `l3m-self` · `kiro-credit` · `unpriced` |
| `mix` | `measured` · `assumed` (renders `~`) · `no-mix` |
| `std` | `standardized` · `unpriced` · `ambiguous` · `no-tokens` |

Two checks keep it honest. `provenance()` rejects any label outside the
vocabulary, so a typo can't fall through a lookup and render as measured.
`validate_rows()` then checks each label *agrees with the row it describes* — a
row with no token buckets can't claim a `measured` mix, and nothing can claim
`standardized` without a standardized rate. It runs on every invocation.

This replaced four unrelated ad-hoc conventions: `tokens is None`, a `"!"` glued
onto the price-source string, an `assumed_mix` presence check, and `std_rate`
being falsy. Each was somewhere a new row producer could satisfy nothing and
still render as though everything were measured.

## Tests

```fish
cd ccusage; python3 -m unittest discover      # or ./test_ccusage_all.py
```

Stdlib `unittest`, no dependency to install. They run automatically via
pre-commit whenever anything under `ccusage/` changes.

Every test corresponds to something that was once wrong. Most of them guard
provenance — that each row states how its numbers are known, and that the label
agrees with the row. Two of the sharpest were only reachable after extracting
`harness_subtotals` out of `render` and `resolve_kiro_pricing` out of `main`; the
recurring failure mode in this file has been *wiring*, where a correct function
that nothing calls passes every test about the function.

The suite is checked by mutation rather than trusted: reintroducing each of 24
known bugs produces a failure in every case. `test_main_actually_calls_it` exists
purely to fail when the `validate_rows(rows)` call is deleted from `main`, since
every other test would still pass.

An earlier revision carried four more columns (cache-read/write shares, a
mix-normalized rate, and their ratio). They were removed for table width; the two
propagation bugs they once had went with them, and the token counts they
displayed are still in `--json`.

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
