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


def token_row(harness="claude", model="claude-opus-5", cost=1.0, mtok=1.0, **tokens):
    counts = {"inputTokens": 0, "outputTokens": 0,
              "cacheReadTokens": int(mtok * 1e6), "cacheCreationTokens": 0}
    counts.update(tokens)
    return {"day": "2026-08-01", "harness": harness, "model": model,
            "consumed": mtok, "unit": "Mtok", "rate": cost / mtok if mtok else 0.0,
            "cost": cost, "tokens": counts, "priced_by": "l3m"}


class MixArithmetic(unittest.TestCase):
    """The assumed-mix decomposition behind Kiro's $/credit."""

    def test_default_mix_factor_matches_the_published_constant(self):
        # If these drift, the table shows a mix that did not produce the rate.
        self.assertAlmostEqual(cc.kiro_mix_factor(cc.KIRO_DEFAULT_MIX),
                               cc.KIRO_ASSUMED_MIX, places=12)

    def test_default_rate_is_derived_from_the_displayed_mix(self):
        self.assertAlmostEqual(cc.KIRO_DEFAULT_RATE, cc.USD_PER_CREDIT, places=12)

    def test_rate_follows_the_mix_rather_than_being_pinned(self):
        """The bug this replaces: the default rate ignored the displayed mix, so
        editing the mix rendered one assumption while costing at another."""
        cheap = cc.kiro_mix_rate("100/0")["rate"]
        dear = cc.kiro_mix_rate("80/20")["rate"]
        self.assertAlmostEqual(cheap, cc.USD_PER_CREDIT, places=12)
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
        rate, mix = cc.resolve_kiro_pricing(None, cc.USD_PER_CREDIT)
        self.assertEqual(mix, cc.KIRO_DEFAULT_MIX)
        self.assertAlmostEqual(
            rate, cc.KIRO_FRESH_INPUT_RATE * cc.kiro_mix_factor(mix), places=12)

    def test_default_rate_tracks_the_mix_when_the_mix_changes(self):
        """The load-bearing check: with the mix swapped, the resolved rate must
        move with it rather than staying pinned to USD_PER_CREDIT."""
        original = cc.KIRO_DEFAULT_MIX
        try:
            cc.KIRO_DEFAULT_MIX = {"cr": 0.80, "cw": 0.20, "in": 0.00}
            cc.KIRO_DEFAULT_RATE = (cc.KIRO_FRESH_INPUT_RATE
                                    * cc.kiro_mix_factor(cc.KIRO_DEFAULT_MIX))
            rate, mix = cc.resolve_kiro_pricing(None, cc.USD_PER_CREDIT)
            self.assertEqual(mix["cw"], 0.20)
            self.assertGreater(rate, cc.USD_PER_CREDIT * 3)
        finally:
            cc.KIRO_DEFAULT_MIX = original
            cc.KIRO_DEFAULT_RATE = (cc.KIRO_FRESH_INPUT_RATE
                                    * cc.kiro_mix_factor(original))

    def test_kiro_mix_flag_wins_and_carries_its_own_mix(self):
        rate, mix = cc.resolve_kiro_pricing(cc.kiro_mix_rate("95/5"),
                                            cc.USD_PER_CREDIT)
        self.assertAlmostEqual(mix["cr"], 0.95, places=10)
        self.assertNotIn("rate", mix)
        self.assertGreater(rate, cc.USD_PER_CREDIT)

    def test_explicit_credit_rate_carries_no_mix(self):
        """0.056 back-solves to an impossible >100% cache-read share, so showing
        any mix for it would be a fabrication."""
        rate, mix = cc.resolve_kiro_pricing(None, 0.056)
        self.assertEqual(rate, 0.056)
        self.assertIsNone(mix)


