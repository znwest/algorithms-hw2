import unittest

from src.hash_table import HashTable


class HashTableTests(unittest.TestCase):
    def test_colliding_keys_are_stored_and_retrieved_independently(self):
        table = HashTable()
        # "a" and "i" have the same bucket index at capacity 8.
        table.put("a", "first")
        table.put("i", "second")

        self.assertEqual(table.get("a"), "first")
        self.assertEqual(table.get("i"), "second")
        self.assertIn("a", table)
        self.assertIn("i", table)
        self.assertEqual(len(table), 2)

    def test_updating_a_key_does_not_increase_length(self):
        table = HashTable()
        table.put("key", "old")
        table.put("key", "new")

        self.assertEqual(table.get("key"), "new")
        self.assertEqual(len(table), 1)

    def test_missing_key_returns_none_and_is_not_contained(self):
        table = HashTable()

        self.assertIsNone(table.get("missing"))
        self.assertNotIn("missing", table)
        self.assertEqual(len(table), 0)

    def test_empty_string_key_can_be_stored(self):
        table = HashTable()
        table.put("", "empty")

        self.assertEqual(table.get(""), "empty")
        self.assertIn("", table)
        self.assertEqual(len(table), 1)

    def test_seventh_insert_grows_capacity_to_sixteen(self):
        table = HashTable()
        for index in range(7):
            table.put(f"key-{index}", index)

        self.assertEqual(len(table), 7)
        self.assertEqual(table._capacity, 16)

    def test_multiple_resizes_preserve_all_entries(self):
        table = HashTable()
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


if __name__ == "__main__":
    unittest.main()
