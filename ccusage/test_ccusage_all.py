#!/usr/bin/env python3
"""Invariants for ccusage-all. Stdlib unittest -- no dependency to install.

    ./test_ccusage_all.py            # or: python3 -m unittest discover

Every test here exists because something was wrong once. The wiring tests in
particular: three times a correct function sat in this file with nothing calling
it, and every test about the function passed.
"""

import importlib.util
import io
import sys
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

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
        """Kiro's mix factor is only defensible because this ratio holds."""
        for name, (inp, _out, cr, _cw) in cc.LITELLM_SNAPSHOT.items():
            if name.startswith("deepseek"):
                continue          # the lone exception, at a fifth
            with self.subTest(model=name):
                self.assertAlmostEqual(cr / inp, 0.1, places=9)

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
