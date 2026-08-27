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
              std=None, **tokens):
    """A token-logged row, shaped exactly as the real producers shape one.

    Built through cc.provenance() rather than a literal dict so the helper cannot
    drift from the vocabulary the production code enforces."""
    counts = {"inputTokens": 0, "outputTokens": 0,
              "cacheReadTokens": int(mtok * 1e6), "cacheCreationTokens": 0}
    counts.update(tokens)
    row = {"day": "2026-08-01", "harness": harness, "model": model,
           "consumed": mtok, "unit": "Mtok", "rate": cost / mtok if mtok else 0.0,
           "cost": cost, "tokens": counts, "assumed_mix": None,
           "provenance": cc.provenance(consumed=cc.COUNTED, cost="l3m",
                                       mix=cc.MEASURED, std=cc.UNPRICED)}
    if std is not None:
        row["std_rate"] = std
        row["provenance"]["std"] = cc.STANDARDIZED
        row["efficiency"] = row["rate"] / std if std else None
    return row


def credit_row(mix=None, rate=None, cost=7.47, credits=100.0):
    """A Kiro row: metered credits, no token buckets, mix assumed or absent."""
    rate = cc.USD_PER_CREDIT if rate is None else rate
    return {"day": "2026-08-01", "harness": "kiro", "model": "claude-opus-5",
            "consumed": credits, "unit": "credits", "rate": rate, "cost": cost,
            "tokens": None, "assumed_mix": mix,
            "provenance": cc.provenance(
                consumed=cc.METERED, cost="kiro-credit",
                mix=cc.ASSUMED if mix else cc.NO_MIX, std=cc.NO_TOKENS)}


class Provenance(unittest.TestCase):
    """One vocabulary, stated by every producer, read by render.

    The point of this class: provenance used to be re-inferred at the render
    layer from four unrelated presence checks -- `tokens is None`, a "!" suffix
    glued onto the price-source string, an `assumed_mix` presence check, and
    `std_rate` being falsy. Any new row producer could satisfy none of them and
    still render as though everything were measured."""

    def test_vocabulary_is_enforced(self):
        with self.assertRaises(ValueError):
            cc.provenance(consumed="guessed", cost="l3m", mix=cc.MEASURED,
                          std=cc.STANDARDIZED)
        with self.assertRaises(ValueError):
            cc.provenance(consumed=cc.COUNTED, cost="l3m", mix="probably",
                          std=cc.STANDARDIZED)
        with self.assertRaises(ValueError):
            cc.provenance(consumed=cc.COUNTED, cost="l3m", mix=cc.MEASURED,
                          std="sort-of")

    def test_a_cost_source_is_mandatory(self):
        """Every dollar figure must name where its price came from."""
        with self.assertRaises(ValueError):
            cc.provenance(consumed=cc.COUNTED, cost="", mix=cc.MEASURED,
                          std=cc.STANDARDIZED)

    def test_every_real_producer_emits_complete_provenance(self):
        """The uniformity guarantee. Runs the actual producers over local data --
        a new one cannot be added without provenance and still pass."""
        rows = (cc.kiro_rows(cc.USD_PER_CREDIT, 1.0, dict(cc.KIRO_DEFAULT_MIX))
                + cc.l3m_rows(cc.l3m_settings()))
        if not rows:
            self.skipTest("no local Kiro or l3m data to read")
        for row in rows:
            with self.subTest(harness=row["harness"], model=row["model"]):
                self.assertEqual(set(row["provenance"]),
                                 {"consumed", "cost", "mix", "std"})
                self.assertIn(row["provenance"]["consumed"], {cc.COUNTED, cc.METERED})
                self.assertIn(row["provenance"]["mix"],
                              {cc.MEASURED, cc.ASSUMED, cc.NO_MIX})
                self.assertIn(row["provenance"]["std"],
                              {cc.STANDARDIZED, cc.UNPRICED, cc.AMBIGUOUS,
                               cc.NO_TOKENS})
                self.assertTrue(row["provenance"]["cost"])

    def test_every_row_carries_the_keys_render_reads(self):
        """render indexes these unconditionally; a producer omitting one would
        raise at print time rather than at construction."""
        rows = (cc.kiro_rows(cc.USD_PER_CREDIT, 1.0, dict(cc.KIRO_DEFAULT_MIX))
                + cc.l3m_rows(cc.l3m_settings()))
        if not rows:
            self.skipTest("no local Kiro or l3m data to read")
        for row in rows:
            with self.subTest(harness=row["harness"]):
                for key in ("day", "harness", "model", "consumed", "unit", "rate",
                            "cost", "tokens", "assumed_mix", "provenance"):
                    self.assertIn(key, row)

    def test_measured_and_assumed_mixes_are_visually_distinguishable(self):
        """A measured share must never carry the assumed marker, or the whole
        point of showing Kiro's assumption is lost."""
        self.assertEqual(cc.MIX_MARKER[cc.MEASURED], "")
        self.assertEqual(cc.MIX_MARKER[cc.ASSUMED], "~")

    def test_standardize_labels_why_a_row_has_no_std(self):
        """Three different reasons, distinguished rather than collapsed to a
        blank: an unlisted model, a fallback chain, and a credit-metered row."""
        unlisted = token_row(model="mystery-model-9")
        chain = token_row(model="claude-opus-5,opus,sonnet,haiku")
        credits = credit_row(mix=dict(cc.KIRO_DEFAULT_MIX))
        cc.standardize([token_row(), unlisted, chain, credits], "l3m", False)
        self.assertEqual(unlisted["provenance"]["std"], cc.UNPRICED)
        self.assertEqual(chain["provenance"]["std"], cc.AMBIGUOUS)
        self.assertEqual(credits["provenance"]["std"], cc.NO_TOKENS)

    def test_unpriced_cost_is_a_label_not_a_string_suffix(self):
        """It used to be `priced_by += "!"`, so render had to parse a string to
        learn whether a dollar figure was real."""
        self.assertNotIn("!", cc.UNPRICED)
        row = token_row()
        row["provenance"]["cost"] = cc.UNPRICED
        self.assertEqual(row["provenance"]["cost"], cc.UNPRICED)


