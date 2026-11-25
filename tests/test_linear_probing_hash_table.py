import unittest

from src.linear_probing_hash_table import LinearProbingHashTable


class LinearProbingHashTableTests(unittest.TestCase):
    def test_collisions_wrap_from_last_slot_to_zero(self):
        table: LinearProbingHashTable[str] = LinearProbingHashTable(
            capacity=5, max_load=None
        )
        table.put("c", "first")
        table.put("h", "second")
        table.put("m", "third")

        self.assertEqual(table.snapshot_slots()[4], ("c", "first"))
        self.assertEqual(table.snapshot_slots()[0], ("h", "second"))
        self.assertEqual(table.snapshot_slots()[1], ("m", "third"))
        self.assertEqual(table.probe_indices("m"), (4, 0, 1))

    def test_full_table_supports_updates_and_missing_lookups(self):
        table: LinearProbingHashTable[str] = LinearProbingHashTable(
            capacity=5, max_load=None
        )
        keys = ("c", "h", "m", "x", "z")
        for key in keys:
            table.put(key, f"value-{key}")

        self.assertEqual(len(table), 5)
        self.assertEqual(table.get("not-present"), None)
        self.assertEqual(len(table.probe_indices("not-present")), 5)
        with self.assertRaises(OverflowError):
            table.put("new-key", "new-value")

        table.put("c", "updated")
        self.assertEqual(table.get("c"), "updated")
        self.assertEqual(len(table), 5)

    def test_default_load_limit_resizes_and_preserves_entries(self):
        table: LinearProbingHashTable[str] = LinearProbingHashTable()
        entries = [(f"key-{index}", f"value-{index}") for index in range(50)]

        for key, value in entries:
            table.put(key, value)

        self.assertGreater(table._capacity, 8)
        self.assertEqual(len(table), len(entries))
        for key, value in entries:
            with self.subTest(key=key):
                self.assertEqual(table.get(key), value)

    def test_contains_and_update_match_hash_table_interface(self):
        table: LinearProbingHashTable[str] = LinearProbingHashTable()
        table.put("", "empty")

        self.assertIn("", table)
        self.assertNotIn("missing", table)
        self.assertNotIn(1, table)
        table.put("", "updated")
        self.assertEqual(table.get(""), "updated")
        self.assertEqual(len(table), 1)


if __name__ == "__main__":
    unittest.main()
