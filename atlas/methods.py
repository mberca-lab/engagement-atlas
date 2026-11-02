from __future__ import annotations

import numpy as np
from scipy import stats
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

SEED = 42


def benjamini_hochberg(p_values):
    values = np.asarray(p_values, dtype=float)
    result = np.full(values.shape, np.nan)
    valid = np.flatnonzero(np.isfinite(values))
    if not len(valid):
        return result
    order = valid[np.argsort(values[valid])]
    adjusted = values[order] * len(order) / np.arange(1, len(order) + 1)
    result[order] = np.clip(np.minimum.accumulate(adjusted[::-1])[::-1], 0, 1)
    return result


def make_forecast_panel(frame, features):
    """Join only exact organization names and consecutive survey years."""
    if frame.duplicated(["organization", "year"]).any():
        raise ValueError("Duplicate organization-year keys must be resolved before forecasting.")
    future = frame[["organization", "year", "engagement"]].copy()
    future["year"] = future["year"] - 1
    future = future.rename(columns={"engagement": "target"})
    panel = frame.merge(future, on=["organization", "year"], how="inner", validate="one_to_one")
    panel["target_year"] = panel["year"] + 1
    return panel.dropna(subset=["engagement", "target"])[
        ["organization", "year", "target_year", "engagement", "target", *features]
    ].sort_values(["target_year", "organization"])


def temporal_partitions(panel):
    years = sorted(panel["target_year"].unique())
    if len(years) < 5:
        raise ValueError(
            "At least five forecast target years are required for temporal validation."
        )
    calibration_year, test_year = years[-2:]
    development = panel[panel.target_year < calibration_year].copy()
    calibration = panel[panel.target_year == calibration_year].copy()
    test = panel[panel.target_year == test_year].copy()
    if min(len(development), len(calibration), len(test)) < 10:
        raise ValueError("Each temporal partition needs at least ten organization observations.")
    return development, calibration, test


def interval_radius(residuals, coverage=0.90):
    residuals = np.abs(np.asarray(residuals, dtype=float))
    residuals = residuals[np.isfinite(residuals)]
    if not len(residuals) or not 0 < coverage < 1:
        raise ValueError("Finite calibration residuals and coverage in (0, 1) are required.")
    rank = int(np.ceil((len(residuals) + 1) * coverage))
    if rank > len(residuals):
        return float("inf")
    return float(np.sort(residuals)[rank - 1])


def bootstrap_mae(actual, predicted, n_boot=2000):
    actual, predicted = np.asarray(actual), np.asarray(predicted)
    rng = np.random.default_rng(SEED)
    indices = rng.integers(0, len(actual), size=(n_boot, len(actual)))
    estimates = np.abs(actual[indices] - predicted[indices]).mean(axis=1)
    return [float(v) for v in np.quantile(estimates, [0.025, 0.975])]


def model_metrics(name, actual, predicted):
    low, high = bootstrap_mae(actual, predicted)
    return {
        "name": name,
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "r2": float(r2_score(actual, predicted)),
        "low": low,
        "high": high,
    }


def paired_error_comparison(actual, predicted, reference, n_boot=5000):
    """Resample matched agency error differences; positive means lower model MAE."""
    actual, predicted, reference = [
        np.asarray(values, dtype=float) for values in [actual, predicted, reference]
    ]
    if (
        actual.ndim != 1
        or not actual.size
        or actual.shape != predicted.shape
        or actual.shape != reference.shape
        or not all(np.isfinite(values).all() for values in [actual, predicted, reference])
        or not isinstance(n_boot, int)
        or n_boot < 1
    ):
        raise ValueError("Paired error comparisons need matching finite nonempty vectors.")
    differences = np.abs(actual - reference) - np.abs(actual - predicted)
    rng = np.random.default_rng(SEED)
    sample = differences[rng.integers(0, len(actual), (n_boot, len(actual)))].mean(axis=1)
    low, high = np.quantile(sample, [0.025, 0.975])
    return {
        "n": len(actual),
        "difference": float(differences.mean()),
        "low": float(low),
        "high": float(high),
        "fractionBetter": float(np.mean(differences > 0)),
        "medianAbsoluteError": float(np.median(np.abs(actual - predicted))),
    }


def feature_correlations(frame, features):
    results = []
    for key, label in features.items():
        pair = frame[[key, "engagement"]].dropna()
        if len(pair) < 5 or pair[key].nunique() < 2 or pair.engagement.nunique() < 2:
            continue
        rho, p_value = stats.spearmanr(pair[key], pair.engagement)
        results.append(
            {"feature": key, "label": label, "rho": float(rho), "p": float(p_value), "n": len(pair)}
        )
    adjusted = benjamini_hochberg([r["p"] for r in results])
    for row, q_value in zip(results, adjusted, strict=True):
        row["q"] = float(q_value)
    return sorted(results, key=lambda r: abs(r["rho"]), reverse=True)