class Standardization(unittest.TestCase):
    """Which rows may be re-priced at a common mix, and which must abstain."""

    def setUp(self):
        self.table = cc.litellm_table(False)

    def test_single_model_resolves(self):
        self.assertIsNotNone(cc.model_rates("claude-opus-5", "l3m", self.table))

    def test_dated_snapshot_resolves_to_its_family(self):
        self.assertIsNotNone(
            cc.model_rates("claude-haiku-4-5-20251001", "l3m", self.table))

    def test_fallback_chain_abstains(self):
        """Longest-prefix matching resolved an l3m chain to its first element and
        priced it as pure opus-5, though the calls may have landed on sonnet,
        haiku or GPT. Cost was unaffected (l3m self-prices); Std/Eff were not."""
        for chain in ("claude-opus-5,opus,sonnet,haiku",
                      "claude-opus-5,opus,sonnet,haiku,gpt-5.6-terra"):
            with self.subTest(chain=chain):
                self.assertIsNone(cc.model_rates(chain, "l3m", self.table))

    def test_unknown_model_abstains(self):
        self.assertIsNone(cc.model_rates("l3m-unknown", "l3m", self.table))

    def test_efficiency_is_one_when_a_row_matches_the_pooled_mix(self):
        """Two rows with identical mixes: each must standardize to its own rate."""
        rows = [token_row(cost=0.5), token_row(cost=0.5)]
        cc.standardize(rows, "l3m", False)
        for row in rows:
            self.assertAlmostEqual(row["efficiency"], 1.0, places=6)

    def test_kiro_gets_efficiency_but_never_a_standardized_rate(self):
        """Eff needs only a mix factor ratio; Std would need an invented token
        count from k x multiplier, which is the line FINDINGS.md draws."""
        kiro = {"day": "2026-08-01", "harness": "kiro", "model": "claude-opus-5",
                "consumed": 100.0, "unit": "credits", "rate": cc.USD_PER_CREDIT,
                "cost": 7.47, "tokens": None, "priced_by": "kiro-credit",
                "assumed_mix": dict(cc.KIRO_DEFAULT_MIX)}
        cc.standardize([token_row(), kiro], "l3m", False)
        self.assertIsNone(kiro.get("std_rate"))
        self.assertIsNotNone(kiro.get("efficiency"))

    def test_kiro_efficiency_reaches_one_when_its_assumption_matches_reality(self):
        """--kiro-mix set to the measured mix must read ~1.00; that is the only
        check that the borrowed 95/5 proxy means what it claims."""
        measured = {"cacheReadTokens": 950_000, "cacheCreationTokens": 50_000,
                    "inputTokens": 0, "outputTokens": 0}
        kiro = {"day": "2026-08-01", "harness": "kiro", "model": "claude-opus-5",
                "consumed": 100.0, "unit": "credits", "rate": 0.1,
                "cost": 10.0, "tokens": None, "priced_by": "kiro-credit",
                "assumed_mix": {"cr": 0.95, "cw": 0.05, "in": 0.0}}
        cc.standardize([token_row(mtok=1.0, **measured), kiro], "l3m", False)
        self.assertAlmostEqual(kiro["efficiency"], 1.0, places=6)

    def test_no_tokens_anywhere_yields_no_reference_mix(self):
        self.assertIsNone(cc.standardize([], "l3m", False))


class SubtotalPropagation(unittest.TestCase):
    """harness_subtotals: where both shipped Std/Eff bugs lived."""

    def test_unpriced_volume_does_not_dilute_std(self):
        """The bug: std was weighted over priced rows but divided by ALL consumed,
        so a harness with unpriced volume had Std understated and Eff overstated
        in proportion. It put opencode at Eff 2.57 where the priced portion is
        0.51 -- inverting "dearer than average" into "cheaper"."""
        priced = token_row(harness="h", cost=1.0, mtok=1.0)
        priced["std_rate"] = 1.0
        unpriced = token_row(harness="h", model="mystery", cost=0.0, mtok=9.0)
        bucket = cc.harness_subtotals([priced, unpriced])["h"]
        self.assertAlmostEqual(bucket["std"], 1.0, places=9)
        self.assertAlmostEqual(bucket["consumed"], 10.0, places=9)

    def test_std_is_volume_weighted_across_priced_rows(self):
        cheap = token_row(harness="h", cost=1.0, mtok=1.0)
        cheap["std_rate"] = 1.0
        dear = token_row(harness="h", cost=3.0, mtok=3.0)
        dear["std_rate"] = 3.0
        bucket = cc.harness_subtotals([cheap, dear])["h"]
        self.assertAlmostEqual(bucket["std"], (1.0 * 1 + 3.0 * 3) / 4, places=9)

    def test_nothing_priced_gives_std_none_not_zero(self):
        """None renders "-"; 0.0 would render a fabricated rate and divide-by-zero
        into Eff."""
        bucket = cc.harness_subtotals([token_row(harness="h", model="mystery")])["h"]
        self.assertIsNone(bucket["std"])
        self.assertIsNone(bucket["efficiency"])

    def test_effective_rate_is_cost_over_consumed(self):
        bucket = cc.harness_subtotals([token_row(harness="h", cost=9.0, mtok=3.0)])["h"]
        self.assertAlmostEqual(bucket["rate"], 3.0, places=9)

    def test_cache_shares_come_from_summed_buckets(self):
        row = token_row(harness="h", mtok=1.0, cacheReadTokens=800_000,
                        cacheCreationTokens=200_000)
        shares = cc.harness_subtotals([row])["h"]["cache_shares"]
        self.assertAlmostEqual(shares["cr"], 0.8, places=9)
        self.assertAlmostEqual(shares["cw"], 0.2, places=9)

    def test_credit_harness_has_no_cache_shares(self):
        kiro = {"day": "2026-08-01", "harness": "kiro", "model": "m",
                "consumed": 1.0, "unit": "credits", "rate": 1.0, "cost": 1.0,
                "tokens": None, "priced_by": "kiro-credit", "assumed_mix": None}
        self.assertIsNone(cc.harness_subtotals([kiro])["kiro"]["cache_shares"])

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
