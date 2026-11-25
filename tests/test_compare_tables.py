import unittest

from experiments.compare_tables import run_comparison


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


if __name__ == "__main__":
    unittest.main()
