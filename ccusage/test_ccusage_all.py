#!/usr/bin/env python3
"""Invariants for ccusage-all. Stdlib unittest -- no dependency to install.

    ./test_ccusage_all.py            # or: python3 -m unittest discover

Every test here exists because something was wrong once. The wiring tests in
particular: three times a correct function sat in this file with nothing calling
it, and every test about the function passed.
"""

import importlib.util
import io
import json
import sys
import sysconfig
import tempfile
import threading
import time
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).with_name("ccusage-all")


def load():
    spec = importlib.util.spec_from_loader("cc", SourceFileLoader("cc", str(SCRIPT)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cc = load()


def token_row(harness="claude", model="claude-opus-5", cost=1.0, mtok=1.0, **tokens):
    """A token-logged row, shaped as the real producers shape one. Built through
    cc.provenance() so the helper cannot drift from the enforced vocabulary."""
    counts = dict.fromkeys(cc.TOKEN_KEYS, 0)
    counts["cacheReadTokens"] = int(mtok * 1e6)
    counts.update(tokens)
    return {"day": "2026-08-01", "harness": harness, "model": model,
            "consumed": mtok, "unit": "Mtok", "rate": cost / mtok if mtok else 0.0,
            "cost": cost, "tokens": counts, "assumed_mix": None, "unmeasured": (),
            "provenance": cc.provenance(consumed=cc.COUNTED, cost="litellm",
                                        mix=cc.MEASURED)}


def credit_row(mix=None, credits=100.0):
    """A Kiro row: metered credits, no token buckets, mix assumed."""
    mix = dict(cc.KIRO_DEFAULT_MIX) if mix is None else mix
    return {"day": "2026-08-01", "harness": "kiro", "model": "claude-opus-5",
            "consumed": credits, "unit": "credits", "rate": cc.KIRO_DEFAULT_RATE,
            "cost": credits * cc.KIRO_DEFAULT_RATE, "tokens": None,
            "assumed_mix": mix, "unmeasured": (),
            "provenance": cc.provenance(consumed=cc.METERED, cost="kiro-credit",
                                        mix=cc.ASSUMED)}


class Provenance(unittest.TestCase):
    """One vocabulary, stated by every producer, read by render.

    Provenance used to be re-inferred at the render layer from four unrelated
    presence checks, so a new row producer could satisfy none of them and still
    render as though everything were measured."""

    def test_vocabulary_is_enforced(self):
        """A typo'd label must not fall through a lookup and read as measured."""
        with self.assertRaises(ValueError):
            cc.provenance(consumed="guessed", cost="litellm", mix=cc.MEASURED)
        with self.assertRaises(ValueError):
            cc.provenance(consumed=cc.COUNTED, cost="litellm", mix="probably")

    def test_a_cost_source_is_mandatory(self):
        with self.assertRaises(ValueError):
            cc.provenance(consumed=cc.COUNTED, cost="", mix=cc.MEASURED)

    def test_every_real_producer_emits_complete_provenance(self):
        """The uniformity guarantee, run over the actual producers: a new one
        cannot be added without provenance and still pass."""
        rows = (cc.kiro_rows(cc.KIRO_DEFAULT_RATE, dict(cc.KIRO_DEFAULT_MIX))
                + cc.l3m_rows(cc.l3m_settings()))
        if not rows:
            self.skipTest("no local Kiro or l3m data to read")
        for row in rows:
            with self.subTest(harness=row["harness"], model=row["model"]):
                self.assertEqual(set(row["provenance"]), {"consumed", "cost", "mix"})
                self.assertIn(row["provenance"]["consumed"], {cc.COUNTED, cc.METERED})
                self.assertIn(row["provenance"]["mix"],
                              {cc.MEASURED, cc.PARTIAL, cc.ASSUMED})
                self.assertTrue(row["provenance"]["cost"])

    def test_every_row_carries_the_keys_render_reads(self):
        rows = (cc.kiro_rows(cc.KIRO_DEFAULT_RATE, dict(cc.KIRO_DEFAULT_MIX))
                + cc.l3m_rows(cc.l3m_settings()))
        if not rows:
            self.skipTest("no local Kiro or l3m data to read")
        for row in rows:
            with self.subTest(harness=row["harness"]):
                for key in ("day", "harness", "model", "consumed", "unit", "rate",
                            "cost", "tokens", "assumed_mix", "unmeasured",
                            "provenance"):
                    self.assertIn(key, row)

    def test_partial_mix_is_distinct_from_fully_measured(self):
        """codex's cache-write is unobservable, not zero, so its rows must not
        claim the provenance of a harness that counted all four buckets."""
        self.assertNotEqual(cc.PARTIAL, cc.MEASURED)

    def test_unpriced_is_a_label_not_a_string_suffix(self):
        """It used to be `priced_by += "!"`, so render parsed a string to learn
        whether a dollar figure was real."""
        self.assertNotIn("!", cc.UNPRICED)


class RowCoherence(unittest.TestCase):
    """validate_rows: labels must agree with the row they describe.

    provenance() only checks each label is in the vocabulary. Both mutations
    below used every label legally and passed the whole suite before this
    existed."""

    def test_real_rows_pass(self):
        rows = (cc.kiro_rows(cc.KIRO_DEFAULT_RATE, dict(cc.KIRO_DEFAULT_MIX))
                + cc.l3m_rows(cc.l3m_settings()))
        if not rows:
            self.skipTest("no local Kiro or l3m data to read")
        cc.validate_rows(rows)

    def test_constructed_rows_pass(self):
        cc.validate_rows([token_row(), credit_row()])

    def test_measured_mix_without_token_buckets_is_rejected(self):
        """Isolated: assumed_mix cleared too, so only the mix/token check can
        fire. With it set, the ASSUMED/assumed_mix check catches this instead and
        the test passes for the wrong reason."""
        row = credit_row()
        row["assumed_mix"] = None
        row["provenance"]["mix"] = cc.MEASURED
        with self.assertRaises(ValueError):
            cc.validate_rows([row])

    def test_counted_claimed_without_buckets_is_rejected(self):
        row = credit_row()
        row["provenance"]["consumed"] = cc.COUNTED
        with self.assertRaises(ValueError):
            cc.validate_rows([row])

    def test_assumed_label_without_an_assumed_mix_is_rejected(self):
        """Isolated on a credit row: a token row labelled ASSUMED trips the
        mix/token check first, so it cannot exercise this one."""
        row = credit_row()
        row["assumed_mix"] = None
        with self.assertRaises(ValueError):
            cc.validate_rows([row])

    def test_assumed_mix_without_the_assumed_label_is_rejected(self):
        row = token_row()
        row["assumed_mix"] = dict(cc.KIRO_DEFAULT_MIX)
        with self.assertRaises(ValueError):
            cc.validate_rows([row])

    def test_partial_label_must_match_the_unmeasured_field(self):
        orphan = token_row()
        orphan["provenance"]["mix"] = cc.PARTIAL
        with self.assertRaises(ValueError):
            cc.validate_rows([orphan])
        unlabelled = token_row()
        unlabelled["unmeasured"] = ("cacheCreationTokens",)
        with self.assertRaises(ValueError):
            cc.validate_rows([unlabelled])

    def test_unmeasured_must_name_real_buckets(self):
        row = token_row()
        row["unmeasured"] = ("notATokenBucket",)
        row["provenance"]["mix"] = cc.PARTIAL
        with self.assertRaises(ValueError):
            cc.validate_rows([row])

    def test_the_error_names_the_offending_row(self):
        row = credit_row()
        row["provenance"]["mix"] = cc.MEASURED
        with self.assertRaises(ValueError) as caught:
            cc.validate_rows([row])
        self.assertIn("kiro/claude-opus-5", str(caught.exception))

    def test_main_actually_calls_it(self):
        """A wiring test. Deleting the validate_rows(rows) call from main leaves
        every test above passing -- the blind spot that hid two earlier bugs."""
        calls = []
        original = cc.validate_rows

        def spy(rows):
            calls.append(len(rows))
            return original(rows)

        cc.validate_rows = spy
        argv, stdout = sys.argv, sys.stdout
        try:
            sys.argv = ["ccusage-all", "--since", "2030-01-01"]
            sys.stdout = io.StringIO()
            cc.main()
        finally:
            cc.validate_rows = original
            sys.argv, sys.stdout = argv, stdout
        self.assertEqual(len(calls), 1, "main must validate rows exactly once")


class UnobservableBuckets(unittest.TestCase):
    """A zero a harness's log cannot distinguish from an absence.

    Codex carries exactly input / cached_input / output / reasoning_output / total
    across all 10,257 token_count events -- no cache-creation field -- while
    gpt-5.6-sol IS billed for cache writes. Its share there is a floor and its
    cost a slight underestimate."""

    def test_only_codex_is_declared_unobservable(self):
        self.assertEqual(cc.UNOBSERVABLE_BUCKETS, {"codex": ("cacheCreationTokens",)})

    def test_codex_log_really_has_no_cache_creation_field(self):
        """Guards the premise: if a future Codex adds the field, CODEX_USAGE_KEYS
        should grow and this should be revisited."""
        self.assertFalse([k for k in cc.CODEX_USAGE_KEYS if "creation" in k])

    def test_gpt_cache_write_is_actually_billed(self):
        """The reason the gap matters: a free tier would make 0% harmless."""
        self.assertGreater(cc.LITELLM_SNAPSHOT["gpt-5.6-sol"][3], 0)
        self.assertGreater(cc.CODEX_LONG_CONTEXT["gpt-5.6-sol"][1][3], 0)


class Rendering(unittest.TestCase):
    def table(self, rows):
        buffer = io.StringIO()
        cc.render(rows, stream=buffer)
        return buffer.getvalue()

    def test_unpriced_model_is_flagged_on_its_own_row(self):
        """A $0 cost because no price table lists the model must be visible, or
        the total silently undercounts."""
        row = token_row(model="mystery-model-9")
        row["provenance"]["cost"] = cc.UNPRICED
        self.assertIn("mystery-model-9 (!)", self.table([row]))

    def test_priced_model_is_not_flagged(self):
        self.assertNotIn("(!)", self.table([token_row()]))

    def test_empty_input_says_so_rather_than_printing_a_header(self):
        self.assertIn("No usage data found", self.table([]))

    def test_render_writes_to_the_current_stdout(self):
        """`stream=sys.stdout` as a default binds whatever stdout was at import,
        so reassigning sys.stdout later would silently have no effect."""
        stdout = sys.stdout
        try:
            sys.stdout = io.StringIO()
            cc.render([token_row()])
            captured = sys.stdout.getvalue()
        finally:
            sys.stdout = stdout
        self.assertIn("Subtotal", captured)


class KiroRate(unittest.TestCase):
    """$/credit = fresh-input rate x an assumed mix factor. No flag bypasses it,
    so KIRO_DEFAULT_MIX is provably what produced every Kiro figure."""

    def test_rate_is_the_fresh_input_rate_times_the_default_mix(self):
        self.assertAlmostEqual(
            cc.KIRO_DEFAULT_RATE,
            cc.KIRO_FRESH_INPUT_RATE * cc.kiro_mix_factor(cc.KIRO_DEFAULT_MIX),
            places=12)

    def test_main_prices_kiro_at_that_rate(self):
        """Wiring: main could resolve a rate some other way and every test above
        would still pass, since they pass the rate in themselves. This runs main
        and reads the rate off the rows it actually produced."""
        seen = []
        original = cc.kiro_rows

        def spy(credit_rate, assumed_mix=None):
            seen.append((credit_rate, assumed_mix))
            return original(credit_rate, assumed_mix)

        cc.kiro_rows = spy
        argv, stdout = sys.argv, sys.stdout
        try:
            sys.argv = ["ccusage-all", "--since", "2030-01-01"]
            sys.stdout = io.StringIO()
            cc.main()
        finally:
            cc.kiro_rows = original
            sys.argv, sys.stdout = argv, stdout
        self.assertEqual(len(seen), 1)
        rate, mix = seen[0]
        self.assertAlmostEqual(rate, cc.KIRO_DEFAULT_RATE, places=12)
        self.assertEqual(mix, cc.KIRO_DEFAULT_MIX)

    def test_the_default_mix_is_deliberately_round(self):
        """It is a guess and must look like one. Claude Code's measured 95.1/4.4
        would read as a measurement while being another harness's measurement."""
        for share in cc.KIRO_DEFAULT_MIX.values():
            self.assertAlmostEqual(share * 100, round(share * 100 / 5) * 5, places=9)

    def test_the_default_mix_keeps_a_margin_below_the_measured_ceiling(self):
        """Measured harnesses span 75.4%-95.6% cache-read (input-side); Claude
        Code is the top. Assuming Kiro is the best cacher present is the claim
        being avoided, and a bound of merely `< 0.956` would admit 0.95."""
        self.assertLessEqual(cc.KIRO_DEFAULT_MIX["cr"], 0.92)
        self.assertGreater(cc.KIRO_DEFAULT_MIX["cr"], 0.754)

    def test_mix_shares_sum_to_one(self):
        self.assertAlmostEqual(sum(cc.KIRO_DEFAULT_MIX.values()), 1.0, places=9)

    def test_cache_write_dominates_the_correction(self):
        """5% cache-write outweighs the 5-point drop in cache-read -- the
        counterintuitive fact the whole mix argument rests on."""
        at_100 = cc.kiro_mix_factor({"cr": 1.00, "cw": 0.00, "in": 0.0})
        at_95 = cc.kiro_mix_factor({"cr": 0.95, "cw": 0.05, "in": 0.0})
        self.assertGreater(at_95, at_100)
        self.assertGreater(0.05 * cc.KIRO_PRICE_RATIO["cw"] / at_95, 0.35)

    def test_credits_are_reported_as_scanned(self):
        """The scan reads ~5% below /usage. That is documented, not corrected:
        scaling every row by one aggregate ratio attributes the miss
        proportionally when its known component is not spread that way."""
        rows = cc.kiro_rows(1.0, dict(cc.KIRO_DEFAULT_MIX))
        if not rows:
            self.skipTest("no local Kiro data to read")
        self.assertEqual({r["rate"] for r in rows}, {1.0})
        for row in rows:
            self.assertAlmostEqual(row["cost"], row["consumed"], places=9)


class RowInvariants(unittest.TestCase):
    def test_consumed_times_rate_equals_cost(self):
        for row in (token_row(cost=2.5, mtok=5.0), token_row(cost=0.0, mtok=1.0),
                    credit_row()):
            with self.subTest(harness=row["harness"], cost=row["cost"]):
                self.assertAlmostEqual(row["consumed"] * row["rate"], row["cost"],
                                       places=9)

    def test_canon_strips_provider_and_region_prefixes(self):
        for name in ("us.anthropic.claude-opus-5", "global.anthropic.claude-opus-5",
                     "openai.claude-opus-5"):
            with self.subTest(name=name):
                self.assertEqual(cc.canon(name), "claude-opus-5")

    def test_cache_read_is_a_tenth_of_input_across_the_price_table(self):
        """Kiro's mix factor (KIRO_PRICE_RATIO cr=0.10) is only defensible
        because this ratio holds. The exceptions are pinned, not skipped, so a
        transcription that changes one of them fails here: Anthropic cut the
        cache-read ratio to 1/20 with Opus 5.5 and 1/40 with Fable 5.1, which
        makes 0.10 an overestimate for the Kiro credits spent on those two.
        OpenAI's GPT-6.1 Sol is 1/20 as well; Kiro has not used it."""
        exceptions = {"deepseek-v4-flash-free": 0.2, "claude-opus-5-5": 0.05,
                      "claude-fable-5-1": 0.025, "gpt-6.1-sol": 0.05}
        for name, (inp, _out, cr, _cw) in cc.LITELLM_SNAPSHOT.items():
            if not inp:
                continue          # a free tier has no ratio
            with self.subTest(model=name):
                self.assertAlmostEqual(cr / inp, exceptions.get(name, 0.1), places=9)

    def test_long_context_pricing_is_dearer_than_base(self):
        for name, (_threshold, long_rates) in cc.CODEX_LONG_CONTEXT.items():
            with self.subTest(model=name):
                self.assertGreater(long_rates[0], cc.LITELLM_SNAPSHOT[name][0])

    def test_long_context_portion_is_repriced_upward(self):
        """OpenAI bills a turn over the threshold entirely at long-context rates.
        token_rows prices everything at base, then swaps the long portion -- if
        that swap is dropped, the cost is silently the base-rate figure."""
        model = "openai.gpt-5.6-sol"
        day = "2026-08-01"
        key = f"{day}\x00{model}"
        tok = [300_000, 1_000, 500_000, 0]          # input over the 272K threshold
        base = cc.token_rows({"codex": ({key: tok}, {})}, False)
        long = cc.token_rows({"codex": ({key: tok}, {key: tok})}, False)
        self.assertGreater(long[0]["cost"], base[0]["cost"] * 1.5)

    def test_short_turns_are_not_repriced(self):
        key = "2026-08-01\x00openai.gpt-5.6-sol"
        tok = [1_000, 100, 5_000, 0]
        rows = cc.token_rows({"codex": ({key: tok}, {})}, False)
        rate = cc.litellm_rates("openai.gpt-5.6-sol", cc.litellm_table(False))
        expected = cc.token_cost_usd(rate, dict(zip(cc.TOKEN_KEYS, tok, strict=True)))
        self.assertAlmostEqual(rows[0]["cost"], expected, places=12)


class PriceTable(unittest.TestCase):
    """The embedded table must list every model this box's token-logged
    harnesses have used, or their rows print `(!)` at $0. `--online` only
    refreshes keys the table already has, so a new model is a table edit."""

    # Model names exactly as the logs spell them: Claude Code bare, Codex with
    # the Bedrock route prefix, opencode's Zen free tier by its own alias.
    LOGGED = ("claude-opus-5", "claude-opus-5-5", "claude-sonnet-5", "claude-opus-4-8",
              "claude-fable-5", "openai.gpt-5.6-sol", "global.openai.gpt-5.6-luna",
              "us.openai.gpt-6-astra", "us.openai.gpt-6.1-sol", "global.openai.gpt-6.1-sol",
              "openai.gpt-5.5", "openai.gpt-5.4", "deepseek-v4-flash-free", "big-pickle")

    def test_every_logged_model_is_priced(self):
        for name in self.LOGGED:
            with self.subTest(model=name):
                self.assertIsNotNone(cc.litellm_rates(name, cc.LITELLM_SNAPSHOT))

    def test_a_sibling_version_does_not_inherit_its_familys_price(self):
        """The longest-prefix rule exists for dated snapshots
        (claude-haiku-4-5-20251001 -> claude-haiku-4-5). claude-opus-5-5 also
        starts with claude-opus-5, and rode that rule to Opus 5's price for a
        week -- 25% over on input and 2.5x over on cache reads."""
        table = cc.LITELLM_SNAPSHOT
        self.assertEqual(cc.litellm_rates("claude-haiku-4-5-20251001", table),
                         table["claude-haiku-4-5"])
        self.assertEqual(cc.litellm_rates("claude-opus-5-5", table), table["claude-opus-5-5"])
        self.assertNotEqual(table["claude-opus-5-5"], table["claude-opus-5"])
        self.assertEqual(cc.litellm_rates("claude-fable-5-1", table), table["claude-fable-5-1"])
        self.assertNotEqual(table["claude-fable-5-1"], table["claude-fable-5"])

    def test_a_free_tier_is_a_price_not_a_gap(self):
        """UNPRICED means no table lists the model. A $0 entry (opencode's Zen
        free tier) is a known price, so its row must not be flagged, while a
        model absent from the table still is -- the test cost==0 alone could
        not tell the two apart."""
        tok = [80_000, 12_000, 1_000_000, 0]
        rows = cc.token_rows({"opencode": ({"2026-06-11\x00big-pickle": tok,
                                            "2026-06-11\x00mystery-model-9": tok}, {})},
                             False)
        by_model = {row["model"]: row for row in rows}
        self.assertEqual(by_model["big-pickle"]["cost"], 0.0)
        self.assertNotEqual(by_model["big-pickle"]["provenance"]["cost"], cc.UNPRICED)
        self.assertEqual(by_model["mystery-model-9"]["provenance"]["cost"], cc.UNPRICED)

    def test_every_openai_model_has_a_long_context_tier(self):
        """OpenAI bills two-stage; a GPT model in the base table with no tier
        entry silently prices its >272K turns at base."""
        gpt = {name for name in cc.LITELLM_SNAPSHOT if name.startswith("gpt-")}
        self.assertEqual(gpt, set(cc.CODEX_LONG_CONTEXT))
        for name, (threshold, _rates) in cc.CODEX_LONG_CONTEXT.items():
            with self.subTest(model=name):
                self.assertEqual(threshold, 272_000)

    def test_long_context_doubles_input_across_the_gpt_family(self):
        """The published tier is 2x on input, cache-read and cache-write, 1.5x
        on output, for every model that has one (gpt-5.5/5.4 carry no
        cache-write price at either tier)."""
        for name, (_threshold, long_rates) in cc.CODEX_LONG_CONTEXT.items():
            base = cc.LITELLM_SNAPSHOT[name]
            with self.subTest(model=name):
                self.assertAlmostEqual(long_rates[0], base[0] * 2, places=9)
                self.assertAlmostEqual(long_rates[1], base[1] * 1.5, places=9)
                self.assertAlmostEqual(long_rates[2], base[2] * 2, places=9)
                self.assertAlmostEqual(long_rates[3], base[3] * 2, places=9)


class Subtotals(unittest.TestCase):
    def test_effective_rate_is_cost_over_consumed(self):
        bucket = cc.harness_subtotals([token_row(harness="h", cost=9.0, mtok=3.0)])["h"]
        self.assertAlmostEqual(bucket["rate"], 3.0, places=9)

    def test_harnesses_do_not_bleed_into_each_other(self):
        agg = cc.harness_subtotals([token_row(harness="a", cost=1.0),
                                    token_row(harness="b", cost=2.0)])
        self.assertAlmostEqual(agg["a"]["cost"], 1.0, places=9)
        self.assertAlmostEqual(agg["b"]["cost"], 2.0, places=9)

    def test_zero_consumed_does_not_divide_by_zero(self):
        row = token_row(harness="h", cost=0.0, mtok=0.0)
        self.assertEqual(cc.harness_subtotals([row])["h"]["rate"], 0.0)


# --- synthetic logs, written the way the harnesses write them ------------------

def jsonl(records):
    """Compact JSON lines. Compact matters: the Claude parser's substring gate
    looks for `"type":"assistant"` with no space after the colon."""
    return b"".join(json.dumps(r, separators=(",", ":")).encode() + b"\n"
                    for r in records)


def kiro_log(turns, day=1):
    """Per turn [(n, model, credits)]: the assistant record naming the model,
    an unrelated record, then the usage_summary carrying the credits -- so a
    cut can fall between a turn's model and its credits."""
    records = []
    for n, model, credits in turns:
        eid, ts = f"exec-{n}", f"2026-10-{day + n % 2:02d}T10:00:00Z"
        records += [
            {"id": f"a{n}", "timestamp": ts, "payload": {
                "type": "assistant", "executionId": eid,
                "reasoningModelId": f"qdev::{model}", "content": "x" * 40}},
            {"id": f"f{n}", "timestamp": ts, "payload": {"type": "user", "content": "y" * 40}},
            {"id": f"s{n}", "timestamp": ts, "payload": {
                "type": "usage_summary", "executionId": eid,
                "promptTurnSummaries": [{"usage": credits, "unit": "credit"}]}},
        ]
    return jsonl(records)


def claude_log(messages):
    """Assistant records [(message id, request id, (in, out, cr, cw), sidechain)],
    each after an unrelated record."""
    records = []
    for n, (mid, req, tok, side) in enumerate(messages):
        records.append({"type": "user", "timestamp": "2026-10-01T09:00:00Z",
                        "message": {"content": "q" * 30}})
        records.append({
            "type": "assistant", "timestamp": f"2026-10-{1 + n % 2:02d}T10:00:00Z",
            "requestId": req, "isSidechain": side,
            "message": {"id": mid, "model": "claude-opus-5", "usage": {
                "input_tokens": tok[0], "output_tokens": tok[1],
                "cache_read_input_tokens": tok[2], "cache_creation_input_tokens": tok[3]}}})
    return jsonl(records)


# A message streamed as three rewrites (the first two partial), an anonymous
# entry, a smaller rewrite that must not win, and a sidechain replay.
CLAUDE_STREAM = [
    ("m1", "r1", (1, 1, 0, 0), False), ("m2", "r2", (2, 2, 20, 1), False),
    ("m1", "r1", (1, 9, 50, 2), False), (None, "r4", (1, 1, 1, 1), False),
    ("m1", "r1", (1, 2, 0, 0), False), ("m5", "r5", (3, 3, 3, 3), True),
    ("m1", "r1", (1, 9, 60, 2), False), ("m5", "r6", (3, 3, 9, 3), True),
]


def codex_usage(inp, cached, out):
    return {"input_tokens": inp, "cached_input_tokens": cached, "output_tokens": out,
            "reasoning_output_tokens": 0, "total_tokens": inp + out}


def codex_log(sid, turns, parent=None, meta_ts="2026-10-01T10:00:00Z"):
    """A rollout file. `turns` is [(timestamp, (input, cached, output))], a
    `None` turn being a model switch. Cumulative totals advance with each turn;
    one repeated event (totals unchanged) must be ignored, and one event carries
    totals only, so its usage is the delta against the turn before it."""
    payload = {"id": sid, "timestamp": meta_ts}
    if parent:
        payload["forked_from_id"] = parent
    records = [{"type": "session_meta", "timestamp": meta_ts, "payload": payload},
               {"type": "turn_context", "payload": {"model": "gpt-5.6-sol"}}]
    total = [0, 0, 0]
    for index, turn in enumerate(turns):
        if turn is None:
            records.append({"type": "turn_context", "payload": {"model": "gpt-5.6-luna"}})
            continue
        ts, (inp, cached, out) = turn
        total = [total[0] + inp, total[1] + cached, total[2] + out]
        info = {"total_token_usage": codex_usage(*total)}
        if index % 3 != 2:
            info["last_token_usage"] = codex_usage(inp, cached, out)
        event = {"type": "event_msg", "timestamp": ts,
                 "payload": {"type": "token_count", "info": info}}
        records.append(event)
        if index == 1:
            records.append(event)
    return jsonl(records)


def codex_turns(start_minute, count, scale=1):
    return [(f"2026-10-01T10:{start_minute + i:02d}:00Z",
             ((300_000 if i == 2 else 1_000 * (i + 1)) * scale, 500 * i, 50 + i))
            for i in range(count)]


def claude_record(path, prev=None):
    """claude_file_entries shaped as the cache record it is stored in."""
    entries, mark = cc.claude_file_entries(path, prev)
    return {"entries": entries, **mark}


class Resume(unittest.TestCase):
    """A grown log is read from the byte the last run stopped at.

    The cache now carries each parser's fold state across runs, so a field
    missing from that state is wrong only for a turn that straddles two runs --
    a bug no single-run test can see. Equivalence is therefore checked against
    the one thing it must equal: a cold parse of the final file, however its
    growth was cut, mid-line included."""

    PARSERS = {
        "kiro": (lambda: cc.kiro_parse_file,
                 kiro_log([(n, "claude-opus-5" if n % 2 else "gpt-5.6-sol", 1.25 * n)
                           for n in range(1, 6)])),
        "claude": (lambda: claude_record, claude_log(CLAUDE_STREAM)),
        "codex": (lambda: cc.codex_parse_file,
                  codex_log("s1", codex_turns(0, 3) + [None] + codex_turns(5, 3))),
    }

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "log.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def parse(self, parser, data, prev=None):
        """Write `data`, parse it with `prev` carried the way the cache carries
        it -- through a JSON round trip."""
        self.path.write_bytes(data)
        if prev is not None:
            prev = json.loads(json.dumps(prev))
        return parser(str(self.path), prev)

    def cuts(self, data):
        """Every kind of place a run can land: on a line's newline (the record
        complete but unterminated), just after it, one byte into the next line,
        and mid-line."""
        ends = [i for i, byte in enumerate(data) if byte == 0x0A]
        points = {0, len(data)}
        for start, end in zip([-1, *ends], ends):
            points |= {end, end + 1, end + 2, (start + end) // 2}
        return sorted(p for p in points if 0 <= p <= len(data))

    def test_any_single_cut_resumes_to_the_cold_result(self):
        for name, (get, data) in self.PARSERS.items():
            parser = get()
            cold = self.parse(parser, data)
            for cut in self.cuts(data):
                with self.subTest(parser=name, cut=cut):
                    first = self.parse(parser, data[:cut])
                    self.assertEqual(self.parse(parser, data, first), cold)

    def test_many_small_appends_resume_to_the_cold_result(self):
        for name, (get, data) in self.PARSERS.items():
            parser = get()
            cold = self.parse(parser, data)
            for step in (5, 17, 101):
                with self.subTest(parser=name, step=step):
                    record = None
                    for end in [*range(step, len(data), step), len(data)]:
                        record = self.parse(parser, data[:end], record)
                    self.assertEqual(record, cold)

    def test_the_resume_actually_skips_the_parsed_prefix(self):
        """Wiring: every test above would also pass if resume_offset always
        answered 0 and each run re-parsed from the start -- the slow path this
        exists to remove."""
        for name, (get, data) in self.PARSERS.items():
            with self.subTest(parser=name):
                parser = get()
                first = self.parse(parser, data[:len(data) // 2])
                self.path.write_bytes(data)
                self.assertGreater(cc.resume_offset(str(self.path), first), 0)
                self.assertEqual(cc.resume_offset(str(self.path), first), first["offset"])

    def test_a_rewritten_log_is_parsed_from_scratch(self):
        for name, (get, data) in self.PARSERS.items():
            parser = get()
            first = self.parse(parser, data[:len(data) // 2])
            # Same length as before and then grown, but different bytes.
            other = data[:len(data) // 2].replace(b"10:00", b"11:00") + data[len(data) // 2:]
            with self.subTest(parser=name, change="rewritten"):
                self.assertEqual(self.parse(parser, other, first), self.parse(parser, other))
            with self.subTest(parser=name, change="truncated"):
                short = data[:len(data) // 4]
                self.assertEqual(self.parse(parser, short, first), self.parse(parser, short))

    def test_a_record_caught_mid_write_resumes_from_its_start(self):
        """Checkpointing past the unfinished line would skip the rest of it next
        run; dropping the checkpoint instead would re-read a live log whole every
        time a run happened to land mid-write."""
        for name, (get, data) in self.PARSERS.items():
            with self.subTest(parser=name):
                last_start = data.rfind(b"\n", 0, len(data) - 1) + 1
                self.assertEqual(self.parse(get(), data[:-3])["offset"], last_start)

    def test_a_complete_record_missing_its_newline_still_counts(self):
        """The one unterminated line that parses: counted, as a cold read of the
        same bytes counts it, but never checkpointed past."""
        def content(record):
            return {k: v for k, v in record.items() if k not in ("offset", "tail")}
        for name, (get, data) in self.PARSERS.items():
            with self.subTest(parser=name):
                record = self.parse(get(), data[:-1])
                self.assertNotIn("offset", record)
                self.assertEqual(content(record), content(self.parse(get(), data)))


class IncrementalScanners(unittest.TestCase):
    """The scanners themselves: a run on a cache built from shorter logs must
    equal a run on a fresh cache, across the cross-file rules (Kiro's
    first-seen executionId, Claude's per-dir dedup, Codex fork replay)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_scanner(self, scanner, files, cut):
        """Write each file cut at `cut` of its length (mid-line), scan, write
        them whole, scan again on the same cache. Returns (warm, cold, offsets)
        where cold is the whole files scanned on a fresh cache and offsets the
        resume points the warm scan used."""
        for path, data in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data[:int(len(data) * cut)])
        offsets = []
        real = cc.resume_offset

        def spy(path, prev):
            offsets.append(real(path, prev))
            return offsets[-1]

        with mock.patch.object(cc, "CACHE_DIR", self.root / "cache-warm"):
            scanner()
            for path, data in files.items():
                path.write_bytes(data)
            with mock.patch.object(cc, "resume_offset", spy):
                warm = scanner()
        with mock.patch.object(cc, "CACHE_DIR", self.root / "cache-cold"):
            cold = scanner()
        return warm, cold, offsets

    def check(self, scanner, files, normalize):
        for cut in (0.3, 0.55, 0.8):
            with self.subTest(cut=cut):
                for sub in ("cache-warm", "cache-cold"):
                    for stale in (self.root / sub).glob("*"):
                        stale.unlink()
                warm, cold, offsets = self.run_scanner(scanner, files, cut)
                self.assertEqual(normalize(warm), normalize(cold))
                self.assertTrue(any(offsets), "the warm scan never resumed")

    def test_kiro(self):
        sessions = self.root / "kiro"
        first = sessions / "ws1" / "sess_a"
        second = sessions / "ws2" / "sess_b"
        files = {
            first / "messages.jsonl": kiro_log([(n, "claude-opus-5", 1.5) for n in range(1, 7)]),
            # exec-3 again, on another day: counted once, where first seen.
            second / "messages.jsonl": kiro_log([(n, "gpt-5.6-sol", 0.75) for n in range(3, 9)],
                                                day=5),
        }
        second.mkdir(parents=True)
        (second / "session.json").write_text('{"modelId": "claude-sonnet-5"}')
        with mock.patch.object(cc, "KIRO_SESSIONS", sessions):
            self.check(lambda: cc.kiro_rows(1.0, dict(cc.KIRO_DEFAULT_MIX)), files,
                       lambda rows: sorted((r["day"], r["model"], r["consumed"]) for r in rows))

    def test_claude(self):
        project = self.root / "claude" / "projects" / "-p1"
        resumed = CLAUDE_STREAM[:5] + [("m7", "r7", (5, 5, 5, 5), False)]
        files = {
            project / "s1.jsonl": claude_log(CLAUDE_STREAM),
            project / "s2.jsonl": claude_log(resumed),            # a resume's copy
            project / "s1" / "subagents" / "agent-x.jsonl": claude_log(
                [("m5", "r9", (3, 3, 30, 3), True), ("m8", "r8", (1, 2, 3, 4), True)]),
            self.root / "claude" / "projects" / "-p2" / "s3.jsonl": claude_log(CLAUDE_STREAM[2:]),
        }
        with mock.patch.object(cc, "CLAUDE_PROJECTS", [self.root / "claude" / "projects"]):
            self.check(cc.claude_sums, files, dict)

    def test_codex(self):
        sessions = self.root / "codex" / "sessions" / "2026" / "10" / "01"
        parent_turns = codex_turns(0, 4)
        child_turns = ([(f"2026-10-01T11:00:0{i}Z", usage) for i, (_, usage) in
                        enumerate(parent_turns[:2])] + codex_turns(20, 4, scale=2))
        files = {
            sessions / "rollout-a.jsonl": codex_log("p", parent_turns + codex_turns(30, 3)),
            sessions / "rollout-b.jsonl": codex_log("c", child_turns, parent="p",
                                                    meta_ts="2026-10-01T10:01:30Z"),
        }
        with mock.patch.object(cc, "CODEX_HOME", self.root / "codex"):
            self.check(cc.codex_sums, files,
                       lambda result: tuple(dict(part) for part in result))

    def test_codex_sums_are_not_reused_across_a_threshold_change(self):
        """The one input to the stored Codex sums that is code, not log: which
        turns count as long-context. Changing a threshold with no log touched
        must still move the long-context split."""
        sessions = self.root / "codex" / "sessions"
        sessions.mkdir(parents=True)
        (sessions / "rollout-a.jsonl").write_bytes(codex_log("p", codex_turns(0, 4)))
        table = dict(cc.CODEX_LONG_CONTEXT)
        table["gpt-5.6-sol"] = (1_500, table["gpt-5.6-sol"][1])
        try:
            with mock.patch.object(cc, "CODEX_HOME", self.root / "codex"), \
                 mock.patch.object(cc, "CACHE_DIR", self.root / "cache"):
                _, before = cc.codex_sums()
                cc.codex_long_rates.cache_clear()
                with mock.patch.object(cc, "CODEX_LONG_CONTEXT", table):
                    _, after = cc.codex_sums()
                    with mock.patch.object(cc, "CACHE_DIR", self.root / "fresh"):
                        _, fresh = cc.codex_sums()
        finally:
            cc.codex_long_rates.cache_clear()
        self.assertNotEqual(dict(after), dict(before))
        self.assertEqual(dict(after), dict(fresh))


class Parallel(unittest.TestCase):
    def test_results_come_back_in_job_order(self):
        def slow_square(n):
            time.sleep(0.002 * (n % 4))
            return n * n
        self.assertEqual(cc.parallel(slow_square, [(n,) for n in range(40)]),
                         [n * n for n in range(40)])

    def test_a_failing_job_raises_in_the_caller(self):
        """Not swallowed into a missing result: a scanner that loses one file's
        parse would otherwise report a silently smaller total."""
        def boom(n):
            if n == 3:
                raise ValueError("job 3")
            return n
        with self.assertRaisesRegex(ValueError, "job 3"):
            cc.parallel(boom, [(n,) for n in range(8)])

    def test_a_single_job_runs_inline(self):
        self.assertEqual(cc.parallel(lambda: threading.get_ident(), [()]),
                         [threading.get_ident()])

    def test_the_gil_stays_off_on_a_free_threaded_build(self):
        """parallel() only parallelizes JSON work on a free-threaded build, and
        one stdlib extension without free-threading support would silently turn
        the GIL back on for the whole process."""
        if not sysconfig.get_config_var("Py_GIL_DISABLED"):
            self.skipTest("not a free-threaded build")
        self.assertFalse(sys._is_gil_enabled())


if __name__ == "__main__":
    unittest.main(verbosity=2)
