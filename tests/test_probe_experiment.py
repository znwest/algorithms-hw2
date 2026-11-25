import unittest

from src.hash_table import HashTable


class HashTableConfigurationTests(unittest.TestCase):
    def test_capacity_and_disabled_resize_are_respected(self):
        table: HashTable[str] = HashTable(capacity=4093, max_load=None)

        for index in range(4094):
            table.put(f"https://{index}.example/", str(index))

        self.assertEqual(table._capacity, 4093)
        self.assertEqual(len(table), 4094)
        self.assertEqual(table.get("https://4093.example/"), "4093")


if __name__ == "__main__":
    unittest.main()
