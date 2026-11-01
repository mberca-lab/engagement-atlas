from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from atlas.methods import SEED, benjamini_hochberg


def annual_summary(frame):
    rng = np.random.default_rng(SEED)
    results = []
    for year, group in frame.groupby("year"):
        values = group.engagement.dropna().to_numpy()
        boot = np.median(values[rng.integers(0, len(values), size=(2000, len(values)))], axis=1)
        low, high = np.quantile(boot, [0.025, 0.975])
        results.append(
            {
                "year": int(year),
                "n": len(values),
                "engagement": float(values.mean()),
                "median": float(np.median(values)),
                "min": float(values.min()),
                "max": float(values.max()),
                "low": float(low),
                "high": float(high),
            }
        )
    return results


def change_analysis(frame, features):
    ordered = frame.sort_values(["organization", "year"]).copy()
    grouped = ordered.groupby("organization")
    columns = ["engagement", *features]
    differences = grouped[columns].diff()
    consecutive = ordered.year - grouped.year.shift() == 1
    deltas = ordered[["organization", "year"]].join(differences)
    deltas = deltas[consecutive].dropna(subset=columns).copy()
    correlations = []
    rng = np.random.default_rng(SEED)
    groups = list(deltas.groupby("organization"))
    for key, label in features.items():
        rho, p = stats.spearmanr(deltas[key], deltas.engagement)
        bootstrap = []
        for _ in range(500):
            sample = pd.concat(
                [groups[i][1] for i in rng.integers(0, len(groups), len(groups))], ignore_index=True
            )
            value = stats.spearmanr(sample[key], sample.engagement).statistic
            if np.isfinite(value):
                bootstrap.append(value)
        low, high = np.quantile(bootstrap, [0.025, 0.975])
        correlations.append(
            {
                "feature": key,
                "label": label,
                "rho": float(rho),
                "pNaive": float(p),
                "low": float(low),
                "high": float(high),
                "n": len(deltas),
            }
        )
    varying = [key for key in features if deltas[key].std() > 0]
    standard = deltas[varying].std()
    design = (deltas[varying] - deltas[varying].mean()) / standard
    year_dummies = pd.get_dummies(
        deltas.year.astype(str), prefix="year", drop_first=True, dtype=float
    )
    design = sm.add_constant(pd.concat([design, year_dummies], axis=1))
    fitted = sm.OLS(deltas.engagement, design).fit(
        cov_type="cluster", cov_kwds={"groups": deltas.organization}, use_t=True
    )
    intervals = fitted.conf_int()
    coefficients = [
        {
            "feature": key,
            "label": features[key],
            "estimate": float(fitted.params[key]),
            "low": float(intervals.loc[key, 0]),
            "high": float(intervals.loc[key, 1]),
            "p": float(fitted.pvalues[key]),
        }
        for key in varying
    ]
    q_values = benjamini_hochberg([r["p"] for r in coefficients])
    for row, q in zip(coefficients, q_values, strict=True):
        row["q"] = float(q)
    return {
        "correlations": sorted(correlations, key=lambda r: abs(r["rho"]), reverse=True),
        "coefficients": coefficients,
        "n": len(deltas),
        "organizations": int(deltas.organization.nunique()),
        "r2": float(fitted.rsquared),
        "conditionNumber": float(fitted.condition_number),
        "notes": [
            "Only consecutive-year observations are differenced; organization names match exactly.",
            "Regression includes year fixed effects and organization-clustered standard errors.",
            "Coefficients are engagement-index points per one SD of annual change in the feature.",
            "Bootstrap correlations resample whole organization trajectories, not individual years.",
            "Naive correlation p-values do not account for repeated organizations; use the cluster-bootstrap intervals.",
            "Neither first differencing nor statistical adjustment establishes a causal intervention effect.",
        ],
    }, deltas
