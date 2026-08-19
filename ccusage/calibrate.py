#!/usr/bin/env python3
"""Re-derive the credits->tokens->dollars calibration from local Kiro data.

Everything `ccusage-all` relies on for Kiro is measured, not assumed, and this script
reproduces each measurement so the constants can be re-checked when Kiro changes
its rates. Run it and compare against FINDINGS.md.

  ./calibrate.py            # all checks
  ./calibrate.py --json     # machine-readable

The five steps:

  1. CREDITS PER TOKEN. Kiro logs a per-request context-fill percentage next to
     each turn's credits. On a turn with exactly one request the billed token
     count is therefore known, and credits/token solves directly. Uses the
     SQLite store, which keeps the last turn of each conversation with its
     `context_usage_percentage` intact.

  2. HELD-OUT CHECK. Predict credits for turns of a model that step 1 never
     saw, using only that model's rate multiplier.

  3. MULTIPLIER -> BEDROCK PRICE. Kiro's per-model `rate_multiplier` is
     compared against published Bedrock input prices. Because credits already
     scale by the multiplier, it cancels: one model-independent USD-per-credit
     rate follows.

  4. INDEPENDENT MAGNITUDE CHECK. Price the measured context tokens straight at
     Bedrock cache-read rates, never touching credits, and compare totals.

  5. UNCERTAINTY BAND. Compose the credits-per-token spread with the anchor
     spread to get the asymmetric band `ccusage-all` prints beside the Kiro
     subtotal, then check that step 4's independent estimate falls inside it.
"""

import argparse
import collections
import glob
import json
import pathlib
import sqlite3
import statistics
import sys

KIRO = pathlib.Path("~/.kiro").expanduser()
DB = pathlib.Path("~/.local/share/kiro-cli/data.sqlite3").expanduser()

# From `kiro-cli chat --list-models --format json` (rate_multiplier field).
MULTIPLIER = {
    "claude-opus-5": 2.2, "claude-opus-4.8": 2.2, "claude-opus-4.7": 2.2,
    "claude-opus-4.6": 2.2, "claude-opus-4.5": 2.2, "claude-sonnet-5": 1.3,
    "claude-sonnet-4.6": 1.3, "claude-sonnet-4.5": 1.3, "claude-sonnet-4": 1.3,
    "claude-fable-5": 4.4, "claude-haiku-4.5": 0.4, "gpt-5.6-sol": 2.4,
    "gpt-5.6-terra": 1.0, "gpt-5.6-luna": 0.1, "glm-5": 0.5,
    "deepseek-3.2": 0.25, "minimax-m2.5": 0.25, "minimax-m2.1": 0.15,
    "qwen3-coder-next": 0.05, "agi-nova-beta-1m": 0.01, "auto": 1.0,
}

CONTEXT_WINDOW = {
    "gpt-5.6-sol": 272_000, "gpt-5.6-terra": 272_000, "gpt-5.6-luna": 272_000,
    "deepseek-3.2": 164_000, "minimax-m2.5": 196_000, "minimax-m2.1": 196_000,
    "glm-5": 200_000, "claude-haiku-4.5": 200_000, "claude-opus-4.5": 200_000,
    "claude-sonnet-4.5": 200_000, "claude-sonnet-4": 200_000,
}
DEFAULT_WINDOW = 1_000_000

# Published Bedrock list prices, $/Mtok input. Only models whose price is public
# AND that have a Kiro multiplier — used to anchor multipliers to dollars.
BEDROCK_INPUT = {"claude-sonnet-4.5": 3.0, "claude-opus-4.5": 5.0, "claude-haiku-4.5": 1.0}

# Cache reads bill at ~1/10 of fresh input across the Claude family.
CACHE_READ_DISCOUNT = 0.1


def window(model):
    return CONTEXT_WINDOW.get(model, DEFAULT_WINDOW)


