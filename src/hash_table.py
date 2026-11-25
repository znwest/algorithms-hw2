"""A string-keyed hash table using separate chaining."""

from typing import Generic, TypeVar


ValueT = TypeVar("ValueT")


class HashTable(Generic[ValueT]):
    """Store values under string keys with dynamically resized buckets."""

    def __init__(self) -> None:
        self._capacity = 8
        self._buckets: list[list[tuple[str, ValueT]]] = [
            [] for _ in range(self._capacity)
        ]
        self._size = 0

    def _bucket_index(self, key: str) -> int:
        index = 0
        for character in key:
            index = (index * 31 + ord(character)) % self._capacity
        return index

    def _find(self, key: str) -> tuple[list[tuple[str, ValueT]], int] | None:
        bucket = self._buckets[self._bucket_index(key)]
        for position, (stored_key, _) in enumerate(bucket):
            if stored_key == key:
                return bucket, position
        return None

    def put(self, key: str, value: ValueT) -> None:
        """Insert or update a key-value pair."""
        found = self._find(key)
        if found is not None:
            bucket, position = found
            bucket[position] = (key, value)
            return

        self._buckets[self._bucket_index(key)].append((key, value))
        self._size += 1
        if self._size * 4 > self._capacity * 3:
            self._resize()

    def _resize(self) -> None:
        old_buckets = self._buckets
        self._capacity *= 2
        self._buckets = [[] for _ in range(self._capacity)]
        for bucket in old_buckets:
            for key, value in bucket:
                self._buckets[self._bucket_index(key)].append((key, value))

    def get(self, key: str) -> ValueT | None:
        """Return the value for key, or None when key is absent."""
        found = self._find(key)
        if found is None:
            return None
        bucket, position = found
        return bucket[position][1]

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return self._find(key) is not None

    def __len__(self) -> int:
        return self._size
