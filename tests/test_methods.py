import numpy as np
import pandas as pd
import pytest

from atlas.methods import (
    benjamini_hochberg,
    interval_radius,
    make_forecast_panel,
    temporal_partitions,
)


def test_forecast_join_does_not_bridge_gaps_or_organizations():
    frame = pd.DataFrame(
        {
            "organization": ["A", "A", "A", "B", "B"],
            "year": [2020, 2021, 2023, 2020, 2021],
            "engagement": [50, 51, 90, 70, 69],
            "leadership": [40, 41, 80, 60, 59],
        }
    )
    panel = make_forecast_panel(frame, ["leadership"])
    assert panel.organization.tolist() == ["A", "B"]
    assert panel.target.tolist() == [51, 69]
    assert (panel.target_year == panel.year + 1).all()
    assert panel.leadership.tolist() == [40, 60]


def test_duplicate_keys_rejected_before_join():
    frame = pd.DataFrame({"organization": ["A", "A"], "year": [2020, 2020], "engagement": [50, 60]})
    with pytest.raises(ValueError, match="Duplicate"):
        make_forecast_panel(frame, [])


def test_temporal_holdout_is_separate_from_model_selection():
    panel = pd.DataFrame(
        [
            {"target_year": year, "organization": f"Org {i}"}
            for year in range(2015, 2024)
            for i in range(12)
        ]
    )
    train, calibration, test = temporal_partitions(panel)
    assert train.target_year.max() < calibration.target_year.min()
    assert calibration.target_year.max() < test.target_year.min()
    assert test.target_year.unique().tolist() == [2023]


def test_bh_multiple_testing_and_missing_values():
    adjusted = benjamini_hochberg([0.01, 0.04, np.nan, 0.03])
    np.testing.assert_allclose(adjusted[[0, 1, 3]], [0.03, 0.04, 0.04])
    assert np.isnan(adjusted[2])


def test_conformal_finite_sample_rank_not_interpolated():
    assert interval_radius(np.arange(1, 20), 0.9) == 18
    assert np.isinf(interval_radius([1, 2], 0.9))
    with pytest.raises(ValueError):
        interval_radius([], 0.9)