def single_request_turns():
    """Turns with one request, where tokens are directly measurable.

    The SQLite store holds one `history` entry per conversation, each with the
    context percentage of that request and the turn's total credits.
    """
    if not DB.is_file():
        return []
    out = []
    connection = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        rows = connection.execute("select value from conversations_v2").fetchall()
    except sqlite3.DatabaseError:
        return []
    finally:
        connection.close()

    for (value,) in rows:
        try:
            record = json.loads(value)
        except json.JSONDecodeError:
            continue
        usage = (record.get("user_turn_metadata") or {}).get("usage_info") or []
        credits = sum(entry.get("value", 0) for entry in usage)
        history = record.get("history") or []
        # One credit figure covers the turn, so only a single-request turn lets
        # us attribute it to a known token count.
        if credits <= 0 or len(history) != 1:
            continue
        metadata = history[0].get("request_metadata") or {}
        percentage = metadata.get("context_usage_percentage")
        model = metadata.get("model_id")
        if percentage is None or model not in MULTIPLIER:
            continue
        out.append((model, percentage, credits, percentage / 100 * window(model)))
    return out


def v3_turns():
    """Per-turn credits from v3 session logs, with model and context samples.

    Credits land on a `usage_summary` record; the model that spent them is named
    only on `assistant` records sharing the executionId.
    """
    out = []
    for path in glob.glob(str(KIRO / "sessions/*/sess_*/messages.jsonl")):
        context = collections.defaultdict(list)
        models, summaries = {}, []
        with open(path) as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = record.get("payload") or {}
                execution_id = payload.get("executionId") or record.get("id")
                kind = payload.get("type")
                if kind == "session_metadata" and payload.get("key") == "contextUsage":
                    context[execution_id].append(payload["value"]["usagePercentage"])
                elif kind == "assistant" and payload.get("reasoningModelId"):
                    models.setdefault(execution_id, payload["reasoningModelId"].rpartition("::")[2])
                elif kind == "usage_summary":
                    credits = sum(
                        summary.get("usage", 0)
                        for summary in payload.get("promptTurnSummaries") or []
                        if str(summary.get("unit", "")).lower().startswith("credit")
                    )
                    if credits > 0:
                        summaries.append((execution_id, credits, len(payload.get("requestIds") or [])))
        for execution_id, credits, requests in summaries:
            model = models.get(execution_id)
            samples = context.get(execution_id, [])
            out.append((model, credits, samples, requests))
    return out


