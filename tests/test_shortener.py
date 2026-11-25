import importlib
import unittest

from src import shortener


class ShortenerTests(unittest.TestCase):
    def setUp(self):
        importlib.reload(shortener)

    def test_shorten_trims_outer_whitespace_and_reuses_existing_code(self):
        code, is_new = shortener.shorten("  https://example.com/path  ")

        self.assertEqual(code, "0")
        self.assertTrue(is_new)
        self.assertEqual(
            shortener.shorten("https://example.com/path"),
            ("0", False),
        )

    def test_distinct_urls_get_sequential_codes_and_keep_normalization_exact(self):
        urls = (
            "https://example.com",
            "https://example.com/",
            "https://EXAMPLE.com",
        )

        results = [shortener.shorten(url) for url in urls]

        self.assertEqual(results, [("0", True), ("1", True), ("2", True)])

    def test_expand_returns_the_original_normalized_url(self):
        original_url = "https://example.com/a?b=c"
        code, is_new = shortener.shorten(original_url)

        self.assertTrue(is_new)
        self.assertEqual(shortener.expand(code), original_url)

    def test_expand_uses_the_exact_code_string(self):
        shortener.shorten("https://example.com")

        for code in ("00", "missing", ""):
            with self.subTest(code=code), self.assertRaises(KeyError):
                shortener.expand(code)

    def test_uppercase_http_scheme_is_accepted(self):
        code, is_new = shortener.shorten("HTTPS://example.com")

        self.assertEqual(code, "0")
        self.assertTrue(is_new)

    def test_invalid_urls_raise_value_error(self):
        invalid_urls = (
            "",
            " \t ",
            None,
            123,
            "example.com",
            "ftp://example.com",
            "javascript:alert(1)",
            "http://",
            "http://:80",
            "https://exa mple.com",
            "https://example.com/a\tb",
            "https://example.com/path\ninjected",
            "https://例え.テスト",
        )

        for url in invalid_urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                shortener.shorten(url)

    def test_url_length_limit_includes_2048_and_rejects_2049(self):
        prefix = "https://example.com/"
        accepted_url = prefix + "a" * (2048 - len(prefix))
        rejected_url = accepted_url + "a"

        self.assertEqual(len(accepted_url), 2048)
        self.assertTrue(shortener.shorten(accepted_url)[1])
        with self.assertRaises(ValueError):
            shortener.shorten(rejected_url)


if __name__ == "__main__":
    unittest.main()
