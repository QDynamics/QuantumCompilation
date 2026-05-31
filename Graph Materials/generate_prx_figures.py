from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(__file__).resolve().parent / ".matplotlib-cache"),
)

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter


ROOT = Path(__file__).resolve().parents[1]
GRAPH_DIR = ROOT / "Graph Materials"
RESEARCH_DIR = ROOT / "ucc" / "research"

SIZE_ORDER = [4000, 10000, 20000, 50000, 100000]
SIZE_LABELS = ["4k", "10k", "20k", "50k", "100k"]

COLORS = {
    "semantic": "#0072B2",
    "qiskit": "#D55E00",
    "pyzx": "#009E73",
    "tket": "#CC79A7",
    "baseline": "#E69F00",
    "no_ir": "#666666",
    "timeout": "#990000",
}


def _clean_int(value: object) -> int | None:
    if value is None:
        return None
    text = str(value).strip().replace("`", "")
    if text in {"", "-", "timeout"} or text.startswith(">"):
        return None
    text = text.replace(",", "")
    try:
        return int(float(text))
    except ValueError:
        return None


def _parse_markdown_table(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    headers: list[str] | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if headers is None:
            headers = cells
            continue
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def _format_k(value: float, _pos: object = None) -> str:
    if value >= 1000:
        return f"{value / 1000:g}k"
    return f"{value:g}"


def _format_int(value: float, _pos: object = None) -> str:
    if value >= 1000:
        return f"{int(value):,}"
    return f"{int(value)}"


def _style_axes(ax: plt.Axes) -> None:
    ax.grid(True, which="major", color="#d0d0d0", linewidth=0.8, alpha=0.8)
    ax.grid(True, which="minor", color="#e8e8e8", linewidth=0.5, alpha=0.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xticks(SIZE_ORDER)
    ax.set_xticklabels(SIZE_LABELS)


def _save(fig: plt.Figure, basename: str) -> None:
    for suffix in ("png", "pdf"):
        path = GRAPH_DIR / f"{basename}.{suffix}"
        fig.savefig(path, dpi=300, bbox_inches="tight")
        print(f"wrote {path}")
    plt.close(fig)


def _plot_with_timeouts(
    ax: plt.Axes,
    x_values: list[int],
    y_values: list[int | None],
    statuses: list[str],
    *,
    label: str,
    color: str,
    marker: str,
    timeout_y: int,
    linestyle: str = "-",
    show_label: bool = True,
    timeout_x_scale: float = 1.0,
) -> None:
    ok_x = [x for x, y, s in zip(x_values, y_values, statuses) if y is not None and s == "ok"]
    ok_y = [y for y, s in zip(y_values, statuses) if y is not None and s == "ok"]
    if ok_x:
        ax.plot(
            ok_x,
            ok_y,
            marker=marker,
            color=color,
            linestyle=linestyle,
            linewidth=2.4,
            markersize=7,
            label=label if show_label else None,
        )

    timeout_x = [x for x, y, s in zip(x_values, y_values, statuses) if s == "timeout" or y is None]
    if timeout_x:
        ax.scatter(
            [x * timeout_x_scale for x in timeout_x],
            [timeout_y] * len(timeout_x),
            marker="x",
            s=82,
            linewidths=2.2,
            color=color,
            alpha=0.95,
        )


def _legend_handle(label: str, color: str, marker: str, linestyle: str = "-") -> Line2D:
    return Line2D(
        [0],
        [0],
        color=color,
        marker=marker,
        linestyle=linestyle,
        linewidth=2.4,
        markersize=7,
        label=label,
    )


def _timeout_handle() -> Line2D:
    return Line2D(
        [0],
        [0],
        color="#555555",
        marker="x",
        linestyle="None",
        markersize=8,
        markeredgewidth=2.2,
        label="timeout, plotted at top band",
    )


def generate_fourier_separation() -> None:
    data = json.loads((RESEARCH_DIR / "noninverse_phase_ladder_scaling_results.json").read_text())
    family = data["fourier_phase_sandwich"]

    methods = [
        ("optimized_ucc", "Semantic UCC", COLORS["semantic"], "o", "-"),
        ("qiskit_opt3", "Qiskit opt3", COLORS["qiskit"], "^", "-"),
        ("pyzx_opt", "PyZX pipeline", COLORS["pyzx"], "s", "-"),
        ("tket_full_peephole", "TKET FullPeephole", COLORS["tket"], "D", "--"),
    ]

    timeout_y = 250_000
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    timeout_offsets = {
        "optimized_ucc": 1.0,
        "qiskit_opt3": 0.94,
        "pyzx_opt": 1.0,
        "tket_full_peephole": 1.06,
    }
    for method, label, color, marker, linestyle in methods:
        y_values: list[int | None] = []
        statuses: list[str] = []
        for size in SIZE_ORDER:
            result = family[str(size)][method]
            status = result.get("status", "unknown")
            statuses.append(status)
            output = result.get("output") or {}
            y_values.append(output.get("total_gates") if status == "ok" else None)
        _plot_with_timeouts(
            ax,
            SIZE_ORDER,
            y_values,
            statuses,
            label=label,
            color=color,
            marker=marker,
            timeout_y=timeout_y,
            linestyle=linestyle,
            show_label=False,
            timeout_x_scale=timeout_offsets[method],
        )

    ax.axhline(timeout_y, color="#9a9a9a", linestyle=":", linewidth=1.1)
    ax.text(4100, timeout_y * 1.04, "timeout markers", fontsize=9, color="#555555")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylim(25, 420_000)
    ax.set_xlabel("Requested input gates")
    ax.set_ylabel("Compiled output gates")
    ax.set_title("Fourier-layer separation on $H D^r H$")
    ax.yaxis.set_major_formatter(FuncFormatter(_format_int))
    _style_axes(ax)
    handles = [
        _legend_handle(label, color, marker, linestyle)
        for _, label, color, marker, linestyle in methods
    ]
    handles.append(_timeout_handle())
    ax.legend(
        handles=handles,
        frameon=False,
        fontsize=8,
        ncol=3,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
        columnspacing=1.1,
        handletextpad=0.5,
    )
    fig.subplots_adjust(bottom=0.26)
    _save(fig, "01_fourier_separation")


def _resource_rows() -> dict[tuple[int, str], dict[str, str]]:
    rows = _parse_markdown_table(RESEARCH_DIR / "resource_consequence_results.md")
    indexed: dict[tuple[int, str], dict[str, str]] = {}
    for row in rows:
        requested = _clean_int(row["Requested Gates"])
        if requested is None:
            continue
        indexed[(requested, row["Method"])] = row
    return indexed


def generate_resource_consequence() -> None:
    rows = _resource_rows()
    methods = [
        ("semantic_first", "Semantic first", COLORS["semantic"], "o"),
        ("materialize_first_qiskit_opt3", "Qiskit materialize first", COLORS["qiskit"], "^"),
        ("materialize_first_baseline_ucc", "No-Fourier UCC", COLORS["no_ir"], "s"),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.4), sharex=True)
    panels = [
        (axes[0], "RZ/Rot Count", "Arbitrary rotations", 70_000),
        (axes[1], "T-Proxy (1e-10)", "$T_{10^{-10}}$ proxy", 6_000_000),
    ]

    for ax, column, ylabel, timeout_y in panels:
        timeout_offsets = {
            "semantic_first": 1.0,
            "materialize_first_qiskit_opt3": 0.96,
            "materialize_first_baseline_ucc": 1.04,
        }
        for method, label, color, marker in methods:
            y_values: list[int | None] = []
            statuses: list[str] = []
            for size in SIZE_ORDER:
                row = rows.get((size, method), {})
                status = (row.get("Status") or "timeout").replace("`", "")
                statuses.append(status)
                y_values.append(_clean_int(row.get(column)) if status == "ok" else None)
            _plot_with_timeouts(
                ax,
                SIZE_ORDER,
                y_values,
                statuses,
                label=label,
                color=color,
                marker=marker,
                timeout_y=timeout_y,
                show_label=False,
                timeout_x_scale=timeout_offsets[method],
            )
        ax.axhline(timeout_y, color="#9a9a9a", linestyle=":", linewidth=1.1)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Requested input gates")
        ax.set_ylabel(ylabel)
        ax.yaxis.set_major_formatter(FuncFormatter(_format_int))
        _style_axes(ax)

    axes[0].set_title("Rotation multiplicity")
    axes[1].set_title("Clifford+$T$ proxy inflation")
    handles = [
        _legend_handle(label, color, marker)
        for _, label, color, marker in methods
    ]
    handles.append(_timeout_handle())
    fig.legend(
        handles=handles,
        frameon=False,
        fontsize=8,
        ncol=4,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.02),
        columnspacing=1.0,
        handletextpad=0.5,
    )
    fig.suptitle("Resource consequence of materializing before semantic aggregation", y=1.03)
    fig.tight_layout(rect=(0, 0.11, 1, 1))
    _save(fig, "02_resource_consequence")