class RowCoherence(unittest.TestCase):
    """validate_rows: labels must agree with the row they describe.

    provenance() only checks each label is in the vocabulary. Both mutations
    below -- a credit row claiming a MEASURED mix, and claiming its $/Mtok was
    standardized -- used every label legally and passed the entire suite before
    these tests existed."""

    def test_real_rows_pass(self):
        rows = (cc.kiro_rows(cc.USD_PER_CREDIT, 1.0, dict(cc.KIRO_DEFAULT_MIX))
                + cc.l3m_rows(cc.l3m_settings()))
        if not rows:
            self.skipTest("no local Kiro or l3m data to read")
        cc.standardize(rows, "l3m", False)
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

    def test_standardized_without_a_standardized_rate_is_rejected(self):
        row = credit_row(mix={"cr": 1.0})
        row["provenance"]["std"] = cc.STANDARDIZED
        with self.assertRaises(ValueError):
            cc.validate_rows([row])

    def test_no_tokens_claimed_on_a_token_row_is_rejected(self):
        row = token_row(std=1.0)
        row["provenance"]["std"] = cc.NO_TOKENS
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
    """render must derive every marker from provenance, never re-infer it."""

    def table(self, rows):
        buffer = io.StringIO()
        cc.render(rows, stream=buffer)
        return buffer.getvalue()

    def test_assumed_mix_renders_with_a_tilde(self):
        text = self.table([token_row(std=1.0),
                           credit_row(mix={"cr": 1.0, "cw": 0.0, "in": 0.0})])
        self.assertIn("~100%", text)

    def test_measured_mix_renders_without_one(self):
        text = self.table([token_row(mtok=1.0, std=1.0, cacheReadTokens=1_000_000)])
        self.assertIn("100%", text)
        self.assertNotIn("~100%", text)

    def test_no_mix_renders_a_dash_not_a_fabricated_share(self):
        """An explicit --credit-rate corresponds to no stated mix."""
        text = self.table([credit_row(mix=None, rate=0.056)])
        self.assertNotIn("~", text)
        self.assertNotIn("%", text.split("Cost (USD)")[-1])

    def test_unpriced_model_is_flagged_on_its_own_row(self):
        row = token_row(model="mystery-model-9")
        row["provenance"]["cost"] = cc.UNPRICED
        self.assertIn("mystery-model-9 (!)", self.table([row]))

    def test_empty_input_says_so_rather_than_printing_a_header(self):
        self.assertIn("No usage data found", self.table([]))

    def test_render_writes_to_the_current_stdout(self):
        """`stream=sys.stdout` as a default binds whatever stdout was at import,
        so reassigning sys.stdout later silently has no effect -- which is why the
        default is None and resolved at call time."""
        stdout = sys.stdout
        try:
            sys.stdout = io.StringIO()
            cc.render([token_row(std=1.0)])
            captured = sys.stdout.getvalue()
        finally:
            sys.stdout = stdout
        self.assertIn("Subtotal", captured)


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
        kiro = credit_row(mix=dict(cc.KIRO_DEFAULT_MIX))
        cc.standardize([token_row(), kiro], "l3m", False)
        self.assertIsNone(kiro.get("std_rate"))
        self.assertEqual(kiro["provenance"]["std"], cc.NO_TOKENS)
        self.assertIsNotNone(kiro.get("efficiency"))

    def test_kiro_efficiency_reaches_one_when_its_assumption_matches_reality(self):
        """--kiro-mix set to the measured mix must read ~1.00; that is the only
        check that the borrowed 95/5 proxy means what it claims."""
        measured = {"cacheReadTokens": 950_000, "cacheCreationTokens": 50_000,
                    "inputTokens": 0, "outputTokens": 0}
        kiro = credit_row(mix={"cr": 0.95, "cw": 0.05, "in": 0.0}, rate=0.1, cost=10.0)
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
        priced = token_row(harness="h", cost=1.0, mtok=1.0, std=1.0)
        unpriced = token_row(harness="h", model="mystery", cost=0.0, mtok=9.0)
        bucket = cc.harness_subtotals([priced, unpriced])["h"]
        self.assertAlmostEqual(bucket["std"], 1.0, places=9)
        self.assertAlmostEqual(bucket["consumed"], 10.0, places=9)

    def test_std_is_volume_weighted_across_priced_rows(self):
        cheap = token_row(harness="h", cost=1.0, mtok=1.0, std=1.0)
        dear = token_row(harness="h", cost=3.0, mtok=3.0, std=3.0)
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
        self.assertIsNone(
            cc.harness_subtotals([credit_row(mix=None)])["kiro"]["cache_shares"])

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
