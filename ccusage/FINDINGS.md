# Kiro CLI usage accounting

What Kiro CLI 2.16.2 records about its own consumption, how much of it is
recoverable locally, and how `ccusage-all` turns that into a cost figure.
Measured on 2026-08-10 against kiro-cli 2.16.2 and ccusage 20.0.19; revised
2026-08-19 (context windows now read live; steps 2 and 4 restricted to
single-request turns). `./calibrate.py` re-derives every number.

## The short version

Kiro **never exposes token counts locally**. It meters in **credits**, computed
server-side and streamed to the client as a pre-computed scalar. Credits are
recoverable per turn and per model, and convert to a dollar *estimate* carrying
an explicit interval, asymmetric at **-13%/+88%** of the point value.

## What is and is not available

| Want | Available? | Where |
|---|---|---|
| Credits per turn | yes | `usage_summary` in v3 `messages.jsonl` |
| Model per turn | yes | `assistant.reasoningModelId`, joined on `executionId` |
| Account credits this period | yes | `/usage` inside a session — authoritative, unclamped |
| Plan name and allowance | yes | `/usage` — e.g. `KIRO POWER`, 10,000 credits/period |
| Input/output/cache tokens | **no** | fields exist in the schema, always `null` |
| Credits via a hook | **no** | no hook carries usage; see below |
| Credits for v1/v2-engine turns | partly | SQLite, last turn per conversation only |

### Tokens are genuinely absent, not merely hidden

`request_metadata` carries `total_tokens`, `uncached_input_tokens`,
`output_tokens`, `cache_read_input_tokens`, `cache_write_input_tokens` — all
`null` in every record checked (0 non-null across the SQLite store; 0 non-zero
across 6,830 turns in 766 legacy session files).

The client *can* parse tokens: a real code path reads them from the service
response and forwards them to an OTLP counter `kiro_cli_tokens_consumed` with
`model` and `token_type` dimensions — exactly the wanted breakdown. It never
fires. Pointing `KIRO_TELEMETRY_OTLP_ENDPOINT` at a local sink captured 16 real
metric names including `kiro_cli_credits_consumed{model=...}`, but never
`kiro_cli_tokens_consumed`: the KAS `turn_completion` payload carries only
`{promptTurnSummaries, elapsedTime, status, requestIds}`, so the emitter is
called with all-`undefined` values and skips them. The metric is wired and
unreachable.

### No input/output split, on the current version

Worth separating from "no tokens": even the *shape* of Kiro's accounting has no
room for an input/output distinction, so nothing here is an artifact of running
an old build. `toolbox update kiro-cli --check` reports 2.16.2 **is** the latest.

- `promptTurnSummaries` is a list, which could in principle carry one entry per
  token class. Across 155 non-empty turns every one holds exactly **one** entry,
  always `unit: "credit"`. No other unit appears.
- Each entry's keys are exactly `{unit, unitPlural, usage, usedTools}`.
- A key-union over every payload type in every session log — including
  `sub-executions/` — yields **zero** keys matching input/output/token.
- `/context` does break usage down, but by *category* (context files, tools, Kiro
  responses, your prompts) and labels each "(estimated)". Those are all
  input-side, so it is a context-composition view, not an input/output split.
- `/stats` does not exist on this build; it is absent from the slash-command list.

So the input/output mix stays an unmeasured quantity, which is why it is folded
into the cost band rather than shown as a column. Re-check after a Kiro upgrade:
if `promptTurnSummaries` ever returns more than one entry, or a new unit appears,
a real input/output column becomes possible.

### No hook carries usage

Exactly 5 hook events exist — `agentSpawn`, `userPromptSubmit`, `preToolUse`,
`postToolUse`, `stop` — enforced by an allowlist in the shipped binary. Payloads,
captured empirically by wiring all five to a stdin-dumping script:

```
agentSpawn       {hook_event_name, cwd, prompt}     # prompt only if one was given
userPromptSubmit {hook_event_name, cwd, prompt}
preToolUse       {hook_event_name, cwd, tool_name, tool_input}
postToolUse      {hook_event_name, cwd, tool_name, tool_input, tool_response}
stop             {hook_event_name, cwd, assistant_response}
```

`stop` is the only post-turn event and carries no usage, even though the CLI
prints `Credits: 0.50` on that same turn. Env adds only `KIRO_SESSION_ID`,
`KIRO_CLI_PATH`, and `USER_PROMPT`.

