"""Compare separate-chaining probe counts with the topic 08 estimates."""

import csv
from pathlib import Path
from random import Random
import string

from src.hash_table import HashTable


CAPACITY = 4093
SEED = 20261125
LOAD_FACTORS = tuple(step / 4 for step in range(1, 17))
OUTPUT_DIR = Path(__file__).resolve().parent


def random_url(generator: Random) -> str:
    alphabet = string.ascii_lowercase + string.digits
    host = "".join(generator.choice(alphabet) for _ in range(16))
    path = "".join(generator.choice(alphabet) for _ in range(24))
    return f"https://{host}.example/{path}"


def count_node_comparisons(table: HashTable[str], key: str) -> int:
    """Count chain nodes inspected by a lookup for key."""
    bucket = table._buckets[table._bucket_index(key)]
    for comparisons, (stored_key, _) in enumerate(bucket, start=1):
        if stored_key == key:
            return comparisons
    return len(bucket)


def draw_svg(
    rows: list[tuple[float, float, int, float, float, float, float]],
) -> str:
    width, height = 960, 560
    left, right, top, bottom = 82, 30, 55, 75
    plot_width = width - left - right
    plot_height = height - top - bottom
    max_alpha, max_probes = 4.0, 5.0

    def x_position(alpha: float) -> float:
        return left + alpha / max_alpha * plot_width

    def y_position(probes: float) -> float:
        return top + (max_probes - probes) / max_probes * plot_height

    series = (
        ("Measured success", 3, "#1769aa", "solid"),
        ("Theory success", 4, "#1769aa", "dash"),
        ("Measured failure", 5, "#d1495b", "solid"),
        ("Theory failure", 6, "#d1495b", "dash"),
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">',
        "<title>Hash table probe counts by load factor</title>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<g font-family="sans-serif" fill="#222">',
        f'<text x="{width / 2}" y="28" text-anchor="middle" '
        'font-size="20">Separate-chaining probe counts</text>',
    ]

    for tick in range(6):
        y = y_position(float(tick))
        parts.extend(
            [
                f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" '
                f'y2="{y:.1f}" stroke="#ddd"/>',
                f'<text x="{left - 12}" y="{y + 5:.1f}" '
                f'text-anchor="end" font-size="12">{tick}</text>',
            ]
        )
    for tick in range(17):
        alpha = tick / 4
        x = x_position(alpha)
        parts.extend(
            [
                f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" '
                f'y2="{height - bottom}" stroke="#eee"/>',
                f'<text x="{x:.1f}" y="{height - bottom + 20}" '
                f'text-anchor="middle" font-size="10">{alpha:g}</text>',
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
            'text-anchor="middle" font-size="14">Average nodes compared</text>',
        ]
    )

    for index, (label, column, color, style) in enumerate(series):
        points = " ".join(
            f"{x_position(row[1]):.1f},{y_position(row[column]):.1f}"
            for row in rows
        )
        dash = ' stroke-dasharray="6 4"' if style == "dash" else ""
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" '
            f'stroke-width="2"{dash}/>'
        )
        legend_y = 68 + index * 20
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


def run_experiment() -> list[tuple[float, float, int, float, float, float, float]]:
    generator = Random(SEED)
    table: HashTable[str] = HashTable(capacity=CAPACITY, max_load=None)
    inserted_urls: list[str] = []
    rows = []

    for alpha in LOAD_FACTORS:
        target_count = round(alpha * CAPACITY)
        while len(inserted_urls) < target_count:
            url = random_url(generator)
            if url not in table:
                table.put(url, url)
                inserted_urls.append(url)

        success_comparisons = 0
        for url in inserted_urls:
            if table.get(url) != url:
                raise RuntimeError(f"inserted URL was not found: {url}")
            success_comparisons += count_node_comparisons(table, url)

        failure_comparisons = 0
        for _ in range(target_count):
            url = random_url(generator)
            while url in table:
                url = random_url(generator)
            if table.get(url) is not None:
                raise RuntimeError(f"uninserted URL unexpectedly found: {url}")
            failure_comparisons += count_node_comparisons(table, url)

        actual_alpha = target_count / CAPACITY
        success_average = success_comparisons / target_count
        failure_average = failure_comparisons / target_count
        rows.append(
            (
                alpha,
                actual_alpha,
                target_count,
                success_average,
                1 + actual_alpha / 2,
                failure_average,
                actual_alpha,
            )
        )

    return rows


def save_results(
    rows: list[tuple[float, float, int, float, float, float, float]],
) -> None:
    csv_path = OUTPUT_DIR / "results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as result_file:
        writer = csv.writer(result_file, lineterminator="\n")
        writer.writerow(
            (
                "requested_alpha",
                "actual_alpha",
                "entries",
                "success_measured",
                "success_theory",
                "success_abs_error",
                "failure_measured",
                "failure_theory",
                "failure_abs_error",
            )
        )
        for (
            requested_alpha,
            actual_alpha,
            entries,
            success,
            success_theory,
            failure,
            failure_theory,
        ) in rows:
            writer.writerow(
                (
                    f"{requested_alpha:.2f}",
                    f"{actual_alpha:.6f}",
                    entries,
                    f"{success:.6f}",
                    f"{success_theory:.6f}",
                    f"{abs(success - success_theory):.6f}",
                    f"{failure:.6f}",
                    f"{failure_theory:.6f}",
                    f"{abs(failure - failure_theory):.6f}",
                )
            )

    (OUTPUT_DIR / "results.svg").write_text(
        draw_svg(rows), encoding="utf-8"
    )


def main() -> None:
    rows = run_experiment()
    save_results(rows)
    print(
        "alpha  actual   entries success(measured/theory) "
        "failure(measured/theory)"
    )
    for (
        alpha,
        actual_alpha,
        entries,
        success,
        success_theory,
        failure,
        failure_theory,
    ) in rows:
        print(
            f"{alpha:5.2f} {actual_alpha:7.4f} {entries:7d} "
            f"{success:8.4f}/{success_theory:8.4f} "
            f"{failure:8.4f}/{failure_theory:8.4f}"
        )
    print(f"Saved {OUTPUT_DIR / 'results.csv'}")
    print(f"Saved {OUTPUT_DIR / 'results.svg'}")


if __name__ == "__main__":
    main()
