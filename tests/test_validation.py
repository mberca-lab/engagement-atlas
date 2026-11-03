import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from atlas import validation
from atlas.methods import make_forecast_panel

FEATURES = {"signal": "Additional index", "clock": "Survey year marker"}


def test_release_import_uses_committed_methods_without_user_only_helper():
    root = Path(__file__).resolve().parents[1]
    source = subprocess.check_output(
        ["git", "show", "HEAD:atlas/methods.py"], cwd=root, text=True, encoding="utf-8"
    )
    script = """
import sys
import types

methods = types.ModuleType("atlas.methods")
exec(compile(sys.stdin.read(), "atlas/methods.py", "exec"), methods.__dict__)
methods.__dict__.pop("rolling_partitions", None)
sys.modules["atlas.methods"] = methods
from atlas.validation import rolling_origin_audit
assert callable(rolling_origin_audit)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        input=source,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.fixture
def frame():
    return pd.DataFrame(
        [
            {
                "organization": f"Agency {i}",
                "year": year,
                "engagement": 35 + 2 * i + 1.5 * (year - 2017) + np.sin(i + year),
                "signal": 40 + i + np.cos(i + year),
                "clock": float(year),
            }
            for year in range(2017, 2025)
            for i in range(12)
        ]
    )


@pytest.fixture(autouse=True)
def fast_candidates(monkeypatch):
    monkeypatch.setattr(
        validation,
        "candidates",
        lambda: {
            "Ridge": make_pipeline(SimpleImputer(), StandardScaler(), Ridge(alpha=10)),
            "Constant": make_pipeline(SimpleImputer(), DummyRegressor(strategy="mean")),
        },
    )


def test_origins_use_nested_earlier_only_folds_and_valid_metrics(frame):
    result = validation.rolling_origin_audit(frame, FEATURES)
    json.dumps(result, allow_nan=False)
    assert [row["year"] for row in result["origins"]] == [2022, 2023, 2024]
    predictions = pd.DataFrame(result["predictions"])
    assert not predictions.duplicated(["year", "organization"]).any()
    for row in result["origins"]:
        year = row["year"]
        assert row["testYear"] == year
        assert row["calibrationYear"] == year - 1
        assert row["trainingYears"] == list(range(2018, year - 1))
        assert row["selectionYears"] == list(range(2020, year - 1))
        assert max(row["selectionYears"]) < row["calibrationYear"] < year
        assert row["nTraining"] == 12 * len(row["trainingYears"])
        assert row["nCalibration"] == 12
        group = predictions[predictions.year == year]
        assert row["n"] == len(group) == 12
        mae = np.abs(group.actual - group.predicted).mean()
        baseline_mae = np.abs(group.actual - group.baseline).mean()
        assert row["mae"] == pytest.approx(mae)
        assert row["baselineMae"] == pytest.approx(baseline_mae)
        assert row["improvement"] == pytest.approx(baseline_mae - mae)
        covered = int(group.actual.between(group.lower, group.upper).sum())
        assert row["covered"] == covered
        assert row["coverage"] == covered / len(group)
        assert row["nominal"] == 0.9
        assert row["width"] == pytest.approx((group.upper - group.lower).mean())
        assert group.lower.between(0, 100).all()
        assert group.upper.between(0, 100).all()
        ablation = row["ablation"]
        assert ablation["priorOnlyRidgeMae"] == pytest.approx(
            np.abs(group.actual - group.priorOnlyRidge).mean()
        )
        assert ablation["fullRidgeMae"] == pytest.approx(
            np.abs(group.actual - group.fullRidge).mean()
        )
        assert ablation["incrementalFeatureImprovement"] == pytest.approx(
            ablation["priorOnlyRidgeMae"] - ablation["fullRidgeMae"]
        )
        assert row["selected"] == row["selection"][0]["name"]
        selected = next(r for r in row["candidates"] if r["name"] == row["selected"])
        assert selected["mae"] == row["mae"]
    for key in ["mae", "baselineMae", "improvement", "coverage", "width"]:
        assert result["summary"][key] == pytest.approx(
            np.mean([row[key] for row in result["origins"]])
        )
    assert result["summary"]["covered"] == sum(row["covered"] for row in result["origins"])
    assert result["summary"]["n"] == len(predictions)
    assert any("vintages" in note for note in result["notes"])
    assert any("not fresh independent holdouts" in note for note in result["notes"])


def test_target_labels_cannot_change_selection_or_predictions(frame):
    original = validation.rolling_origin_audit(frame, FEATURES)
    changed_frame = frame.copy()
    changed_frame.loc[changed_frame.year == 2024, "engagement"] = 99
    changed = validation.rolling_origin_audit(changed_frame, FEATURES)
    before, after = original["origins"][-1], changed["origins"][-1]
    assert before["selection"] == after["selection"]
    assert before["selected"] == after["selected"]
    assert before["ablation"] != after["ablation"]
    p = pd.DataFrame(original["predictions"]).query("year == 2024")
    q = pd.DataFrame(changed["predictions"]).query("year == 2024")
    np.testing.assert_array_equal(
        p[["predicted", "lower", "upper"]], q[["predicted", "lower", "upper"]]
    )
    assert not np.array_equal(p.actual, q.actual)
    changed_frame.loc[changed_frame.year == 2023, "engagement"] = 1
    changed_calibration = validation.rolling_origin_audit(changed_frame, FEATURES)
    assert before["selection"] == changed_calibration["origins"][-1]["selection"]
    assert before["selected"] == changed_calibration["origins"][-1]["selected"]


def test_every_pipeline_fit_and_imputation_is_local_and_fresh(frame, monkeypatch):
    records = []

    class RecordingImputer(SimpleImputer):
        def fit(self, x, y=None):
            assert not any(record[0] is self for record in records)
            super().fit(x, y)
            records.append((self, x.copy(), y.copy()))
            return self

    template = make_pipeline(RecordingImputer(), StandardScaler(), Ridge(alpha=10))
    monkeypatch.setattr(validation, "candidates", lambda: {"Ridge": template})
    frame.loc[(frame.year == 2017) & (frame.organization == "Agency 0"), "signal"] = np.nan
    validation.rolling_origin_audit(frame, FEATURES)
    # 1+2+3 inner folds, three final full fits, and three prior-only ablation fits.
    assert len(records) == 12
    assert not hasattr(template[0], "statistics_")
    panel = make_forecast_panel(frame, list(FEATURES))
    expected_years = [
        [2018, 2019],
        [2018, 2019, 2020],
        [2018, 2019, 2020],
        [2018, 2019],
        [2018, 2019, 2020],
        [2018, 2019, 2020, 2021],
        [2018, 2019, 2020, 2021],
        [2018, 2019],
        [2018, 2019, 2020],
        [2018, 2019, 2020, 2021],
        [2018, 2019, 2020, 2021, 2022],
        [2018, 2019, 2020, 2021, 2022],
    ]
    for (fitted, x, y), years in zip(records, expected_years, strict=True):
        expected = panel[panel.target_year.isin(years)]
        pd.testing.assert_frame_equal(x, expected[list(x.columns)])
        pd.testing.assert_series_equal(y, expected.target)
        np.testing.assert_allclose(fitted.statistics_, np.nanmean(x, axis=0))
        if "clock" in x:
            assert sorted((x.clock + 1).unique()) == years
    # Independently reproduce a fold with missing feature values.
    training = panel[panel.target_year < 2020]
    heldout = panel[panel.target_year == 2020]
    fitted = clone(template).fit(training[["engagement", *FEATURES]], training.target)
    expected_mae = np.abs(
        heldout.target - np.clip(fitted.predict(heldout[["engagement", *FEATURES]]), 0, 100)
    ).mean()
    result = validation.rolling_origin_audit(frame, FEATURES)
    ridge = next(r for r in result["origins"][0]["selection"] if r["name"] == "Ridge")
    assert ridge["mae"] == pytest.approx(expected_mae)


def test_equal_year_summary_is_not_pooled_by_unequal_cohort_sizes(frame):
    frame = frame[
        ~((frame.year == 2024) & frame.organization.isin(["Agency 0", "Agency 1"]))
    ].copy()
    frame.loc[frame.year == 2024, "engagement"] = 99
    result = validation.rolling_origin_audit(frame, FEATURES)
    rows = result["origins"]
    assert [row["n"] for row in rows] == [12, 12, 10]
    assert result["summary"]["mae"] == pytest.approx(np.mean([r["mae"] for r in rows]))
    pooled = np.average([r["mae"] for r in rows], weights=[r["n"] for r in rows])
    assert result["summary"]["mae"] != pytest.approx(pooled)


def test_ties_prefer_persistence_and_ablation_does_not_enter_selection(frame):
    frame["engagement"] = 50.0
    result = validation.rolling_origin_audit(frame, FEATURES)
    for row in result["origins"]:
        assert row["selected"] == "Persistence"
        assert row["mae"] == row["improvement"] == row["width"] == 0
        assert row["coverage"] == 1
        assert {candidate["name"] for candidate in row["selection"]} == {
            "Persistence",
            "Ridge",
            "Constant",
        }


@pytest.mark.parametrize("last_year", [2020, 2021])
def test_insufficient_nested_warmup_is_rejected(frame, last_year):
    with pytest.raises(ValueError, match="No eligible audit origins"):
        validation.rolling_origin_audit(frame[frame.year <= last_year], FEATURES)


def test_missing_calibration_year_does_not_bridge_gap(frame):
    result = validation.rolling_origin_audit(frame[frame.year != 2023], FEATURES)
    assert [row["year"] for row in result["origins"]] == [2022]


def test_too_small_calibration_partition_is_skipped(frame):
    frame = frame[
        ~((frame.year == 2021) & frame.organization.isin(["Agency 0", "Agency 1", "Agency 2"]))
    ]
    result = validation.rolling_origin_audit(frame, FEATURES)
    assert [row["year"] for row in result["origins"]] == [2024]


def test_duplicate_organization_year_is_rejected(frame):
    with pytest.raises(ValueError, match="Duplicate"):
        validation.rolling_origin_audit(pd.concat([frame, frame.iloc[:1]]), FEATURES)


@pytest.mark.parametrize("bad", [np.inf, -np.inf])
def test_infinite_predictors_are_rejected(frame, bad):
    frame.loc[0, "signal"] = bad
    with pytest.raises(ValueError, match="infinite"):
        validation.rolling_origin_audit(frame, FEATURES)


def test_engagement_outside_index_bounds_is_rejected(frame):
    frame.loc[0, "engagement"] = 101
    with pytest.raises(ValueError, match="0–100"):
        validation.rolling_origin_audit(frame, FEATURES)