Hooks are also the wrong lever structurally: they are per-agent-config only (no
global setting), and 78 of 81 configs in `~/.kiro/agents/` are AIM-managed and
overwritten on update. Hang customizations on the fish `kiro-cli` wrapper
instead. Hooks additionally do **not** fire under `--v3`.

## Calibration: credits to tokens to dollars

Run `./calibrate.py` to reproduce all of this.

### Step 1 — credits per token

Kiro logs a per-request context-fill percentage beside each turn's credits, so
on a **single-request** turn the billed token count is known and credits/token
solves directly:

**1 credit at multiplier 1.0 = ~317,000 cached-input tokens** (k = 3.1553e-6),
median of 48 turns across fable-5, opus-5 and sonnet-5.

The sample is **bimodal**, and this is the main caveat. At an identical 25.336%
context fill, some turns cost 3.5145 credits and others 1.8605 — a 1.80× split.
Nothing in any logged field distinguishes them: same model, same
`chat_conversation_type`, same (empty) meta tags, same response size, same rate
multiplier. The most likely driver is thinking/output tokens, which are billed
but never reported. Hence:

- Use the **median**, not the mean. The mean (2.7462e-6) falls between the modes
  and matches neither.
- The upper mode is dense and tight (n=31, CV 0.036) and governs ordinary turns.
- p10 to max spans 1.760e-6 to 3.477e-6, the dominant term in the cost band.

Restrict any fit to turns where `#contextSamples == #requestIds`. On
multi-request turns the ratio spans 2–118× because context is sampled per
request.

### Step 2 — held-out check

Restricted to **single-request** held-out turns, for the same reason step 1's fit
is: on a multi-request turn the context samples are cumulative (see below), so no
token count is recoverable and a prediction against one is meaningless. Over the
10 such turns (gpt-5.6-sol, opus-4.8, opus-4.7) the median absolute error is
**39.5%**, scattering in *both* directions (-70% to +115%) — noisy at this sample
size, but unbiased, which is what the bimodality in step 1 predicts.

An earlier revision of this document claimed **-0.5%** on `claude-opus-4.7`. That
turn had 54 requests, so its token count was the invalid sum described below; the
agreement was a coincidence on a computation that should not have been made.

Restrict any fit to turns where `#contextSamples == #requestIds`, and then
further to `requests == 1`. On multi-request turns the ratio spans 2–118×
because context is sampled per request.

### Context samples are cumulative, not per-request costs

The single most consequential methodology point, because it invalidates the
obvious way to price a turn. A turn's `contextUsage` samples are snapshots of
**one growing context**, not independent per-request amounts:

- 588 of 701 multi-sample turns (**83.9%**) are strictly non-decreasing; 662
  (**94.4%**) are non-decreasing at ≥90% of steps.
- The context grows only **1.05× median** from a turn's first sample to its last
  — it is the same context being re-sent, not new content each time.
- Median `sum(samples) / max(sample)` is **15.85×**.

So summing a turn's samples counts the re-sent prefix once per request and
overstates tokens by roughly that factor. Steps 2 and 4 both used to do this over
the whole corpus; both now restrict to single-request turns, and step 4 reports
the whole-corpus token figure as an explicit upper *bound* rather than an
estimate.

### Model table is read live, never hardcoded

`kiro-cli chat --list-models --format json` is authoritative for both
`rate_multiplier` and `context_window_tokens`. `calibrate.py` reads both on every
run and prints any drift against its fallback tables.

This exists because the hand-maintained table had `gpt-5.6-sol`, `gpt-5.6-terra`
and `gpt-5.6-luna` at 272,000 against a real 1,000,000, and omitted
`qwen3-coder-next` (256,000, so it fell through to the 1,000,000 default). The
GPT error undercounted those turns' tokens by **3.676×** and inflated their
implied credits-per-token by the same factor, which read as *the GPT family needs
its own calibration*: implied `k` was 7.092e-6 against Claude's 2.065e-6, a 3.43×
gap. With the correct window the ratio is **0.93×**. There is no GPT-specific
effect — it was one stale constant.

### Credits are recorded POST-multiplier

Worth stating plainly, because it determines whether the multiplier belongs in
any conversion: the credit figure Kiro records **already has the model's rate
multiplier applied**. It is not a raw base unit awaiting scaling.

Two same-size turns (~26k tokens of context each) settle it:

