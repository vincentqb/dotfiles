# ccusage — working state

Living plan file. Re-read this after any compaction, and check current work
against the **Goal** below rather than against a conversation summary.

## Goal

One trustworthy table of what this box spent on LLM harnesses, per day, per
harness, per model — where every number traces to a log record or a named
assumption.

Origin: "the cost varies a lot in what's picked up across harness for the same
model — what's a good way to unify our estimate? use authoritative sources?"

## Definition of done

- `ccusage-all` runs clean; `Consumed × Rate == Cost` on every row.
- Every reported number is either measured from a log or labelled as assumed.
- `python3 -m unittest discover` green, enforced by the pre-commit hook.
- No column or flag whose value cannot be explained in one sentence.

## Decided — do not relitigate

1. **The cross-harness rate spread is token mix, not a pricing disagreement.**
   Measured: switching price tables moved the grand total by **$0.0033**.
2. **Do not "unify" the blended rate.** It is a mix statistic and carries real
   information about caching behaviour.
3. **Cache mix is a HARNESS property, not per-model.** The same `claude-opus-5`
   measures 95.3% cache-read under Claude Code and 87.1% under l3m; four models
   under Claude Code all land within 1.8 points. So there is no per-model mix to
   assign.
4. **Kiro's assumed mix is 90% cache-read / 5% cache-write / 5% fresh input**,
   deliberately round because it is a guess. Rate = `$0.7468 × 0.2025 =
   $0.1512/credit`. Lives in `KIRO_DEFAULT_MIX`; no flag bypasses it.
5. **No credit-completeness correction.** The scan reads ~5% below `/usage`; that
   is documented, not corrected. A single aggregate ratio smeared per-row
   attributes the miss proportionally when its known component is not.
6. **Price all token rows linearly from the LiteLLM table.** l3m's
   round-to-nearest-cent is how l3m charges, not how anyone else bills.
7. **CLI is four flags**: `--since --until --offline --online`.
8. **Table is** Date | Day Total | Harness | Model | Consumed | Unit | Rate | Cost.
9. **Keep the provenance vocabulary and `validate_rows`.** Every row states how
   its numbers are known; labels are checked against the row on every run.
10. **Keep comments that document external systems**; the file's own history was
    removed. Reverse-engineering is not clutter.
11. **Tests are stdlib unittest**, verified by mutation, gated by pre-commit on
    `^ccusage/`.

## Findings — scope-conditioned, not decisions

- `calibrate.py` had `gpt-5.6-*` context windows at 272,000 against an
  authoritative 1,000,000. **GPT needs no separate calibration**: the apparent
  3.43× family gap became 0.93× once the window was right. 272,000 is OpenAI's
  long-context *pricing* boundary, correct where it lives in `ccusage-all`.
- Kiro's `contextUsage` samples are **cumulative snapshots**, so summing them is
  invalid for multi-request turns (median `sum/max` = 15.85×).
- `/usage` does **not** clamp at the plan cap. Scan reads 5.1% low
  (63,061.16 vs 66,425.17, 2026-08-27). ~0.4 of those points is v1/v2 turns; the
  rest unexplained.
- Codex logs **no cache-creation field** in any of 10,257 usage events, while
  `gpt-5.6-sol` is billed for cache writes. Its cache-write is a floor and its
  cost a slight underestimate.
- l3m self-prices from its own `cents`, running **~12% above list**. Unexplained;
  leading candidate is per-call cent rounding. Not fixable by any price change here.
- l3m records **no timing data**. Its `value_per_session` hourly-rate model is a
  design doc (`budget-and-attention.md`), unimplemented.
- Claude Code work/idle split: **752 h** union agent-work over a 70-day span,
  **3.42×** average session concurrency.
- `value_per_session` is not computable: `user_time_saved` is a counterfactual, not
  an instrumentation gap. The computable half is a **break-even bar** (~574 h saved
  at $200/hr and a 15-min switch threshold), and it swings 100–898 h on the
  threshold alone.

## Open

- **Duration columns** (workload + wall). Raised but unresolved: wall time is a
  union, so it is not attributable per row — it belongs on Subtotal/TOTAL only.
  Claude would need every record type read, losing the substring gate that keeps
  the 5,478-file scan fast, plus an outlier guard for resumed sessions. Awaiting a
  call on full-five-harness vs kiro/codex/opencode only.
- Whether to strip the remaining external-system comments (I declined once).
- l3m's 12%-above-list gap.
- `$0.0557/credit` (output-dominated) sits below the band floor `$0.0647`;
  derived from an underived `base * 5 / 67`. No longer reachable from the CLI.
- The mix factor is unvalidated and `calibrate.py` step 4 shares its structure, so
  the cross-check cannot detect a mix error.

## Next step

Decide the duration-column question, or explicitly park it.

## Drift note (2026-08-27)

The last two rounds moved to agent-hours and l3m's hourly-rate economics. Those
are adjacent to the goal above, not in it — the goal is cost attribution, and no
duration column has been agreed. Parking them is a legitimate outcome.
