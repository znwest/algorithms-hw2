import importlib
import unittest

from src import shortener
from src.hash_table import HashTable
from src.linear_probing_hash_table import LinearProbingHashTable


class ShortenerBackendTests(unittest.TestCase):
    table_class = HashTable

    def setUp(self):
        importlib.reload(shortener)
        shortener.configure_table_type(self.table_class)

    def test_normalization_and_duplicate_urls(self):
        self.assertEqual(
            shortener.shorten("  https://example.com/path  "),
            ("0", True),
        )
        self.assertEqual(
            shortener.shorten("https://example.com/path"),
            ("0", False),
        )

    def test_distinct_urls_receive_sequential_codes(self):
        urls = (
            "https://example.com",
            "https://example.com/",
            "https://EXAMPLE.com",
        )

        self.assertEqual(
            [shortener.shorten(url) for url in urls],
            [("0", True), ("1", True), ("2", True)],
        )

    def test_expand_uses_the_exact_code(self):
        url = "https://example.com/a?b=c"
        shortener.shorten(url)
        self.assertEqual(shortener.expand("0"), url)

        for code in ("00", "missing", ""):
            with self.subTest(code=code), self.assertRaises(KeyError):
                shortener.expand(code)

    def test_invalid_urls_are_rejected(self):
        for url in ("", "example.com", "ftp://example.com", "http://:80"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                shortener.shorten(url)

    def test_url_length_limit(self):
        prefix = "https://example.com/"
        accepted = prefix + "a" * (2048 - len(prefix))
        self.assertTrue(shortener.shorten(accepted)[1])

        with self.assertRaises(ValueError):
            shortener.shorten(accepted + "a")

    def test_both_table_views_contain_the_same_url_mapping(self):
        url = "https://example.com/current"
        shortener.shorten(url)

        chain_entries = [
            entry
            for bucket in shortener.url_table_snapshot()
            for entry in bucket
        ]
        linear_entries = [
            entry
            for entry in shortener.linear_table_snapshot()
            if entry is not None
        ]
        self.assertEqual(chain_entries, [(url, "0")])
        self.assertEqual(linear_entries, [(url, "0")])


class LinearProbingShortenerTests(ShortenerBackendTests):
    table_class = LinearProbingHashTable


class SeparateChainingShortenerTests(ShortenerBackendTests):
    table_class = HashTable


if __name__ == "__main__":
    unittest.main()