| Model | Multiplier | Credits recorded |
|---|---|---|
| claude-sonnet-5 | 1.3x | 0.1091 |
| claude-fable-5 | 4.4x | 0.3633 |

The credit ratio is 3.33x for an identical token count, against a multiplier
ratio of 4.4/1.3 = 3.385. Across the full sample the observed fable/sonnet ratio
is 3.383 versus 3.385 predicted. Dividing recorded credits by the multiplier
collapses all three models onto one constant (spread 1.00x); not dividing leaves
them 3.38x apart.

Consequences:

- The `Credits` column and `/usage`'s plan cap are both in already-scaled units,
  so they are directly comparable and directly summable across models.
- Step 1 below must divide by the multiplier to recover a per-token constant.
- Step 3's cancellation follows from this: since credits carry the multiplier and
  the multiplier tracks price, one rate converts credits to dollars for every
  model.

### Step 3 — multipliers anchor credits to dollars

`kiro-cli chat --list-models --format json` publishes a `rate_multiplier` per
model. Those track Bedrock **input** prices, checked against published prices:

| Model | Multiplier | Implied $/Mtok in | Actual | Error |
|---|---|---|---|---|
| claude-sonnet-4.5 | 1.30x | $3.00 | $3.00 | 0.0% |
| claude-opus-4.5 | 2.20x | $5.08 | $5.00 | +1.5% |
| claude-haiku-4.5 | 0.40x | $0.92 | $1.00 | -7.7% |

Because credits already scale by the multiplier, **the multiplier cancels** and
one model-independent rate converts credits to dollars:

- **$0.0747/credit** if cache-read-dominated (every token a cache read)
- **$0.0557/credit** when output-dominated

`ccusage-all` no longer defaults to either. Since 2026-08 it prices Kiro at an
explicit assumed input-side mix of **90% cache-read / 5% cache-write / 5% fresh
input**, giving `$0.7468 × 0.2025 = $0.1512/credit`. The reasoning:

- 100% cache-read is not a neutral assumption, it is a known-low one. No harness
  measured on this box achieves it; Claude Code, the best, reaches 95.1%.
- Cache-read share is a **harness** property, not a model one. The same
  `claude-opus-5` measures 95.3% under Claude Code and 87.1% under l3m, while four
  different models under Claude Code all land within 1.8 points (94.4 / 95.1 /
  95.3 / 96.2). So there is no per-model mix to borrow — only a per-harness one,
  and Kiro's is unobservable.
- Across measurable harnesses the range is 75.4%–95.1%. Claude Code sits at the
  top, so borrowing its mix assumes Kiro is the best cacher present. 90% sits
  inside the range instead.
- The mix is **deliberately round** so it reads as the guess it is. Claude Code's
  measured 95.1/4.4 was rejected for looking like a measurement while being
  Claude Code's measurement wearing a Kiro label.
- Cache-write is the term that matters: it costs 1.25× fresh input, 12.5× a cache
  read. And the 5% fresh-input remainder contributes a quarter of the factor,
  since fresh input is 10× a cache read.

There is no flag for this — `KIRO_DEFAULT_MIX` in the script is the single place
it lives, which is what makes it provably the mix that priced every Kiro row.

### Step 4 — independent magnitude check

Pricing the measured context tokens straight at Bedrock cache-read rates, never
touching credits, and comparing against the credit route over the **same
single-request turns** (n=66, where the token count is real) agrees to within
**5%** by disjoint methods. `calibrate.py` prints both totals for the local data,
plus the whole-corpus token figure as an explicit upper bound — that one sums
cumulative context samples, so it is not comparable and must not be read as a
rival estimate.

Note this route shares two of three assumptions with step 3 — the same
`anchor` and the same `CACHE_READ_DISCOUNT` — so it validates the
credits-per-token constant `k` and *not* the assumed cache-read-dominated mix.
If the real mix is richer in output or cache-write than the ×0.1 factor assumes,
both routes are low together and this check cannot detect it.

An external check also exists, and it is the strongest one available: compare the
scan's credit total for the billing period against `/usage` inside a session.

`/usage` does **not** clamp at the plan cap — an earlier revision of this
document claimed it did. Measured 2026-08-27 on an org-provisioned seat it
reported `Credits (66425.17 of 10000 covered in plan)` at **664.3%**, i.e. the
true total and a percentage well past 100. So it anchors the credit *count*
exactly, which quarantines all remaining uncertainty in the $/credit conversion.

