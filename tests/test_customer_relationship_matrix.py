"""
Tests for customer relationship matrix scoring and period filtering.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))


def _build_rows(maintainer: str, month: str, volume: int, aging_days: int):
    rows = []
    for idx in range(volume):
        rows.append(
            {
                "MANTENEDOR": maintainer,
                "INÍCIO": pd.Timestamp(f"{month}-01"),
                "CHAMADO": f"{maintainer}-{month}-{idx}",
                "AGING": aging_days,
            }
        )
    return rows


def test_calculate_relationship_score_quadrants():
    from visualization import calculate_relationship_score

    assert calculate_relationship_score(20, 3, 10, 7) == 1
    assert calculate_relationship_score(5, 3, 10, 7) == 2
    assert calculate_relationship_score(5, 10, 10, 7) == 3
    assert calculate_relationship_score(20, 10, 10, 7) == 4


def test_filter_customer_relationship_period_last_six_months():
    from visualization import filter_customer_relationship_period

    df = pd.DataFrame(
        {
            "MANTENEDOR": ["SAW"] * 8,
            "INÍCIO": pd.date_range("2025-01-01", periods=8, freq="MS"),
            "CHAMADO": [f"C{i}" for i in range(8)],
            "AGING": [3] * 8,
        }
    )

    result = filter_customer_relationship_period(df, "Últimos 6 meses")

    assert not result.empty
    assert result["DATA_BASE"].min() >= pd.Timestamp("2025-02-01")
    assert result["DATA_BASE"].max() == pd.Timestamp("2025-08-01")


def test_get_customer_relationship_matrix_data_scores():
    from visualization import get_customer_relationship_matrix_data

    df = pd.DataFrame(
        _build_rows("SAW_A", "2025-01", 10, 2)
        + _build_rows("SAW_B", "2025-01", 2, 2)
        + _build_rows("SAW_C", "2025-01", 2, 12)
        + _build_rows("SAW_D", "2025-01", 10, 12)
    )

    matrix, volume_corte, aging_corte = get_customer_relationship_matrix_data(df)
    score_map = dict(zip(matrix["MANTENEDOR"], matrix["SCORE"]))

    assert volume_corte == 6.0
    assert aging_corte == 7.0
    assert score_map["SAW_A"] == 1
    assert score_map["SAW_B"] == 2
    assert score_map["SAW_C"] == 3
    assert score_map["SAW_D"] == 4


def test_get_customer_relationship_monthly_scores_changes_by_month():
    from visualization import get_customer_relationship_monthly_scores

    df = pd.DataFrame(
        _build_rows("SAW_A", "2025-01", 10, 2)
        + _build_rows("SAW_B", "2025-01", 2, 12)
        + _build_rows("SAW_A", "2025-02", 2, 2)
        + _build_rows("SAW_B", "2025-02", 10, 12)
    )

    monthly = get_customer_relationship_monthly_scores(df)
    jan = monthly[monthly["ANO_MES"] == pd.Timestamp("2025-01-01")]
    feb = monthly[monthly["ANO_MES"] == pd.Timestamp("2025-02-01")]

    jan_scores = dict(zip(jan["MANTENEDOR"], jan["SCORE"]))
    feb_scores = dict(zip(feb["MANTENEDOR"], feb["SCORE"]))

    assert jan_scores["SAW_A"] == 1
    assert jan_scores["SAW_B"] == 3
    assert feb_scores["SAW_A"] == 2
    assert feb_scores["SAW_B"] == 4
