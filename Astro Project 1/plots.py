#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import os
import re


try:
    # Ensure Matplotlib writes caches/configs into the project (sandbox-friendly).
    _mpl_dir = Path(__file__).resolve().parent / ".mplconfig"
    _mpl_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(_mpl_dir))

    import matplotlib  # type: ignore[import-not-found]

    matplotlib.use("Agg")  # headless rendering
    import matplotlib.pyplot as plt  # type: ignore[import-not-found]
except ImportError as e:
    project_dir = Path(__file__).resolve().parent
    raise SystemExit(
        "matplotlib is required to run plots.\n\n"
        "You are likely running the system Python (e.g. /usr/bin/python3) instead of the project's virtualenv.\n\n"
        "Run with the project venv:\n"
        f"  {project_dir}/.venv/bin/python {project_dir}/plots\n\n"
        "If you still need to install deps into the venv:\n"
        f"  python3 -m venv {project_dir}/.venv\n"
        f"  {project_dir}/.venv/bin/python -m pip install matplotlib numpy"
    ) from e


from main import DEFAULT_ASTROPHYSICS_KEYWORDS, load_all_papers  # noqa: E402


def _normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _paper_text(paper) -> str:
    # `Paper` has `title` and `abstract`; we treat them as one searchable blob.
    return _normalize_space(paper.get_searchable_text())


def _count_occurrences(text: str, keyword: str) -> int:
    """
    Count occurrences of `keyword` in `text`.

    - For single-word keywords, uses word boundaries (avoids matching inside other words).
    - For multi-word keywords (phrases), counts simple case-insensitive substring matches
      on normalized whitespace.
    """
    text_norm = _normalize_space(text).lower()
    kw_norm = _normalize_space(keyword).lower()

    if not kw_norm:
        return 0

    if " " not in kw_norm and kw_norm.isalnum():
        # Whole-word match for plain single tokens like "galaxy"
        pattern = re.compile(rf"\b{re.escape(kw_norm)}\b", re.IGNORECASE)
        return len(pattern.findall(text_norm))

    # Phrase match (e.g., "black hole", "dark matter")
    return text_norm.count(kw_norm)


@dataclass(frozen=True)
class KeywordStats:
    keywords: List[str]
    paper_labels: List[str]
    # matrix[p][k] = occurrences of keyword k in paper p (title+abstract)
    matrix: List[List[int]]

    def total_occurrences(self) -> List[int]:
        return [sum(self.matrix[p][k] for p in range(len(self.matrix))) for k in range(len(self.keywords))]

    def papers_with_keyword(self) -> List[int]:
        return [sum(1 for p in range(len(self.matrix)) if self.matrix[p][k] > 0) for k in range(len(self.keywords))]


def build_keyword_stats(papers: Sequence, keywords: Sequence[str]) -> KeywordStats:
    paper_labels: List[str] = []
    matrix: List[List[int]] = []

    for i, paper in enumerate(papers, start=1):
        label = f"paper{i}"
        title = (paper.title or "").strip()
        if title:
            label = f"{label}: {title[:60]}{'…' if len(title) > 60 else ''}"
        paper_labels.append(label)

        text = _paper_text(paper)
        row = [_count_occurrences(text, kw) for kw in keywords]
        matrix.append(row)

    return KeywordStats(keywords=list(keywords), paper_labels=paper_labels, matrix=matrix)


def _top_n_indices(values: Sequence[int], n: int) -> List[int]:
    return sorted(range(len(values)), key=lambda i: values[i], reverse=True)[:n]


def plot_top_keywords_bar(
    *,
    keywords: Sequence[str],
    values: Sequence[int],
    ylabel: str,
    title: str,
    outpath: Path,
    top_n: int = 20,
) -> None:
    idx = _top_n_indices(values, top_n)
    top_keywords = [keywords[i] for i in idx]
    top_values = [values[i] for i in idx]

    plt.figure(figsize=(12, 7))
    plt.barh(range(len(top_keywords)), top_values)
    plt.yticks(range(len(top_keywords)), top_keywords)
    plt.gca().invert_yaxis()
    plt.xlabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(outpath, dpi=200)
    plt.close()


def plot_keyword_heatmap(
    *,
    stats: KeywordStats,
    outpath: Path,
    top_n_keywords: int = 30,
    use_binary_presence: bool = True,
) -> None:
    """
    Heatmap of papers (rows) x keywords (columns).
    """
    totals = stats.papers_with_keyword() if use_binary_presence else stats.total_occurrences()
    k_idx = _top_n_indices(totals, top_n_keywords)

    # Build reduced matrix (binary or counts)
    reduced = []
    for p in range(len(stats.matrix)):
        row = []
        for k in k_idx:
            v = stats.matrix[p][k]
            row.append(1 if (use_binary_presence and v > 0) else v)
        reduced.append(row)

    # Import numpy only if we’re making the heatmap (keeps the script lightweight).
    try:
        import numpy as np  # type: ignore[import-not-found]
    except ImportError as e:
        project_dir = Path(__file__).resolve().parent
        raise SystemExit(
            "numpy is required for the heatmap plot.\n\n"
            "Install it into the project venv:\n"
            f"  {project_dir}/.venv/bin/python -m pip install numpy"
        ) from e

    data = np.array(reduced, dtype=float)

    plt.figure(figsize=(max(12, len(k_idx) * 0.4), max(6, len(stats.paper_labels) * 0.45)))
    im = plt.imshow(data, aspect="auto", interpolation="nearest")
    plt.colorbar(im, label=("presence (0/1)" if use_binary_presence else "occurrences"))

    plt.yticks(range(len(stats.paper_labels)), stats.paper_labels)
    plt.xticks(range(len(k_idx)), [stats.keywords[i] for i in k_idx], rotation=45, ha="right")
    plt.title("Keyword matches by paper (top keywords)")
    plt.tight_layout()
    plt.savefig(outpath, dpi=200)
    plt.close()


def main() -> int:
    out_dir = Path(__file__).resolve().parent / "plots_output_new"
    out_dir.mkdir(parents=True, exist_ok=True)

    papers = load_all_papers()
    if not papers:
        print("No papers found. Expected paper1.txt ... paper10.txt next to main.py.")
        return 1

    keywords = DEFAULT_ASTROPHYSICS_KEYWORDS
    stats = build_keyword_stats(papers, keywords)

    paper_counts = stats.papers_with_keyword()
    occ_counts = stats.total_occurrences()

    plot_top_keywords_bar(
        keywords=keywords,
        values=paper_counts,
        ylabel="# of papers containing keyword",
        title="Top keywords (by papers containing them)",
        outpath=out_dir / "top_keywords_by_papers.png",
        top_n=25,
    )

    plot_top_keywords_bar(
        keywords=keywords,
        values=occ_counts,
        ylabel="total occurrences across papers",
        title="Top keywords (by total occurrences)",
        outpath=out_dir / "top_keywords_by_occurrences.png",
        top_n=25,
    )

    plot_keyword_heatmap(
        stats=stats,
        outpath=out_dir / "keyword_heatmap_presence.png",
        top_n_keywords=30,
        use_binary_presence=True,
    )

    print(f"Wrote plots to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
