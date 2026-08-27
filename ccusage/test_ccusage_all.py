#!/usr/bin/env python3
"""Invariants for ccusage-all. Stdlib unittest -- no dependency to install.

    ./test_ccusage_all.py            # or: python3 -m unittest discover

Every test here exists because something was wrong once. The propagation tests
in particular: two Std/Eff bugs shipped and survived several readings of the
table, because a plausible-looking number in a derived column is invisible.
A wrong number that renders neatly needs a test, not a closer look.
"""

import argparse
import importlib.util
import io
import sys
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

SCRIPT = Path(__file__).with_name("ccusage-all")


def load():
    """Import ccusage-all despite it having no .py suffix."""
    spec = importlib.util.spec_from_loader("cc", SourceFileLoader("cc", str(SCRIPT)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cc = load()


def token_row(harness="claude", model="claude-opus-5", cost=1.0, mtok=1.0,
              **tokens):
    """A token-logged row, shaped exactly as the real producers shape one.

    Built through cc.provenance() rather than a literal dict so the helper cannot
    drift from the vocabulary the production code enforces."""
    counts = {"inputTokens": 0, "outputTokens": 0,
              "cacheReadTokens": int(mtok * 1e6), "cacheCreationTokens": 0}
    counts.update(tokens)
    row = {"day": "2026-08-01", "harness": harness, "model": model,
           "consumed": mtok, "unit": "Mtok", "rate": cost / mtok if mtok else 0.0,
           "cost": cost, "tokens": counts, "assumed_mix": None,
           "unmeasured": (),
           "provenance": cc.provenance(consumed=cc.COUNTED, cost="l3m",
                                       mix=cc.MEASURED)}
    return row


def credit_row(mix=None, rate=None, cost=7.47, credits=100.0):
    """A Kiro row: metered credits, no token buckets, mix assumed or absent."""
    rate = cc.KIRO_DEFAULT_RATE if rate is None else rate
    return {"day": "2026-08-01", "harness": "kiro", "model": "claude-opus-5",
            "consumed": credits, "unit": "credits", "rate": rate, "cost": cost,
            "tokens": None, "assumed_mix": mix, "unmeasured": (),
            "provenance": cc.provenance(
                consumed=cc.METERED, cost="kiro-credit",
                mix=cc.ASSUMED if mix else cc.NO_MIX)}


class Provenance(unittest.TestCase):
    """One vocabulary, stated by every producer, read by render.

    The point of this class: provenance used to be re-inferred at the render
    layer from four unrelated presence checks -- `tokens is None`, a "!" suffix
    glued onto the price-source string, an `assumed_mix` presence check, and
    `std_rate` being falsy. Any new row producer could satisfy none of them and
    still render as though everything were measured."""

    def test_vocabulary_is_enforced(self):
        with self.assertRaises(ValueError):
            cc.provenance(consumed="guessed", cost="l3m", mix=cc.MEASURED)
        with self.assertRaises(ValueError):
            cc.provenance(consumed=cc.COUNTED, cost="l3m", mix="probably")

    def test_a_cost_source_is_mandatory(self):
        """Every dollar figure must name where its price came from."""
        with self.assertRaises(ValueError):
            cc.provenance(consumed=cc.COUNTED, cost="", mix=cc.MEASURED)

    def test_every_real_producer_emits_complete_provenance(self):
        """The uniformity guarantee. Runs the actual producers over local data --
        a new one cannot be added without provenance and still pass."""
        rows = (cc.kiro_rows(cc.KIRO_DEFAULT_RATE, 1.0, dict(cc.KIRO_DEFAULT_MIX))
                + cc.l3m_rows(cc.l3m_settings()))
        if not rows:
            self.skipTest("no local Kiro or l3m data to read")
        for row in rows:
            with self.subTest(harness=row["harness"], model=row["model"]):
                self.assertEqual(set(row["provenance"]),
                                 {"consumed", "cost", "mix"})
                self.assertIn(row["provenance"]["consumed"], {cc.COUNTED, cc.METERED})
                self.assertIn(row["provenance"]["mix"],
                              {cc.MEASURED, cc.PARTIAL, cc.ASSUMED, cc.NO_MIX})
                self.assertTrue(row["provenance"]["cost"])

    def test_every_row_carries_the_keys_render_reads(self):
        """render indexes these unconditionally; a producer omitting one would
        raise at print time rather than at construction."""
        rows = (cc.kiro_rows(cc.KIRO_DEFAULT_RATE, 1.0, dict(cc.KIRO_DEFAULT_MIX))
                + cc.l3m_rows(cc.l3m_settings()))
        if not rows:
            self.skipTest("no local Kiro or l3m data to read")
        for row in rows:
            with self.subTest(harness=row["harness"]):
                for key in ("day", "harness", "model", "consumed", "unit", "rate",
                            "cost", "tokens", "assumed_mix", "provenance"):
                    self.assertIn(key, row)

    def test_partial_mix_is_distinct_from_fully_measured(self):
        """codex's cache-write is unobservable, not zero, so its rows must not
        claim the same provenance as a harness that counted all four buckets."""
        self.assertNotEqual(cc.PARTIAL, cc.MEASURED)
        self.assertIn(cc.PARTIAL, {cc.MEASURED, cc.PARTIAL, cc.ASSUMED, cc.NO_MIX})

    def test_unpriced_cost_is_a_label_not_a_string_suffix(self):
        """It used to be `priced_by += "!"`, so render had to parse a string to
        learn whether a dollar figure was real."""
        self.assertNotIn("!", cc.UNPRICED)
        row = token_row()
        row["provenance"]["cost"] = cc.UNPRICED
        self.assertEqual(row["provenance"]["cost"], cc.UNPRICED)


class UnobservableBuckets(unittest.TestCase):
    """A zero a harness's log cannot distinguish from an absence.

    Codex carries exactly input / cached_input / output / reasoning_output / total
    across all 10,257 token_count events -- no cache-creation field -- while
    gpt-5.6-sol IS billed for cache writes ($6.25/Mtok base, $12.50 long-context).
    So its cache-write share is a floor, and rendering a confident "0%" invited
    the false conclusion that codex never writes a cache."""

    def test_only_codex_is_declared_unobservable(self):
        self.assertEqual(cc.UNOBSERVABLE_BUCKETS,
                         {"codex": ("cacheCreationTokens",)})

    def test_codex_log_really_has_no_cache_creation_field(self):
        """Guards the premise, not the code: if a future Codex version adds the
        field, CODEX_USAGE_KEYS should grow and this should be revisited."""
        self.assertNotIn("cache_creation_input_tokens", cc.CODEX_USAGE_KEYS)
        self.assertFalse([k for k in cc.CODEX_USAGE_KEYS if "creation" in k])

    def test_gpt_cache_write_is_actually_billed(self):
        """The reason the gap matters: a free tier would make 0% harmless."""
        self.assertGreater(cc.LITELLM_SNAPSHOT["gpt-5.6-sol"][3], 0)
        self.assertGreater(cc.CODEX_LONG_CONTEXT["gpt-5.6-sol"][1][3], 0)

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

class RowCoherence(unittest.TestCase):
    """validate_rows: labels must agree with the row they describe.

    provenance() only checks each label is in the vocabulary. Both mutations
    below -- a credit row claiming a MEASURED mix, and claiming its $/Mtok was
    standardized -- used every label legally and passed the entire suite before
    these tests existed."""

    def test_real_rows_pass(self):
        rows = (cc.kiro_rows(cc.KIRO_DEFAULT_RATE, 1.0, dict(cc.KIRO_DEFAULT_MIX))
                + cc.l3m_rows(cc.l3m_settings()))
        if not rows:
            self.skipTest("no local Kiro or l3m data to read")
        cc.validate_rows(rows)                       # must not raise

    def test_constructed_rows_pass(self):
        rows = [token_row(std=1.0), token_row(), credit_row(mix={"cr": 1.0}),
                credit_row(mix=None)]
        cc.validate_rows(rows)

    def test_measured_mix_without_token_buckets_is_rejected(self):
        row = credit_row(mix=None)
        row["provenance"]["mix"] = cc.MEASURED
        with self.assertRaises(ValueError):
            cc.validate_rows([row])

    def test_counted_claimed_without_buckets_is_rejected(self):
        row = credit_row(mix=None)
        row["provenance"]["consumed"] = cc.COUNTED
        with self.assertRaises(ValueError):
            cc.validate_rows([row])

    def test_assumed_mix_label_must_match_the_actual_mix_field(self):
        orphan = credit_row(mix=None)
        orphan["provenance"]["mix"] = cc.ASSUMED
        with self.assertRaises(ValueError):
            cc.validate_rows([orphan])
        unlabelled = credit_row(mix={"cr": 1.0})
        unlabelled["provenance"]["mix"] = cc.NO_MIX
        with self.assertRaises(ValueError):
            cc.validate_rows([unlabelled])

    def test_the_error_names_the_offending_row(self):
        row = credit_row(mix=None)
        row["provenance"]["mix"] = cc.MEASURED
        with self.assertRaises(ValueError) as caught:
            cc.validate_rows([row])
        self.assertIn("kiro/claude-opus-5", str(caught.exception))

    def test_main_actually_calls_it(self):
        """A wiring test, not a logic one. Deleting the validate_rows(rows) call
        from main leaves every test above passing -- the same blind spot that hid
        the default-rate bug, where the function was right and nothing invoked
        it. Runs main over a window with almost no rows to keep it cheap."""
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


class Rendering(unittest.TestCase):
    """Only what survives the removal of the cache/standardization columns.

    The rest of this class went with them; these two remain because they guard
    render behaviour that is still live, and mutation testing caught their
    absence immediately."""

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
        so reassigning sys.stdout later silently has no effect -- which is why the
        default is None and resolved at call time."""
        stdout = sys.stdout
        try:
            sys.stdout = io.StringIO()
            cc.render([token_row()])
            captured = sys.stdout.getvalue()
        finally:
            sys.stdout = stdout
        self.assertIn("Subtotal", captured)


class MixArithmetic(unittest.TestCase):
    """The assumed-mix decomposition behind Kiro's $/credit."""

    def test_default_rate_is_the_fresh_input_rate_times_the_default_mix(self):
        """The whole point of the constant structure: the rate is a product of a
        primitive and a visible mix, not a magic number with a mix hidden in it."""
        self.assertAlmostEqual(
            cc.KIRO_DEFAULT_RATE,
            cc.KIRO_FRESH_INPUT_RATE * cc.kiro_mix_factor(cc.KIRO_DEFAULT_MIX),
            places=12)

    def test_the_default_mix_is_deliberately_round(self):
        """It is a guess and must look like one -- 95.1/4.4 would read as a
        measurement while being Claude Code's measurement wearing a Kiro label."""
        for share in cc.KIRO_DEFAULT_MIX.values():
            self.assertAlmostEqual(share * 100, round(share * 100 / 5) * 5, places=9)

    def test_the_default_mix_sits_inside_the_measured_range(self):
        """Measured harnesses span 75.4%-95.6% cache-read (input-side); Claude Code
        is the top. The default must keep a real margin below it -- assuming Kiro
        is the best cacher present is precisely the claim being avoided, and a
        bound of merely `< 0.956` would admit 0.95, which is that claim."""
        self.assertLessEqual(cc.KIRO_DEFAULT_MIX["cr"], 0.92)
        self.assertGreater(cc.KIRO_DEFAULT_MIX["cr"], 0.754)

    def test_shares_sum_to_one(self):
        self.assertAlmostEqual(sum(cc.KIRO_DEFAULT_MIX.values()), 1.0, places=9)

    def test_pure_cache_read_reproduces_the_former_default(self):
        """--kiro-mix 100/0 must still reach the pre-2026-08 $0.0747."""
        self.assertAlmostEqual(cc.kiro_mix_rate("100/0")["rate"],
                               cc.KIRO_PURE_CACHE_READ_RATE, places=12)
        self.assertAlmostEqual(cc.KIRO_PURE_CACHE_READ_RATE, 0.0747, places=4)

    def test_rate_follows_the_mix_rather_than_being_pinned(self):
        """The bug this replaces: the default rate ignored the displayed mix, so
        editing the mix rendered one assumption while costing at another."""
        cheap = cc.kiro_mix_rate("100/0")["rate"]
        dear = cc.kiro_mix_rate("80/20")["rate"]
        self.assertGreater(dear, cheap * 3)

    def test_cache_write_dominates_the_correction(self):
        """5% cache-write contributes more than the 5-point drop in cache-read
        takes away -- the counterintuitive fact the whole mix argument rests on."""
        at_100 = cc.kiro_mix_factor({"cr": 1.00, "cw": 0.00, "in": 0.0})
        at_95 = cc.kiro_mix_factor({"cr": 0.95, "cw": 0.05, "in": 0.0})
        self.assertGreater(at_95, at_100)
        cw_term = 0.05 * cc.KIRO_PRICE_RATIO["cw"]
        self.assertGreater(cw_term / at_95, 0.35)

    def test_remainder_becomes_fresh_input(self):
        mix = cc.kiro_mix_rate("80/5")
        self.assertAlmostEqual(mix["in"], 0.15, places=10)

    def test_no_float_dust_in_the_remainder(self):
        # 1 - 0.95 - 0.05 is 4.2e-17 in binary floating point.
        self.assertEqual(cc.kiro_mix_rate("95/5")["in"], 0.0)

    def test_rejects_malformed_and_impossible_mixes(self):
        # Narrow to the argparse type -- assertRaises(Exception) would also pass
        # on a NameError from a typo inside kiro_mix_rate, testing nothing.
        for spec in ("abc", "80/40", "-5/10", "1/2/3", ""):
            with self.subTest(spec=spec), \
                 self.assertRaises(argparse.ArgumentTypeError):
                cc.kiro_mix_rate(spec)


class KiroPricingWiring(unittest.TestCase):
    """resolve_kiro_pricing: which rate and which mix reach the rows.

    Tested separately from the constants because the constants can stay perfectly
    consistent while the plumbing stops honouring them -- that was the actual bug,
    and no assertion about KIRO_DEFAULT_RATE could see it."""

    def test_default_path_derives_the_rate_from_the_default_mix(self):
        rate, mix = cc.resolve_kiro_pricing(None, cc.KIRO_DEFAULT_RATE)
        self.assertEqual(mix, cc.KIRO_DEFAULT_MIX)
        self.assertAlmostEqual(
            rate, cc.KIRO_FRESH_INPUT_RATE * cc.kiro_mix_factor(mix), places=12)

    def test_default_rate_tracks_the_mix_when_the_mix_changes(self):
        """The load-bearing check: with the mix swapped, the resolved rate must
        move with it rather than staying pinned to a hardcoded constant."""
        original, baseline = cc.KIRO_DEFAULT_MIX, cc.KIRO_DEFAULT_RATE
        try:
            cc.KIRO_DEFAULT_MIX = {"cr": 0.80, "cw": 0.20, "in": 0.00}
            cc.KIRO_DEFAULT_RATE = (cc.KIRO_FRESH_INPUT_RATE
                                    * cc.kiro_mix_factor(cc.KIRO_DEFAULT_MIX))
            rate, mix = cc.resolve_kiro_pricing(None, cc.KIRO_DEFAULT_RATE)
            self.assertEqual(mix["cw"], 0.20)
            self.assertGreater(rate, baseline)
        finally:
            cc.KIRO_DEFAULT_MIX, cc.KIRO_DEFAULT_RATE = original, baseline

    def test_kiro_mix_flag_wins_and_carries_its_own_mix(self):
        rate, mix = cc.resolve_kiro_pricing(cc.kiro_mix_rate("95/5"),
                                            cc.KIRO_DEFAULT_RATE)
        self.assertAlmostEqual(mix["cr"], 0.95, places=10)
        self.assertNotIn("rate", mix)
        self.assertAlmostEqual(rate, cc.kiro_mix_rate("95/5")["rate"], places=12)

    def test_explicit_credit_rate_carries_no_mix(self):
        """0.056 back-solves to an impossible >100% cache-read share, so showing
        any mix for it would be a fabrication."""
        rate, mix = cc.resolve_kiro_pricing(None, 0.056)
        self.assertEqual(rate, 0.056)
        self.assertIsNone(mix)


class SubtotalPropagation(unittest.TestCase):
    """harness_subtotals: where both shipped Std/Eff bugs lived."""

    def test_effective_rate_is_cost_over_consumed(self):
        bucket = cc.harness_subtotals([token_row(harness="h", cost=9.0, mtok=3.0)])["h"]
        self.assertAlmostEqual(bucket["rate"], 3.0, places=9)

    def test_harnesses_do_not_bleed_into_each_other(self):
        agg = cc.harness_subtotals([token_row(harness="a", cost=1.0),
                                    token_row(harness="b", cost=2.0)])
        self.assertAlmostEqual(agg["a"]["cost"], 1.0, places=9)
        self.assertAlmostEqual(agg["b"]["cost"], 2.0, places=9)


class CreditCalibration(unittest.TestCase):
    """The /usage anchor that corrects the scan, not the price."""

    def test_completeness_derives_from_the_recorded_anchor(self):
        anchor = cc.KIRO_CREDIT_ANCHOR
        self.assertAlmostEqual(
            cc.KIRO_COMPLETENESS,
            anchor["authoritative_credits"] / anchor["scanned_credits"], places=12)

    def test_the_scan_reads_low_so_the_correction_is_upward(self):
        self.assertGreater(cc.KIRO_COMPLETENESS, 1.0)

    def test_completeness_scales_consumed_not_rate(self):
        """Applied to credits so that Consumed x Rate == Cost keeps holding and
        Rate stays the documented $/credit."""
        plain = cc.kiro_rows(0.1, completeness=1.0)
        scaled = cc.kiro_rows(0.1, completeness=2.0)
        if not plain:
            self.skipTest("no local Kiro sessions to read")
        self.assertAlmostEqual(sum(r["consumed"] for r in scaled),
                               2 * sum(r["consumed"] for r in plain), places=6)
        self.assertEqual({r["rate"] for r in scaled}, {0.1})


class RowInvariants(unittest.TestCase):
    """Properties every row must satisfy, whatever produced it."""

    def test_consumed_times_rate_equals_cost(self):
        for row in (token_row(cost=2.5, mtok=5.0),
                    token_row(cost=0.0, mtok=1.0)):
            with self.subTest(cost=row["cost"]):
                self.assertAlmostEqual(row["consumed"] * row["rate"], row["cost"],
                                       places=9)

    def test_canon_strips_provider_and_region_prefixes(self):
        for name in ("us.anthropic.claude-opus-5", "global.anthropic.claude-opus-5",
                     "openai.claude-opus-5"):
            with self.subTest(name=name):
                self.assertEqual(cc.canon(name), "claude-opus-5")

    def test_l3m_cost_rounds_to_the_cent_like_the_lean_source(self):
        """Must use a sub-cent case: on an exact multiple the +500000 term is
        invisible, so a whole-dollar example tests nothing about the rounding."""
        rates = cc.L3M_CLAUDE["claude-opus-4-8"]

        def cost(input_tokens):
            return cc.l3m_cost_usd(rates, {"inputTokens": input_tokens,
                                           "outputTokens": 0, "cacheReadTokens": 0,
                                           "cacheCreationTokens": 0})

        # 1500 tokens x 500 cents/Mtok = 0.75 cents -> rounds UP to 1 cent.
        self.assertAlmostEqual(cost(1500), 0.01, places=9)
        # 400 tokens = 0.20 cents -> rounds DOWN to nothing.
        self.assertAlmostEqual(cost(400), 0.0, places=9)
        # and the exact multiple still lands exactly.
        self.assertAlmostEqual(cost(1_000_000), 5.0, places=9)

    def test_cache_read_is_a_tenth_of_input_across_the_tables(self):
        """Kiro's x0.1 mix factor is only defensible because this holds."""
        for name, (inp, _out, cr, _cw) in cc.L3M_CLAUDE.items():
            with self.subTest(model=name):
                self.assertAlmostEqual(cr / inp, 0.1, places=9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
