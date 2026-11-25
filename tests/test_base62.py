import unittest

from src.base62 import decode, encode


class Base62Tests(unittest.TestCase):
    def test_encode_zero(self):
        self.assertEqual(encode(0), "0")

    def test_encode_uses_expected_alphabet_order(self):
        self.assertEqual(encode(61), "Z")
        self.assertEqual(encode(62), "10")

    def test_round_trip_large_integer(self):
        number = 2**128
        self.assertEqual(decode(encode(number)), number)

    def test_decode_accepts_leading_zeroes(self):
        self.assertEqual(decode("000a"), 10)

    def test_encode_rejects_negative_numbers(self):
        with self.assertRaises(ValueError):
            encode(-1)

    def test_encode_rejects_non_integers(self):
        with self.assertRaises(TypeError):
            encode(True)

    def test_decode_rejects_empty_or_invalid_strings(self):
        for value in ("", "a-b"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                decode(value)

    def test_decode_rejects_non_strings(self):
        with self.assertRaises(TypeError):
            decode(1)


if __name__ == "__main__":
    unittest.main()
