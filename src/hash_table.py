"""A string-keyed hash table using separate chaining."""

from typing import Generic, TypeVar


ValueT = TypeVar("ValueT")


class HashTable(Generic[ValueT]):
    """Store values under string keys with dynamically resized buckets."""

    def __init__(
        self, capacity: int = 8, max_load: float | None = 0.75
    ) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        if max_load is not None and max_load <= 0:
            raise ValueError("max_load must be positive or None")

        self._capacity = capacity
        self._max_load = max_load
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
        if (
            self._max_load is not None
            and self._size > self._capacity * self._max_load
        ):
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

    def snapshot_buckets(self) -> tuple[tuple[tuple[str, ValueT], ...], ...]:
        """Return an immutable snapshot of the bucket chains."""
        return tuple(tuple(bucket) for bucket in self._buckets)
