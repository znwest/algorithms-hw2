"""A string-keyed hash table using linear probing."""

from typing import Generic, TypeVar

from src.hash_table import _horner_hash


ValueT = TypeVar("ValueT")


class LinearProbingHashTable(Generic[ValueT]):
    """Store values in an open-addressed table with linear probing."""

    def __init__(
        self, capacity: int = 8, max_load: float | None = 0.75
    ) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        if max_load is not None and max_load <= 0:
            raise ValueError("max_load must be positive or None")

        self._capacity = capacity
        self._max_load = max_load
        self._slots: list[tuple[str, ValueT] | None] = [
            None for _ in range(capacity)
        ]
        self._size = 0

    def _home_index(self, key: str) -> int:
        return _horner_hash(key, self._capacity)

    def _find_slot(self, key: str) -> tuple[int | None, bool]:
        home = self._home_index(key)
        for offset in range(self._capacity):
            index = (home + offset) % self._capacity
            entry = self._slots[index]
            if entry is None:
                return index, False
            if entry[0] == key:
                return index, True
        return None, False

    def put(self, key: str, value: ValueT) -> None:
        """Insert or update a key-value pair."""
        index, found = self._find_slot(key)
        if index is None:
            raise OverflowError("linear-probing hash table is full")
        if found:
            self._slots[index] = (key, value)
            return

        self._slots[index] = (key, value)
        self._size += 1
        if (
            self._max_load is not None
            and self._size > self._capacity * self._max_load
        ):
            self._resize()

    def _resize(self) -> None:
        old_slots = self._slots
        self._capacity *= 2
        self._slots = [None for _ in range(self._capacity)]
        self._size = 0
        for entry in old_slots:
            if entry is None:
                continue
            index, _ = self._find_slot(entry[0])
            if index is None:
                raise RuntimeError("resized table unexpectedly has no free slot")
            self._slots[index] = entry
            self._size += 1

    def get(self, key: str) -> ValueT | None:
        """Return the value for key, or None when key is absent."""
        index, found = self._find_slot(key)
        if not found or index is None:
            return None
        entry = self._slots[index]
        if entry is None:
            raise RuntimeError("located key is missing from its slot")
        return entry[1]

    def find(self, key: str) -> tuple[ValueT | None, int]:
        """Return (value or None, number of slots inspected)."""
        indices = self.probe_indices(key)
        entry = self._slots[indices[-1]]
        if entry is not None and entry[0] == key:
            return entry[1], len(indices)
        return None, len(indices)

    def load_factor(self) -> float:
        """Return entries / capacity."""
        return self._size / self._capacity

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        _, found = self._find_slot(key)
        return found

    def __len__(self) -> int:
        return self._size

    def probe_indices(self, key: str) -> tuple[int, ...]:
        """Return the slots inspected by a lookup for key."""
        home = self._home_index(key)
        indices = []
        for offset in range(self._capacity):
            index = (home + offset) % self._capacity
            indices.append(index)
            entry = self._slots[index]
            if entry is None or entry[0] == key:
                break
        return tuple(indices)

    def snapshot_slots(self) -> tuple[tuple[str, ValueT] | None, ...]:
        """Return an immutable snapshot of the table slots."""
        return tuple(self._slots)