def _ablation_rows() -> dict[tuple[int, str], dict[str, str]]:
    rows = _parse_markdown_table(RESEARCH_DIR / "fourier_layer_ablation_results.md")
    indexed: dict[tuple[int, str], dict[str, str]] = {}
    for row in rows:
        requested = _clean_int(row["Requested Gates"])
        if requested is None:
            continue
        indexed[(requested, row["Method"])] = row
    return indexed


def generate_fourier_ablation() -> None:
    rows = _ablation_rows()
    methods = [
        ("optimized_ucc_full", "Fourier-enabled UCC", COLORS["semantic"], "o"),
        ("optimized_ucc_no_fourier_layer_ir", "No Fourier-layer IR", COLORS["no_ir"], "s"),
        ("qiskit_opt3", "Qiskit opt3", COLORS["qiskit"], "^"),
    ]
    timeout_y = 80_000
    fig, ax = plt.subplots(figsize=(7.2, 4.6))

    timeout_offsets = {
        "optimized_ucc_full": 1.0,
        "optimized_ucc_no_fourier_layer_ir": 0.96,
        "qiskit_opt3": 1.04,
    }
    for method, label, color, marker in methods:
        y_values: list[int | None] = []
        statuses: list[str] = []
        for size in SIZE_ORDER:
            row = rows.get((size, method), {})
            status = (row.get("Status") or "timeout").replace("`", "")
            statuses.append(status)
            y_values.append(_clean_int(row.get("Output Gates")) if status == "ok" else None)
        _plot_with_timeouts(
            ax,
            SIZE_ORDER,
            y_values,
            statuses,
            label=label,
            color=color,
            marker=marker,
            timeout_y=timeout_y,
            show_label=False,
            timeout_x_scale=timeout_offsets[method],
        )

    ax.axvspan(18_000, 22_000, color="#999999", alpha=0.15)
    ax.text(20_000, 120, "20k all-timeout row\n(runtime caveat)", ha="center", va="bottom", fontsize=8)
    ax.axhline(timeout_y, color="#9a9a9a", linestyle=":", linewidth=1.1)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylim(25, 140_000)
    ax.set_xlabel("Requested input gates")
    ax.set_ylabel("Compiled output gates")
    ax.set_title("Fourier-layer semantic-path ablation")
    ax.yaxis.set_major_formatter(FuncFormatter(_format_int))
    _style_axes(ax)
    handles = [
        _legend_handle(label, color, marker)
        for _, label, color, marker in methods
    ]
    handles.append(_timeout_handle())
    ax.legend(
        handles=handles,
        frameon=False,
        fontsize=8,
        ncol=2,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
        columnspacing=1.0,
        handletextpad=0.5,
    )
    fig.subplots_adjust(bottom=0.26)
    _save(fig, "03_fourier_ablation")


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "legend.fontsize": 8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    generate_fourier_separation()
    generate_resource_consequence()
    generate_fourier_ablation()


if __name__ == "__main__":
    main()
