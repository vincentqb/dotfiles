# Kiro CLI usage accounting

What Kiro CLI 2.16.2 records about its own consumption, how much of it is
recoverable locally, and how `kiro-ccusage` turns that into a ccusage report.
Everything here was measured on 2026-08-10 against kiro-cli 2.16.2 and
ccusage 20.0.19; `./calibrate.py` re-derives every number.

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
| Account credits this period | yes | `/usage` inside a session |
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

Predicting a model absent from the fit (`claude-opus-4.7`, 54 requests,
12.3M context tokens) gives 85.2 credits against 84.9 actual: **-0.5%**.

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

- **$0.0747/credit** when cache-read-dominated (the default; Kiro agent traffic
  is overwhelmingly cached input)
- **$0.0557/credit** when output-dominated

### Step 4 — independent magnitude check

Pricing the measured context tokens straight at Bedrock cache-read rates, never
touching credits, and comparing against the credit route over the same history
agreed to within **8%** by disjoint methods. `calibrate.py` prints both totals
for the local data.

An external check also exists: compare the export's credit total for the billing
period against `/usage` inside a session. Note that `/usage` clamps at the plan
cap, so once spend exceeds the plan it reports 100% and can only confirm a lower
bound.

### Step 5 — the uncertainty band printed beside every cost

Two independent sources compose, and the band spans their corners:

| Source | Range | Effect on $/credit |
|---|---|---|
| credits-per-token (p10 to max) | 1.760e-6 to 3.477e-6 | dominant |
| multiplier-to-price anchor | ±4.7% | secondary |

$/credit moves *inversely* with credits-per-token — fewer credits per token means
more tokens bought per credit, hence more dollars. Taking the extreme corners:

- low: highest k with highest anchor → **$0.0647**
- point: median k with mean anchor → **$0.0747**
- high: p10 k with lowest anchor → **$0.1405**

That is **-13%/+88%**. It is printed as an explicit dollar interval next to each
cost — `$120 [104, 226]` — rather than as a percentage, and rounded to whole
dollars: cents on a figure this uncertain would imply precision that is not
there. Sub-dollar rows render as `<$1`, since `$0 [0, 0]` says nothing and the
credits column already carries the detail.

The band was initially derived from source 1 alone, giving -8%/+79%. That put
step 4's independent cross-check just outside the interval, by about 1%, which is
how the missing anchor term surfaced. Folding it in restores containment, and
`calibrate.py` asserts it on every run. A cross-check landing outside the stated
uncertainty is a defect in the uncertainty, not a rounding detail.

The input/output mix is deliberately not compounded on top. Unreported output
tokens are the most likely cause of the bimodality in source 1, so widening for
both would count one phenomenon twice.

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
   accounting.
4. **Per-model splits carry ~15% attribution error.** Subagents run a different
   model than their parent 15% of the time, and their spend is folded into the
   parent turn's credits. Totals are unaffected — turns with and without
   subagent calls show the same actual/predicted ratio (0.72 vs 0.75), which is
   what shows the spend is included rather than lost.
5. **Prices are hardcoded** from 2026-08. Re-run `calibrate.py` after rate
   changes.

## ccusage integration notes

- **Records must be compact JSON.** ccusage prefilters lines on the literal
  byte sequence `"usage":{` — `json.dumps` default spacing silently drops the
  record with no error, just "No usage data found". Use `separators=(",", ":")`.
- Session id comes from the **filename**; project from the **parent directory**.
  A record's own `sessionId` and `cwd` are ignored.
- `costUSD` overrides computed pricing (except under `--mode calculate`).
- Dedup key is `message.id`, or `(requestId, message.id)` when both exist.
  `kiro-ccusage` uses the stable `executionId`, so re-exporting is idempotent.
- Timestamps must be full RFC3339; date-only strings and epoch ints are dropped.
