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


def balanced_longitudinal(frame):
    if frame.duplicated(["organization", "year"]).any():
        raise ValueError("Balanced comparisons require unique organization-year keys.")
    observed = frame.dropna(subset=["engagement"])
    if not np.isfinite(observed.engagement).all():
        raise ValueError("Balanced comparisons require finite engagement values.")
    years = sorted(frame.year.unique())
    counts = observed.groupby("organization").year.nunique()
    names = counts[counts == len(years)].index
    if len(names) < 2 or len(years) < 2:
        raise ValueError("At least two continuously observed agencies and years are required.")
    panel = observed[observed.organization.isin(names)].pivot(
        index="organization", columns="year", values="engagement"
    )
    changes = panel[years[-1]] - panel[years[0]]
    rng = np.random.default_rng(SEED)
    sample = changes.to_numpy()[rng.integers(0, len(changes), (5000, len(changes)))].mean(axis=1)
    low, high = np.quantile(sample, [0.025, 0.975])
    return {
        "n": len(panel),
        "firstYear": int(years[0]),
        "lastYear": int(years[-1]),
        "firstMean": float(panel[years[0]].mean()),
        "lastMean": float(panel[years[-1]].mean()),
        "meanChange": float(changes.mean()),
        "low": float(low),
        "high": float(high),
        "trend": [
            {"year": int(year), "n": len(panel), "engagement": float(panel[year].mean())}
            for year in years
        ],
        "agencyChanges": [
            {"organization": name, "change": float(value)} for name, value in changes.items()
        ],
        "interpretation": (
            "Sensitivity comparison: the same reporting names in every observed year. "
            "Paired agency-bootstrap intervals describe this observed cohort, not national "
            "employee sampling uncertainty. Related agencies weaken the resampling assumption. "
            "Names do not guarantee unchanged agency boundaries or workforces."
        ),
    }


def intention_analysis(latest):
    if latest.organization.duplicated().any():
        raise ValueError("Intention diagnostics require one observation per agency.")
    paired = latest[["organization", "engagement", "intent_leave"]].dropna()
    if len(paired) < 10:
        raise ValueError("At least ten linked agencies are required for intention diagnostics.")
    x, y = paired.engagement.to_numpy(), paired.intent_leave.to_numpy()
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Intention diagnostics require finite survey values.")
    if min(len(np.unique(x)), len(np.unique(y))) < 2:
        raise ValueError("Intention diagnostics require varying engagement and intention scores.")
    rho, p = stats.spearmanr(x, y)
    rng = np.random.default_rng(SEED)
    bootstrap = []
    for index in rng.integers(0, len(paired), (3000, len(paired))):
        if min(len(np.unique(x[index])), len(np.unique(y[index]))) > 1:
            bootstrap.append(float(stats.spearmanr(x[index], y[index]).statistic))
    if not bootstrap:
        raise ValueError("No varying bootstrap samples remain for intention diagnostics.")
    low, high = np.quantile(bootstrap, [0.025, 0.975])
    leave_one_out = []
    for i, name in enumerate(paired.organization):
        a, b = np.delete(x, i), np.delete(y, i)
        value = (
            float(stats.spearmanr(a, b).statistic)
            if min(len(np.unique(a)), len(np.unique(b))) > 1
            else None
        )
        leave_one_out.append({"organization": name, "rho": value})
    valid_loo = [row["rho"] for row in leave_one_out if row["rho"] is not None]
    roster = latest.copy()
    roster["linked"] = roster[["engagement", "intent_leave"]].notna().all(axis=1)
    groups = []
    for linked, group in roster.groupby("linked"):
        groups.append(
            {
                "linked": bool(linked),
                "label": "Linked" if linked else "Not linked",
                "n": len(group),
                "medianEngagement": float(group.engagement.median()),
                "medianResponseRate": float(group.response_rate.median()),
            }
        )
    composition = [
        {
            "size": str(size),
            "linked": int(group.linked.sum()),
            "unlinked": int((~group.linked).sum()),
        }
        for size, group in roster.groupby("agency_size")
    ]
    return {
        "n": len(paired),
        "rho": float(rho),
        "p": float(p),
        "low": float(low),
        "high": float(high),
        "leaveOneOut": leave_one_out,
        "bootstrapValid": len(bootstrap),
        "bootstrapDraws": 3000,
        "leaveOneOutValid": len(valid_loo),
        "leaveOneOutLow": min(valid_loo) if valid_loo else None,
        "leaveOneOutHigh": max(valid_loo) if valid_loo else None,
        "selection": groups,
        "sizeComposition": composition,
        "unrepresentedSizes": [row["size"] for row in composition if row["linked"] == 0],
        "interpretation": (
            "A distinct same-survey question, not an external or causal validation. "
            "Agency-bootstrap and leave-one-out checks are conditional on the selected linked "
            "agencies; they do not correct nonresponse, selection, or common-method bias."
        ),
    }


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