Against that anchor the session-log scan reads **5.1% low** (63,061.16 scanned
against 66,425.17 authoritative, window 2026-08-01+).

`ccusage-all` does **not** correct for it. It briefly did, scaling every credit by
1.0533, and that was wrong: the gap is one aggregate measurement over one billing
period, and multiplying every day and model by it spreads the miss proportionally
when its one known component (limitation 3 below, ~0.4 of the 5.1 points) is not
spread that way. The result matched neither the logs nor the authority. The scan
is now reported as-is and the gap documented — read the Kiro total as a floor,
roughly 5% low.

The remaining ~4.7 points are unexplained. Candidates: interrupted turns whose
`usage_summary` never landed, sessions outside `KIRO_SESSIONS`, or `executionId`
collisions in the dedup. Caveat on the anchor: the period start is assumed to be
calendar-month (the reset is 2026-09-01); if it began later, the true gap is
larger.

## Known limitations

1. **Token columns read 0.** By design — Kiro exposes no tokens. The estimate
   rides in `costUSD`, which overrides ccusage's own pricing. Synthesizing token
   counts would render invented numbers as if measured.
2. **The 1.80× bimodality** is unexplained and dominates the cost band. Combined
   with the anchor's ±4.7% spread it gives **-13%/+88%** on any dollar figure —
   asymmetric because credits-per-token is left-skewed, so most turns sit near
   the low-cost end with a tail running high. Both sources compose; the
   input/output mix is not added on top, since unreported output tokens are what
   drive the bimodality in the first place.
3. **v1/v2-engine turns are missing.** Those write credits only to SQLite, which
   keeps just the last turn per conversation. Measured on one local history the
   v1/v2 share was about **0.4%** of total credits. Use `--v3` for complete
   accounting. This is a known component of the 5.1% scan gap measured against
   `/usage`, but only a small part of it; the rest is unexplained.
4. **Per-model splits carry ~15% attribution error.** Subagents run a different
   model than their parent 15% of the time, and their spend is folded into the
   parent turn's credits. Totals are unaffected — turns with and without
   subagent calls show the same actual/predicted ratio (0.72 vs 0.75), which is
   what shows the spend is included rather than lost.
5. **Prices are hardcoded** from 2026-08. Re-run `calibrate.py` after rate
   changes. Multipliers and context windows are *not* hardcoded — they are read
   live from `kiro-cli chat --list-models` on every run.
6. **The mix factor is unvalidated.** `$0.1512` = `$0.7468` (fresh-input) ×
   0.2025, where 0.2025 comes from an *assumed* 90/5/5 input-side mix. Nothing
   here tests that mix; step 4 shares the same structure and so cannot detect a
   mix error. Kiro publishes no token buckets, so its real cache behaviour is
   unobservable and every candidate mix is a borrow from some other harness. The
   measurable ones span factors 0.151 (claude) to 0.329 (l3m) — a 2.2× spread —
   which is the true width of this uncertainty, wider than the printed band.
   The old default of 0.100 (100% cache-read) was below *all* of them.
7. **`$0.0557/credit` sits outside the band.** The output-dominated rate comes
   from `base * 5 / 67`, an underived constant, and falls below the band's own
   low end of `$0.0647`. Unresolved, and no longer reachable from the CLI — the
   flag that exposed it is gone.
8. **Held-out validation is thin.** Only 10 held-out turns are single-request,
   and the median absolute error over them is 39.5%. The 102 multi-request
   held-out turns are excluded rather than mispredicted, which is correct but
   leaves the check underpowered. It strengthens as more single-request turns
   accumulate.

## ccusage integration notes

- **Records must be compact JSON.** ccusage prefilters lines on the literal
  byte sequence `"usage":{` — `json.dumps` default spacing silently drops the
  record with no error, just "No usage data found". Use `separators=(",", ":")`.
- Session id comes from the **filename**; project from the **parent directory**.
  A record's own `sessionId` and `cwd` are ignored.
- `costUSD` overrides computed pricing (except under `--mode calculate`).
- Dedup key is `message.id`, or `(requestId, message.id)` when both exist.
  `ccusage-all` keys Kiro turns on the stable `executionId`, so a turn recorded
  twice counts once.
- Timestamps must be full RFC3339; date-only strings and epoch ints are dropped.
