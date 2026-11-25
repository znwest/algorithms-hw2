import unittest

from src.hash_table import HashTable


class HashTableContract:
    """Tests every hash table implementation must pass.

    Subclasses set make_table to a callable taking (capacity, max_load).
    test_linear_probing_hash_table.py reuses this class unchanged.
    """

    make_table = None

    def new_table(self, capacity=8, max_load=0.75):
        return type(self).make_table(capacity=capacity, max_load=max_load)

    def test_colliding_keys_are_stored_and_retrieved_independently(self):
        table = self.new_table()
        # "a" and "i" have the same Horner index at capacity 8.
        table.put("a", "first")
        table.put("i", "second")

        self.assertEqual(table.get("a"), "first")
        self.assertEqual(table.get("i"), "second")
        self.assertIn("a", table)
        self.assertIn("i", table)
        self.assertEqual(len(table), 2)

    def test_updating_a_key_does_not_increase_length(self):
        table = self.new_table()
        table.put("key", "old")
        table.put("key", "new")

        self.assertEqual(table.get("key"), "new")
        self.assertEqual(len(table), 1)

    def test_missing_key_returns_none_and_is_not_contained(self):
        table = self.new_table()

        self.assertIsNone(table.get("missing"))
        self.assertNotIn("missing", table)
        self.assertNotIn(1, table)
        self.assertEqual(len(table), 0)

    def test_empty_string_key_can_be_stored(self):
        table = self.new_table()
        table.put("", "empty")

        self.assertEqual(table.get(""), "empty")
        self.assertIn("", table)
        self.assertEqual(len(table), 1)

    def test_seventh_insert_grows_capacity_to_sixteen(self):
        table = self.new_table()
        for index in range(6):
            table.put(f"key-{index}", index)
        self.assertEqual(table._capacity, 8)

        table.put("key-6", 6)
        self.assertEqual(len(table), 7)
        self.assertEqual(table._capacity, 16)

    def test_multiple_resizes_preserve_all_entries(self):
        table = self.new_table()
        entries = [
            (f"key-{index}", f"value-{index}")
            for index in range(100)
        ]

        for key, value in entries:
            table.put(key, value)

        self.assertEqual(len(table), len(entries))
        for key, value in entries:
            with self.subTest(key=key):
                self.assertEqual(table.get(key), value)

    def test_load_factor_is_entries_over_capacity(self):
        table = self.new_table(capacity=10, max_load=None)
        self.assertEqual(table.load_factor(), 0.0)
        for index in range(4):
            table.put(f"key-{index}", index)
        self.assertAlmostEqual(table.load_factor(), 0.4)

    def test_load_factor_stays_at_or_below_limit_after_resize(self):
        table = self.new_table()
        for index in range(50):
            table.put(f"key-{index}", index)
            self.assertLessEqual(table.load_factor(), 0.75)

    def test_find_returns_value_and_positive_cost_for_present_key(self):
        table = self.new_table()
        table.put("a", "first")
        table.put("i", "second")  # same index as "a"

        self.assertEqual(table.find("a"), ("first", 1))
        value, cost = table.find("i")
        self.assertEqual(value, "second")
        self.assertEqual(cost, 2)

    def test_find_returns_none_for_missing_key(self):
        table = self.new_table()
        table.put("a", "first")

        value, cost = table.find("i")  # same index as "a", not stored
        self.assertIsNone(value)
        self.assertGreaterEqual(cost, 1)


class HashTableTests(HashTableContract, unittest.TestCase):
    make_table = HashTable

    def test_find_cost_on_empty_bucket_is_zero_nodes(self):
        table = HashTable()
        self.assertEqual(table.find("missing"), (None, 0))


if __name__ == "__main__":
    unittest.main()
