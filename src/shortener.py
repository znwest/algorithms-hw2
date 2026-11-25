"""In-memory URL shortening service."""

from urllib.parse import urlparse

from src.base62 import encode
from src.hash_table import HashTable


_url_to_code: HashTable[str] = HashTable()
_code_to_url: HashTable[str] = HashTable()
_next_identifier = 0


def _normalize_and_validate(url: object) -> str:
    if not isinstance(url, str):
        raise ValueError("URL must be a string")

    normalized = url.strip()
    if not normalized:
        raise ValueError("URL must not be empty")
    if len(normalized) > 2048:
        raise ValueError("URL must be at most 2048 characters")
    if any(
        ord(character) > 127
        or ord(character) < 32
        or ord(character) == 127
        or character.isspace()
        for character in normalized
    ):
        raise ValueError("URL must contain only printable ASCII characters")

    try:
        parsed = urlparse(normalized)
        hostname = parsed.hostname
    except ValueError as error:
        raise ValueError("URL is invalid") from error

    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError("URL scheme must be HTTP or HTTPS")
    if not hostname:
        raise ValueError("URL must include a hostname")
    return normalized


def shorten(url: object) -> tuple[str, bool]:
    """Return a base62 code and whether a new mapping was created."""
    global _next_identifier

    normalized = _normalize_and_validate(url)
    existing_code = _url_to_code.get(normalized)
    if existing_code is not None:
        return existing_code, False

    code = encode(_next_identifier)
    _next_identifier += 1
    _url_to_code.put(normalized, code)
    _code_to_url.put(code, normalized)
    return code, True


def expand(code: object) -> str:
    """Return the URL stored for the exact code string."""
    if not isinstance(code, str):
        raise KeyError(code)
    url = _code_to_url.get(code)
    if url is None:
        raise KeyError(code)
    return url


def url_table_snapshot() -> tuple[tuple[tuple[str, str], ...], ...]:
    """Return a read-only snapshot of the URL-to-code table's bucket chains."""
    return _url_to_code.snapshot_buckets()