def step1_credits_per_token(report):
    turns = single_request_turns()
    rows = []
    for model, percentage, credits, tokens in turns:
        rows.append((model, percentage, credits, tokens, credits / tokens / MULTIPLIER[model]))

    print("1. CREDITS PER TOKEN (single-request turns; tokens are measured)")
    if not rows:
        print("   no usable turns found — cannot calibrate\n")
        return None
    print(f"   {'model':18s} {'ctx%':>8s} {'credits':>10s} {'tokens':>9s} {'k':>13s}")
    for model, percentage, credits, tokens, k in sorted(rows, key=lambda r: r[0]):
        print(f"   {model:18s} {percentage:8.3f} {credits:10.4f} {tokens:9.0f} {k * 1e6:11.4f}e-6")

    ks = sorted(row[4] for row in rows)
    # The sample is BIMODAL: at identical context percentages some turns cost
    # ~1.8x others (e.g. 25.336% -> either 3.5145 or 1.8605 credits). The driver
    # is not in any recorded field — model, tool use, meta tags and response
    # size are identical across both modes — so it is most likely thinking or
    # output tokens, which are billed but never reported. The mean sits between
    # the modes and matches neither, so use the MEDIAN: it lands on the upper,
    # denser mode, which is the one that governs ordinary turns.
    k = statistics.median(ks)
    upper = [value for value in ks if value >= 2.5e-6]
    lower = [value for value in ks if value < 2.5e-6]
    models = sorted({row[0] for row in rows})
    print(f"\n   k = {k * 1e6:.4f}e-6 credits per token at multiplier 1.0 (median)")
    print(f"   n = {len(ks)} turns over {len(models)} models ({', '.join(models)})")
    print(f"   p10 = {ks[len(ks) // 10] * 1e6:.3f}e-6, p90 = {ks[9 * len(ks) // 10] * 1e6:.3f}e-6")
    if lower and upper:
        cv = statistics.stdev(upper) / statistics.mean(upper)
        print(f"   BIMODAL: upper mode n={len(upper)} (CV {cv:.3f}), lower mode n={len(lower)}, "
              f"{statistics.median(upper) / statistics.median(lower):.2f}x apart")
        print("   -> the gap is unexplained by any logged field; likely unreported thinking/output tokens")
    print(f"   => 1 credit @ 1.0x = {1 / k:,.0f} cached-input tokens\n")
    report["credits_per_token_at_1x"] = k
    report["step1"] = {
        "n": len(ks), "models": models, "p10": ks[len(ks) // 10], "p90": ks[9 * len(ks) // 10],
        "upper_mode_n": len(upper), "lower_mode_n": len(lower),
    }
    return ks


def step2_holdout(k, report, fitted_models):
    print("2. HELD-OUT CHECK (models absent from step 1)")
    checks = []
    for model, credits, samples, requests in v3_turns():
        # Context is sampled per request; if the counts disagree the token total
        # is incomplete and the turn cannot test the constant.
        if not model or model in fitted_models or not samples or len(samples) != requests or requests == 0:
            continue
        tokens = sum(sample / 100 * window(model) for sample in samples)
        predicted = tokens * k * MULTIPLIER.get(model, 1.0)
        if predicted > 0:
            checks.append((model, requests, tokens, credits, predicted))

    if not checks:
        print("   no held-out turns available\n")
        return
    print(f"   {'model':18s} {'reqs':>5s} {'tokens':>12s} {'actual':>10s} {'predicted':>10s} {'error':>8s}")
    for model, requests, tokens, credits, predicted in sorted(checks, key=lambda r: -r[2]):
        print(f"   {model:18s} {requests:5d} {tokens:12.0f} {credits:10.3f} {predicted:10.3f} {(credits / predicted - 1) * 100:+7.1f}%")
    errors = [abs(credits / predicted - 1) for _, _, _, credits, predicted in checks]
    print(f"\n   median absolute error = {statistics.median(errors) * 100:.1f}% over {len(checks)} turns\n")
    report["step2"] = {"n": len(checks), "median_abs_error": statistics.median(errors)}


def step3_dollars(k, report):
    print("3. MULTIPLIER -> BEDROCK PRICE (anchors credits to dollars)")
    anchors = {m: MULTIPLIER[m] / price for m, price in BEDROCK_INPUT.items() if m in MULTIPLIER}
    for model, ratio in sorted(anchors.items()):
        print(f"   {model:20s} {MULTIPLIER[model]:4.2f}x / ${BEDROCK_INPUT[model]:.2f} per Mtok = {ratio:.4f}")
    anchor = statistics.mean(anchors.values())
    spread = (max(anchors.values()) - min(anchors.values())) / 2 / anchor
    print(f"\n   mean anchor = {anchor:.4f} multiplier units per $/Mtok (spread +/-{spread * 100:.1f}%)")

    # $/token = multiplier/anchor/1e6; credits/token = k*multiplier. The
    # multiplier cancels, so $/credit is model-independent.
    base = 1 / (anchor * 1e6 * k)
    cache_read = base * CACHE_READ_DISCOUNT
    print(f"   $/credit, cache-read-dominated  = ${cache_read:.4f}")
    print(f"   $/credit, output-dominated      = ${base * 5 / 67:.4f}")
    print(f"   => model-independent: the multiplier cancels\n")
    report["usd_per_credit_cache_read"] = cache_read
    report["usd_per_credit_output"] = base * 5 / 67
    return cache_read


def step4_cross_check(usd_per_credit, report):
    print("4. INDEPENDENT MAGNITUDE CHECK (prices tokens directly, ignores credits)")
    credit_total = 0.0
    direct_total = 0.0
    for model, credits, samples, requests in v3_turns():
        credit_total += credits
        if not model or not samples:
            continue
        tokens = sum(sample / 100 * window(model) for sample in samples)
        # Bedrock input price implied by the multiplier, then the cache discount.
        implied_input = MULTIPLIER.get(model, 1.0) / statistics.mean(
            MULTIPLIER[m] / p for m, p in BEDROCK_INPUT.items() if m in MULTIPLIER
        )
        direct_total += tokens / 1e6 * implied_input * CACHE_READ_DISCOUNT

    via_credits = credit_total * usd_per_credit
    print(f"   via credits x ${usd_per_credit:.4f}      = ${via_credits:,.2f}")
    print(f"   via measured tokens x Bedrock = ${direct_total:,.2f}")
    if direct_total > 0:
        disagreement = abs(via_credits / direct_total - 1)
        print(f"   two independent routes disagree by {disagreement * 100:.0f}%\n")
        report["cross_check_disagreement"] = disagreement
    report["total_credits"] = credit_total
    report["total_usd_estimate"] = via_credits
    return via_credits, direct_total


def step5_band(ks, report, via_credits, direct_total):
    """Derive the uncertainty band that ccusage-all prints beside the Kiro subtotal."""
    print("5. UNCERTAINTY BAND (printed next to every cost figure)")
    anchors = [MULTIPLIER[m] / price for m, price in BEDROCK_INPUT.items() if m in MULTIPLIER]
    anchor = statistics.mean(anchors)
    spread = (max(anchors) - min(anchors)) / 2 / anchor

    def usd(k, anchor_value):
        return CACHE_READ_DISCOUNT / (anchor_value * 1e6 * k)

    # $/credit moves inversely with k, so the extremes cross: highest k with the
    # highest anchor gives the cheapest rate. Both error sources compose, but the
    # input/output mix is not added on top -- unreported output tokens are the
    # likely cause of the k spread, so that would double-count one phenomenon.
    point = usd(statistics.median(ks), anchor)
    low = usd(max(ks), anchor * (1 + spread))
    high = usd(ks[len(ks) // 10], anchor * (1 - spread))
    print(f"   credits-per-token p10..max = {ks[len(ks) // 10] * 1e6:.3f}e-6 .. {max(ks) * 1e6:.3f}e-6 (dominant)")
    print(f"   anchor spread              = +/-{spread * 100:.1f}% (secondary)")
    print(f"   $/credit  low ${low:.4f}  point ${point:.4f}  high ${high:.4f}")
    print(f"   => band {(low / point - 1) * 100:+.0f}%/{(high / point - 1) * 100:+.0f}%, "
          f"printed as e.g. ${via_credits:,.0f} "
          f"[{via_credits * low / point:,.0f}, {via_credits * high / point:,.0f}]")
    if direct_total > 0:
        contained = low / point <= direct_total / via_credits <= high / point
        print(f"   step 4's independent estimate falls inside the band: {contained}\n")
        report["band_contains_cross_check"] = contained
    report["usd_per_credit_low"] = low
    report["usd_per_credit_high"] = high
    report["cost_band"] = [low / point, high / point]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="emit the derived constants as JSON")
    args = parser.parse_args()

    report = {}
    buffer = sys.stdout
    if args.json:
        sys.stdout = open("/dev/null", "w")

    ks = step1_credits_per_token(report)
    if ks is None:
        sys.stdout = buffer
        sys.exit("calibration needs at least one single-request turn in the SQLite store")
    k = report["credits_per_token_at_1x"]
    step2_holdout(k, report, set(report["step1"]["models"]))
    usd = step3_dollars(k, report)
    via_credits, direct_total = step4_cross_check(usd, report)
    step5_band(ks, report, via_credits, direct_total)

    if args.json:
        sys.stdout = buffer
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
