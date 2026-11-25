"""In-memory URL shortening service."""

from urllib.parse import urlparse

from src.base62 import encode
from src.hash_table import HashTable
from src.linear_probing_hash_table import LinearProbingHashTable


TableClass = type[HashTable[str]] | type[LinearProbingHashTable[str]]

_url_to_code: HashTable[str] | LinearProbingHashTable[str]
_code_to_url: HashTable[str] | LinearProbingHashTable[str]
_chain_view: HashTable[str]
_linear_view: LinearProbingHashTable[str]
_next_identifier: int


def configure_table_type(table_class: TableClass = HashTable) -> None:
    """Reset the shortener and select its URL/code table implementation."""
    global _url_to_code, _code_to_url, _chain_view, _linear_view
    global _next_identifier

    if table_class not in (HashTable, LinearProbingHashTable):
        raise TypeError("table_class must be a supported hash table class")

    _url_to_code = table_class()
    _code_to_url = table_class()
    _chain_view = (
        _url_to_code if table_class is HashTable else HashTable()
    )
    _linear_view = (
        _url_to_code
        if table_class is LinearProbingHashTable
        else LinearProbingHashTable()
    )
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
    if _chain_view is not _url_to_code:
        _chain_view.put(normalized, code)
    if _linear_view is not _url_to_code:
        _linear_view.put(normalized, code)
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
    """Return a read-only snapshot of the separate-chaining URL table."""
    return _chain_view.snapshot_buckets()


def linear_table_snapshot() -> tuple[tuple[str, str] | None, ...]:
    """Return a read-only snapshot of the linear-probing URL table."""
    return _linear_view.snapshot_slots()


def linear_probe_indices(key: str) -> tuple[int, ...]:
    """Return the slots inspected when finding key in the linear-probing view."""
    return _linear_view.probe_indices(key)


configure_table_type()
