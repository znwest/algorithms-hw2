"""Compare separate chaining and linear probing on identical URL keys."""

import csv
from math import log10
from pathlib import Path
from random import Random

from experiments.probe_experiment import CAPACITY, SEED, random_url
from src.hash_table import HashTable
from src.linear_probing_hash_table import LinearProbingHashTable


LOAD_FACTORS = tuple(step / 10 for step in range(1, 10))
OUTPUT_DIR = Path(__file__).resolve().parent
ComparisonRow = tuple[float, float, int, float, float, float, float]


def theory_chain_success(alpha: float) -> float:
    return 1 + alpha / 2


def theory_chain_failure(alpha: float) -> float:
    return alpha


def theory_linear_success(alpha: float) -> float:
    return (1 + 1 / (1 - alpha)) / 2


def theory_linear_failure(alpha: float) -> float:
    return (1 + 1 / (1 - alpha) ** 2) / 2


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
            chain_value, chain_cost = chain_table.find(url)
            linear_value, linear_cost = linear_table.find(url)
            if chain_value != url or linear_value != url:
                raise RuntimeError(f"inserted URL was not found: {url}")
            chain_success += chain_cost
            linear_success += linear_cost

        chain_failure = 0
        linear_failure = 0
        for _ in range(target_count):
            url = random_url(generator)
            while url in chain_table:
                url = random_url(generator)
            chain_value, chain_cost = chain_table.find(url)
            linear_value, linear_cost = linear_table.find(url)
            if chain_value is not None or linear_value is not None:
                raise RuntimeError(f"uninserted URL unexpectedly found: {url}")
            chain_failure += chain_cost
            linear_failure += linear_cost

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


CHAIN_COLOR = "#257de0"
LINEAR_COLOR = "#f47230"
TEXT_COLOR = "#222222"
MUTED_COLOR = "#666666"
Y_MIN, Y_MAX = 0.1, 100.0


def draw_svg(rows: list[ComparisonRow]) -> str:
    """Draw measured points and theory curves on one log-scale chart."""
    width, height = 960, 600
    left, right, top, bottom = 82, 170, 70, 80
    plot_width = width - left - right
    plot_height = height - top - bottom
    log_min, log_max = log10(Y_MIN), log10(Y_MAX)

    def x_position(alpha: float) -> float:
        return left + alpha * plot_width

    def y_position(cost: float) -> float:
        clipped = min(max(cost, Y_MIN), Y_MAX)
        return top + (log_max - log10(clipped)) / (log_max - log_min) * plot_height

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">',
        "<title>Separate chaining vs linear probing: measured and theory</title>",
        '<rect width="100%" height="100%" fill="white"/>',
        f'<g font-family="sans-serif" fill="{TEXT_COLOR}">',
        f'<text x="{left}" y="30" font-size="20">'
        "Search cost by load factor (capacity 4093, same keys)</text>",
        f'<text x="{left}" y="52" font-size="13" fill="{MUTED_COLOR}">'
        "Points: measured · Lines: theory · "
        "solid = successful search, dashed = unsuccessful search · log scale</text>",
    ]

    for exponent in range(-1, 3):
        for multiplier in (1, 2, 5):
            value = multiplier * 10 ** exponent
            if value > Y_MAX:
                continue
            y = y_position(value)
            major = multiplier == 1
            parts.append(
                f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_width}" '
                f'y2="{y:.1f}" stroke="{"#dddddd" if major else "#f0f0f0"}"/>'
            )
            label = f"{value:g}"
            parts.append(
                f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" '
                f'font-size="12" fill="{MUTED_COLOR}">{label}</text>'
            )
    for tick in range(11):
        alpha = tick / 10
        x = x_position(alpha)
        parts.append(
            f'<text x="{x:.1f}" y="{top + plot_height + 20}" '
            f'text-anchor="middle" font-size="12" fill="{MUTED_COLOR}">'
            f"{alpha:.1f}</text>"
        )
    parts.extend(
        [
            f'<line x1="{left}" y1="{top + plot_height}" '
            f'x2="{left + plot_width}" y2="{top + plot_height}" stroke="#999999"/>',
            f'<text x="{left + plot_width / 2}" y="{height - 25}" '
            'text-anchor="middle" font-size="14">Load factor α</text>',
            f'<text x="22" y="{top + plot_height / 2}" '
            f'transform="rotate(-90 22 {top + plot_height / 2})" '
            'text-anchor="middle" font-size="14">'
            "Average cost (chaining: nodes compared, linear: slots inspected)"
            "</text>",
        ]
    )

    curve_alphas = [step / 200 for step in range(16, 183)]  # 0.08 .. 0.91
    series = (
        ("Chaining success", 3, theory_chain_success, CHAIN_COLOR, False),
        ("Chaining failure", 5, theory_chain_failure, CHAIN_COLOR, True),
        ("Linear success", 4, theory_linear_success, LINEAR_COLOR, False),
        ("Linear failure", 6, theory_linear_failure, LINEAR_COLOR, True),
    )
    label_positions = []
    for label, column, theory, color, dashed in series:
        dash = ' stroke-dasharray="7 5"' if dashed else ""
        points = " ".join(
            f"{x_position(alpha):.1f},{y_position(theory(alpha)):.1f}"
            for alpha in curve_alphas
        )
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" '
            f'stroke-width="2" stroke-opacity="0.55"{dash}/>'
        )
        for row in rows:
            x, y = x_position(row[1]), y_position(row[column])
            if dashed:
                parts.append(
                    f'<rect x="{x - 4.5:.1f}" y="{y - 4.5:.1f}" width="9" '
                    f'height="9" fill="{color}" stroke="white" stroke-width="2"/>'
                )
            else:
                parts.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{color}" '
                    'stroke="white" stroke-width="2"/>'
                )
        label_positions.append([y_position(rows[-1][column]), label, color, dash])

    label_positions.sort()
    for index in range(1, len(label_positions)):
        if label_positions[index][0] - label_positions[index - 1][0] < 16:
            label_positions[index][0] = label_positions[index - 1][0] + 16
    for y, label, color, dash in label_positions:
        x = x_position(rows[-1][1]) + 12
        parts.extend(
            [
                f'<line x1="{x}" y1="{y:.1f}" x2="{x + 18}" y2="{y:.1f}" '
                f'stroke="{color}" stroke-width="3"{dash.replace("7 5", "5 3")}/>',
                f'<text x="{x + 20}" y="{y + 4:.1f}" font-size="13">{label}</text>',
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
                "chaining_success_theory",
                "linear_success_theory",
                "chaining_failure_theory",
                "linear_failure_theory",
            )
        )
        for row in rows:
            writer.writerow(
                (
                    f"{row[0]:.1f}",
                    f"{row[1]:.6f}",
                    row[2],
                    *(f"{value:.6f}" for value in row[3:]),
                    f"{theory_chain_success(row[1]):.6f}",
                    f"{theory_linear_success(row[1]):.6f}",
                    f"{theory_chain_failure(row[1]):.6f}",
                    f"{theory_linear_failure(row[1]):.6f}",
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
