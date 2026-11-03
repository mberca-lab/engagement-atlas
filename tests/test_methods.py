import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from atlas.methods import (
    benjamini_hochberg,
    interval_radius,
    make_forecast_panel,
    paired_error_comparison,
    temporal_partitions,
)
from atlas.modeling import segmentation
from atlas.statistics import balanced_longitudinal, intention_analysis


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


def test_paired_comparison_keeps_agency_errors_together_and_sign_consistent():
    actual, candidate, baseline = [0, 10, 20], [0, 8, 19], [2, 10, 20]
    result = paired_error_comparison(actual, candidate, baseline)
    reversed_result = paired_error_comparison(actual, baseline, candidate)
    assert result["difference"] == pytest.approx(-1 / 3)
    assert result["fractionBetter"] == pytest.approx(1 / 3)
    assert result["low"] == -2
    assert result["high"] == 2
    assert reversed_result["difference"] == -result["difference"]
    assert reversed_result["low"] == -result["high"]
    assert reversed_result["high"] == -result["low"]
    identical = paired_error_comparison(actual, baseline, baseline)
    assert identical["difference"] == identical["low"] == identical["high"] == 0


@pytest.mark.parametrize(
    "actual,candidate,baseline,draws",
    [
        ([], [], [], 10),
        ([1], [1, 2], [1], 10),
        ([1], [np.inf], [1], 10),
        ([[1]], [[1]], [[1]], 10),
        (1, 1, 1, 10),
        ([1], [1], [1], 0),
    ],
)
def test_paired_comparison_rejects_unpaired_or_invalid_inputs(actual, candidate, baseline, draws):
    with pytest.raises(ValueError):
        paired_error_comparison(actual, candidate, baseline, n_boot=draws)


def test_balanced_change_requires_observed_engagement_in_every_year():
    frame = pd.DataFrame(
        [
            {"organization": name, "year": 2020 + i, "engagement": value}
            for name, values in {
                "A": [10, 15, 20],
                "B": [40, 50, 60],
                "C": [90, None, 100],
                "D": [20, None, 100],
            }.items()
            for i, value in enumerate(values)
        ]
    )
    frame = frame.drop(index=7)  # C has no middle-year record; D has an explicit missing score.
    result = balanced_longitudinal(frame)
    assert result["n"] == 2
    assert result["meanChange"] == 15
    assert (result["low"], result["high"]) == (10, 20)
    assert [r["engagement"] for r in result["trend"]] == [25, 32.5, 40]
    assert (result["gained"], result["declined"], result["unchanged"]) == (2, 0, 0)
    mixed = frame[frame.organization.isin(["A", "B"])].copy()
    mixed.loc[mixed.organization == "A", "engagement"] = [20, 15, 10]
    mixed.loc[mixed.organization == "B", "engagement"] = [40, 40, 40]
    directions = balanced_longitudinal(mixed)
    assert (directions["gained"], directions["declined"], directions["unchanged"]) == (0, 1, 1)
    with pytest.raises(ValueError, match="unique"):
        balanced_longitudinal(pd.concat([frame, frame.iloc[:1]]))
    with pytest.raises(ValueError, match="At least two"):
        balanced_longitudinal(frame[frame.organization == "A"])


def intention_fixture():
    frame = pd.DataFrame(
        {
            "organization": [f"Agency {i}" for i in range(14)],
            "engagement": np.arange(14, dtype=float) + 40,
            "intent_leave": list(np.arange(12, 0, -1)) + [np.nan, np.nan],
            "response_rate": np.arange(14) + 50,
            "agency_size": ["Large"] * 12 + ["Very Small"] * 2,
        }
    )
    frame.loc[11, "engagement"] = np.nan
    return frame


def test_intention_sensitivity_uses_complete_pairs_and_discloses_missing_sizes():
    result = intention_analysis(intention_fixture())
    assert result["n"] == 11
    assert result["rho"] == pytest.approx(-1)
    assert result["low"] == pytest.approx(-1)
    assert result["high"] == pytest.approx(-1)
    assert result["leaveOneOutValid"] == 11
    assert result["leaveOneOutHigh"] == pytest.approx(-1)
    assert result["unrepresentedSizes"] == ["Very Small"]
    assert {r["linked"]: r["n"] for r in result["selection"]} == {True: 11, False: 3}


def test_intention_diagnostics_disclose_undefined_resamples_and_deletions():
    frame = intention_fixture()
    frame["engagement"] = [0] * 13 + [1]
    frame["intent_leave"] = -frame.engagement
    result = intention_analysis(frame)
    assert result["leaveOneOutValid"] == 13
    assert result["leaveOneOut"][-1]["rho"] is None
    assert 0 < result["bootstrapValid"] < result["bootstrapDraws"]
    np.testing.assert_allclose([result["low"], result["high"]], [-1, -1])
    with pytest.raises(ValueError, match="one observation"):
        intention_analysis(pd.concat([frame, frame.iloc[:1]]))
    frame["engagement"] = 0
    with pytest.raises(ValueError, match="varying"):
        intention_analysis(frame)


def test_one_score_diagnostic_recognizes_a_level_only_partition():
    scores = np.repeat([30, 80], 15)
    rng = np.random.default_rng(42)
    frame = pd.DataFrame(
        {
            "organization": [f"Agency {i}" for i in range(30)],
            "engagement": scores,
            "leaders": scores + rng.normal(0, 0.1, 30),
            "satisfaction": scores + rng.normal(0, 0.1, 30),
        }
    )
    result = segmentation(frame, {"leaders": "Leaders", "satisfaction": "Satisfaction"})
    assert result["levelCheck"]["adjustedRand"] == 1
    assert result["levelCheck"]["n"] == len(result["points"]) == 30


def test_published_diagnostics_match_their_underlying_held_out_agencies():
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / "outputs" / "atlas.json").read_text(encoding="utf-8"))
    models = data["models"]
    predictions = pd.read_csv(root / "outputs" / "model_predictions.csv")
    assert not predictions.duplicated(["model", "organization"]).any()
    assert len(predictions.model.unique()) == len(models["metrics"])
    for row in models["pairedComparisons"]:
        candidate = predictions[predictions.model == row["name"]]
        assert len(candidate) == row["n"] == models["nTest"]
        check = paired_error_comparison(candidate.actual, candidate.predicted, candidate.baseline)
        np.testing.assert_allclose(
            [row[k] for k in ["difference", "low", "high"]],
            [check[k] for k in ["difference", "low", "high"]],
            atol=1e-10,
        )
    assert models["selected"] == min(models["selection"], key=lambda r: r["mae"])["name"]
    cohort = data["cohortSensitivity"]
    assert cohort["meanChange"] == pytest.approx(cohort["lastMean"] - cohort["firstMean"])
    assert cohort["n"] == models["balancedOrgCount"]
    intervals = pd.DataFrame(models["predictions"])
    covered = int(intervals.actual.between(intervals.lower, intervals.upper).sum())
    assert covered == models["interval"]["covered"]
    assert models["interval"]["coverage"] == covered / len(intervals)
