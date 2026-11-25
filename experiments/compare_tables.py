"""Compare separate chaining and linear probing on identical URL keys."""

import csv
from math import ceil
from pathlib import Path
from random import Random

from experiments.probe_experiment import CAPACITY, SEED, random_url
from src.hash_table import HashTable
from src.linear_probing_hash_table import LinearProbingHashTable


LOAD_FACTORS = tuple(step / 10 for step in range(1, 10))
OUTPUT_DIR = Path(__file__).resolve().parent
ComparisonRow = tuple[float, float, int, float, float, float, float]


def _chain_probes(table: HashTable[str], key: str) -> int:
    bucket = table._buckets[table._bucket_index(key)]
    for comparisons, (stored_key, _) in enumerate(bucket, start=1):
        if stored_key == key:
            return comparisons
    return len(bucket)


def run_comparison(
    capacity: int = CAPACITY,
    load_factors: tuple[float, ...] = LOAD_FACTORS,
) -> list[ComparisonRow]:
    if capacity < 1:
        raise ValueError("capacity must be positive")

    generator = Random(SEED)
    chain_table: HashTable[str] = HashTable(capacity, max_load=None)
    linear_table: LinearProbingHashTable[str] = LinearProbingHashTable(
        capacity, max_load=None
    )
    inserted_urls: list[str] = []
    rows = []

    for requested_alpha in load_factors:
        if not 0 < requested_alpha < 1:
            raise ValueError("load factors must be between 0 and 1")
        target_count = round(requested_alpha * capacity)
        if target_count < 1:
            raise ValueError("capacity is too small for the requested load factors")

        while len(inserted_urls) < target_count:
            url = random_url(generator)
            if url not in chain_table:
                chain_table.put(url, url)
                linear_table.put(url, url)
                inserted_urls.append(url)

        chain_success = 0
        linear_success = 0
        for url in inserted_urls:
            if chain_table.get(url) != url or linear_table.get(url) != url:
                raise RuntimeError(f"inserted URL was not found: {url}")
            chain_success += _chain_probes(chain_table, url)
            linear_success += len(linear_table.probe_indices(url))

        chain_failure = 0
        linear_failure = 0
        for _ in range(target_count):
            url = random_url(generator)
            while url in chain_table:
                url = random_url(generator)
            if chain_table.get(url) is not None or linear_table.get(url) is not None:
                raise RuntimeError(f"uninserted URL unexpectedly found: {url}")
            chain_failure += _chain_probes(chain_table, url)
            linear_failure += len(linear_table.probe_indices(url))

        actual_alpha = target_count / capacity
        rows.append(
            (
                requested_alpha,
                actual_alpha,
                target_count,
                chain_success / target_count,
                linear_success / target_count,
                chain_failure / target_count,
                linear_failure / target_count,
            )
        )

    return rows


def draw_svg(rows: list[ComparisonRow]) -> str:
    width, height = 960, 560
    left, right, top, bottom = 82, 30, 55, 75
    plot_width = width - left - right
    plot_height = height - top - bottom
    maximum = max(
        max(row[index] for row in rows)
        for index in (3, 4, 5, 6)
    )
    max_probes = max(1, ceil(maximum / 5) * 5)

    def x_position(alpha: float) -> float:
        return left + alpha * plot_width

    def y_position(probes: float) -> float:
        return top + (max_probes - probes) / max_probes * plot_height

    series = (
        ("Chain success", 3, "#1769aa", "solid"),
        ("Linear success", 4, "#1769aa", "dash"),
        ("Chain failure", 5, "#d1495b", "solid"),
        ("Linear failure", 6, "#d1495b", "dash"),
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">',
        "<title>Separate chaining and linear probing comparison</title>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<g font-family="sans-serif" fill="#222">',
        f'<text x="{width / 2}" y="28" text-anchor="middle" '
        'font-size="20">Probe counts by collision strategy</text>',
    ]

    for tick in range(6):
        probes = max_probes * tick / 5
        y = y_position(probes)
        parts.extend(
            [
                f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" '
                f'y2="{y:.1f}" stroke="#ddd"/>',
                f'<text x="{left - 12}" y="{y + 5:.1f}" '
                f'text-anchor="end" font-size="12">{probes:.0f}</text>',
            ]
        )
    for tick in range(11):
        alpha = tick / 10
        x = x_position(alpha)
        parts.extend(
            [
                f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" '
                f'y2="{height - bottom}" stroke="#eee"/>',
                f'<text x="{x:.1f}" y="{height - bottom + 20}" '
                f'text-anchor="middle" font-size="10">{alpha:.1f}</text>',
            ]
        )

    parts.extend(
        [
            f'<line x1="{left}" y1="{top}" x2="{left}" '
            f'y2="{height - bottom}" stroke="#333"/>',
            f'<line x1="{left}" y1="{height - bottom}" '
            f'x2="{width - right}" y2="{height - bottom}" stroke="#333"/>',
            f'<text x="{left + plot_width / 2}" y="{height - 20}" '
            'text-anchor="middle" font-size="14">Load factor (α)</text>',
            f'<text x="20" y="{top + plot_height / 2}" '
            f'transform="rotate(-90 20 {top + plot_height / 2})" '
            'text-anchor="middle" font-size="14">Average probes</text>',
        ]
    )

    for series_index, (label, column, color, style) in enumerate(series):
        points = " ".join(
            f"{x_position(row[1]):.1f},{y_position(row[column]):.1f}"
            for row in rows
        )
        dash = ' stroke-dasharray="6 4"' if style == "dash" else ""
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" '
            f'stroke-width="2"{dash}/>'
        )
        legend_y = 68 + series_index * 20
        parts.extend(
            [
                f'<line x1="{width - 250}" y1="{legend_y}" '
                f'x2="{width - 220}" y2="{legend_y}" stroke="{color}" '
                f'stroke-width="2"{dash}/>',
                f'<text x="{width - 212}" y="{legend_y + 4}" '
                f'font-size="12">{label}</text>',
            ]
        )

    parts.extend(["</g>", "</svg>"])
    return "\n".join(parts) + "\n"


def save_results(rows: list[ComparisonRow]) -> None:
    with (OUTPUT_DIR / "comparison.csv").open(
        "w", newline="", encoding="utf-8"
    ) as result_file:
        writer = csv.writer(result_file, lineterminator="\n")
        writer.writerow(
            (
                "requested_alpha",
                "actual_alpha",
                "entries",
                "chaining_success",
                "linear_success",
                "chaining_failure",
                "linear_failure",
            )
        )
        for row in rows:
            writer.writerow(
                (
                    f"{row[0]:.1f}",
                    f"{row[1]:.6f}",
                    row[2],
                    *(f"{value:.6f}" for value in row[3:]),
                )
            )
    (OUTPUT_DIR / "comparison.svg").write_text(
        draw_svg(rows), encoding="utf-8"
    )


def main() -> None:
    rows = run_comparison()
    save_results(rows)
    print(
        "alpha actual entries chain(success/failure) "
        "linear(success/failure)"
    )
    for row in rows:
        print(
            f"{row[0]:4.1f} {row[1]:6.3f} {row[2]:7d} "
            f"{row[3]:8.4f}/{row[5]:8.4f} "
            f"{row[4]:8.4f}/{row[6]:8.4f}"
        )
    print(f"Saved {OUTPUT_DIR / 'comparison.csv'}")
    print(f"Saved {OUTPUT_DIR / 'comparison.svg'}")


if __name__ == "__main__":
    main()
