import unittest

from experiments.compare_tables import (
    draw_svg,
    run_comparison,
    theory_chain_failure,
    theory_chain_success,
    theory_linear_failure,
    theory_linear_success,
)


class CompareTablesTests(unittest.TestCase):
    def test_comparison_uses_identical_counts_at_requested_load_factors(self):
        rows = run_comparison(capacity=101, load_factors=(0.1, 0.9))

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][2], 10)
        self.assertEqual(rows[1][2], 91)
        for row in rows:
            with self.subTest(alpha=row[0]):
                self.assertAlmostEqual(row[1], row[2] / 101)
                self.assertTrue(all(probes >= 0 for probes in row[3:]))

    def test_theory_formulas_match_lecture_estimates(self):
        self.assertAlmostEqual(theory_chain_success(0.5), 1.25)
        self.assertAlmostEqual(theory_chain_failure(0.5), 0.5)
        self.assertAlmostEqual(theory_linear_success(0.5), 1.5)
        self.assertAlmostEqual(theory_linear_failure(0.5), 2.5)
        self.assertAlmostEqual(theory_linear_failure(0.9), 50.5)

    def test_graph_draws_four_theory_curves_with_measured_points(self):
        rows = run_comparison(capacity=101, load_factors=(0.1, 0.5, 0.9))
        svg = draw_svg(rows)

        self.assertEqual(svg.count("<polyline"), 4)
        self.assertEqual(svg.count("<circle") + svg.count('<rect x='), 12)


if __name__ == "__main__":
    unittest.main()
