"""
spc.py — Statistical Process Control for OT Sentinel.

Calculates rolling baselines (mean ± 3σ) for device metrics and
detects out-of-control (OOC) conditions per Western Electric rules.
"""

from __future__ import annotations

import math
import statistics


def calculate_baseline(readings: list[dict], field: str) -> dict:
    """
    Calculate mean ± 3σ control limits for *field* across *readings*.

    Parameters
    ----------
    readings:
        List of metric dicts, each containing keys such as cpu_pct,
        mem_pct, temp_c, net_in_kbps, net_out_kbps, risk_score.
    field:
        The key to extract from each reading dict.

    Returns
    -------
    dict with keys: mean, stddev, ucl, lcl, n

    If fewer than 10 readings are present all numeric fields are None.
    UCL = mean + 3 * stddev
    LCL = max(0, mean - 3 * stddev)   — clamped to 0
    """
    n = len(readings)
    if n < 10:
        return {"mean": None, "stddev": None, "ucl": None, "lcl": None, "n": n}

    values = [float(r[field]) for r in readings]

    mean = statistics.mean(values)

    # Population stddev (σ), not sample stddev (s)
    # statistics.pstdev uses N denominator
    stddev = statistics.pstdev(values)

    ucl = mean + 3.0 * stddev
    lcl = max(0.0, mean - 3.0 * stddev)

    return {
        "mean": round(mean, 4),
        "stddev": round(stddev, 4),
        "ucl": round(ucl, 4),
        "lcl": round(lcl, 4),
        "n": n,
    }


def check_violations(current: dict, baseline: dict, field: str) -> bool:
    """
    Return True if current[field] falls outside the baseline control limits.

    Parameters
    ----------
    current:
        Dict containing at least *field*.
    baseline:
        Dict returned by calculate_baseline.
    field:
        Metric key to check.

    Returns False when baseline["ucl"] is None (not enough data yet).
    """
    if baseline["ucl"] is None:
        return False

    value = float(current[field])
    return value > baseline["ucl"] or value < baseline["lcl"]
