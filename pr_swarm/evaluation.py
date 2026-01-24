"""Evaluation utilities for assessing the quality of PR pitch drafts.

This module provides simple scripts to compute send‑readiness metrics and
extraction accuracy based on human‑annotated labels. The evaluation is
performed offline after a run by reading the CSV summaries in the
``outputs`` directory.
"""

from __future__ import annotations

import argparse
from typing import Optional

import pandas as pd


def evaluate_send_readiness(summary_path: str) -> float:
    """Calculate the proportion of send‑ready pitches based on manual labels.

    The summary CSV must contain a ``manual_label`` column where human
    reviewers mark a pitch as 1 (send‑ready) or 0 (needs work). Rows
    without a label are ignored.

    Returns
    -------
    float
        The percentage of send‑ready pitches as a value between 0 and 1.
    """
    df = pd.read_csv(summary_path)
    labeled = df.dropna(subset=["manual_label"])
    if labeled.empty:
        print("No manual labels found. Please fill in the 'manual_label' column in the CSV.")
        return 0.0
    labeled["manual_label"] = labeled["manual_label"].astype(int)
    total = len(labeled)
    send_ready = labeled["manual_label"].sum()
    ratio = send_ready / total
    print(f"Send‑ready pitches: {send_ready}/{total} ({ratio*100:.2f}%)")
    return ratio


def main(args: Optional[argparse.Namespace] = None) -> None:
    parser = argparse.ArgumentParser(description="Evaluate PR pitch drafts")
    parser.add_argument(
        "--pitch_summary",
        type=str,
        required=True,
        help="Path to the pitch_summary.csv produced by the run",
    )
    parsed_args = parser.parse_args(args=args)
    evaluate_send_readiness(parsed_args.pitch_summary)


if __name__ == "__main__":
    main()