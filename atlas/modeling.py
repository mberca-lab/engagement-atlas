from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.base import clone
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import (
    ExtraTreesRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.metrics import adjusted_rand_score, mean_absolute_error, silhouette_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from atlas.methods import (
    SEED,
    interval_radius,
    make_forecast_panel,
    model_metrics,
    paired_error_comparison,
    temporal_partitions,
)


def candidates():
    return {
        "Ridge": make_pipeline(SimpleImputer(), StandardScaler(), Ridge(alpha=10)),
        "Elastic net": make_pipeline(
            SimpleImputer(), StandardScaler(), ElasticNet(alpha=0.1, l1_ratio=0.3, max_iter=10000)
        ),
        "Random forest": make_pipeline(
            SimpleImputer(),
            RandomForestRegressor(
                n_estimators=250, min_samples_leaf=5, max_features=0.8, random_state=SEED, n_jobs=2
            ),
        ),
        "Extra trees": make_pipeline(
            SimpleImputer(),
            ExtraTreesRegressor(n_estimators=250, min_samples_leaf=5, random_state=SEED, n_jobs=2),
        ),
        "Gradient boosting": make_pipeline(
            SimpleImputer(),
            HistGradientBoostingRegressor(
                max_iter=150,
                max_leaf_nodes=7,
                learning_rate=0.05,
                l2_regularization=10,
                min_samples_leaf=15,
                random_state=SEED,
            ),
        ),
    }


def forecast(frame, features):
    panel = make_forecast_panel(frame, list(features))
    development, calibration, test = temporal_partitions(panel)
    keys = ["engagement", *features]
    specs = candidates()
    cv_rows = []
    years = sorted(development.target_year.unique())
    for year in years[2:]:
        train = development[development.target_year < year]
        validation = development[development.target_year == year]
        cv_rows.append(
            {
                "name": "Persistence",
                "year": int(year),
                "mae": float(mean_absolute_error(validation.target, validation.engagement)),
                "n": len(validation),
            }
        )
        for name, specification in specs.items():
            with threadpool_limits(limits=2):
                fitted = clone(specification).fit(train[keys], train.target)
                predicted = np.clip(fitted.predict(validation[keys]), 0, 100)
            cv_rows.append(
                {
                    "name": name,
                    "year": int(year),
                    "mae": float(mean_absolute_error(validation.target, predicted)),
                    "n": len(validation),
                }
            )
    cv = pd.DataFrame(cv_rows)
    if cv.empty:
        raise ValueError("No expanding-window folds could be formed.")
    selection = cv.groupby("name").mae.mean().sort_values()
    selected = str(selection.index[0])
    fitted_models, metrics = {}, [model_metrics("Persistence", test.target, test.engagement)]
    all_predictions = {"Persistence": test.engagement.to_numpy()}
    comparisons = []
    for name, specification in specs.items():
        with threadpool_limits(limits=2):
            fitted = clone(specification).fit(development[keys], development.target)
            predicted = np.clip(fitted.predict(test[keys]), 0, 100)
        fitted_models[name] = fitted
        all_predictions[name] = predicted
        metrics.append(model_metrics(name, test.target, predicted))
        comparisons.append(
            {"name": name, **paired_error_comparison(test.target, predicted, test.engagement)}
        )
    best_ml_name = str(selection.drop("Persistence").index[0])
    explanation_model = fitted_models[best_ml_name]
    with threadpool_limits(limits=2):
        importance = permutation_importance(
            explanation_model,
            test[keys],
            test.target,
            scoring="neg_mean_absolute_error",
            n_repeats=30,
            random_state=SEED,
            n_jobs=1,
        )
    labels = {"engagement": "Prior-year engagement", **features}
    importances = [
        {
            "feature": key,
            "label": labels[key],
            "mean": float(importance.importances_mean[i]),
            "std": float(importance.importances_std[i]),
        }
        for i, key in enumerate(keys)
    ]
    if selected == "Persistence":
        predicted = test.engagement.to_numpy()
        calibration_prediction = calibration.engagement.to_numpy()
    else:
        with threadpool_limits(limits=2):
            predicted = np.clip(fitted_models[selected].predict(test[keys]), 0, 100)
            calibration_prediction = np.clip(
                fitted_models[selected].predict(calibration[keys]), 0, 100
            )
    radius = interval_radius(calibration.target - calibration_prediction)
    lower, upper = np.maximum(0, predicted - radius), np.minimum(100, predicted + radius)
    covered = int(np.sum((test.target >= lower) & (test.target <= upper)))
    coverage_interval = binomtest(covered, len(test)).proportion_ci(method="wilson")
    transport = []
    for train_idx, validation_idx in GroupKFold(n_splits=5).split(
        development, groups=development.organization
    ):
        with threadpool_limits(limits=2):
            fitted = clone(specs[best_ml_name]).fit(
                development.iloc[train_idx][keys], development.iloc[train_idx].target
            )
            values = np.clip(fitted.predict(development.iloc[validation_idx][keys]), 0, 100)
        transport.append(
            float(mean_absolute_error(development.iloc[validation_idx].target, values))
        )
    predictions = [
        {
            "organization": row.organization,
            "actual": float(row.target),
            "predicted": float(predicted[i]),
            "baseline": float(row.engagement),
            "lower": float(lower[i]),
            "upper": float(upper[i]),
        }
        for i, row in enumerate(test.itertuples())
    ]
    observed_years = frame.groupby("organization").year.nunique()
    continuous_names = observed_years[observed_years == frame.year.nunique()].index
    paired = (
        frame[frame.organization.isin(continuous_names)]
        .groupby("year")
        .engagement.agg(["count", "mean"])
    )
    return {
        "target": "Next-year organization-level employee engagement index",
        "trainYears": [int(y) for y in years],
        "validationYear": int(years[-1]),
        "calibrationYear": int(calibration.target_year.min()),
        "testYear": int(test.target_year.min()),
        "selected": selected,
        "explanationModel": best_ml_name,
        "metrics": sorted(metrics, key=lambda r: r["mae"]),
        "pairedComparisons": sorted(comparisons, key=lambda r: r["difference"], reverse=True),
        "comparisonNotes": (
            "Positive differences mean lower MAE than persistence on the same held-out agencies. "
            "Percentile 95% intervals use 5,000 paired agency resamples with seed 42. "
            "These post-hoc diagnostics do not change validation-based model selection, "
            "adjust for five comparisons, or include model-training uncertainty. "
            "Related agencies may weaken the independent-agency resampling assumption."
        ),
        "modelPredictions": [
            {
                "organization": row.organization,
                "model": name,
                "actual": float(row.target),
                "predicted": float(values[i]),
                "baseline": float(row.engagement),
            }
            for name, values in all_predictions.items()
            for i, row in enumerate(test.itertuples())
        ],
        "importance": sorted(importances, key=lambda r: r["mean"], reverse=True),
        "predictions": predictions,
        "nTrain": len(development),
        "nTest": len(test),
        "nCalibration": len(calibration),
        "interval": {
            "nominal": 0.90,
            "coverage": float(np.mean((test.target >= lower) & (test.target <= upper))),
            "covered": covered,
            "n": len(test),
            "coverageLow": float(coverage_interval.low),
            "coverageHigh": float(coverage_interval.high),
            "coverageNote": (
                "The illustrative 95% Wilson interval assumes independent coverage events "
                "and fixed predictions; it does not correct agency dependence or temporal shift."
            ),
            "width": float(np.mean(upper - lower)),
            "radius": float(radius),
        },
        "cv": cv_rows,
        "selection": [{"name": str(n), "mae": float(v)} for n, v in selection.items()],
        "transportability": {"model": best_ml_name, "mae": float(np.mean(transport)), "folds": 5},
        "balancedTrend": [
            {"year": int(y), "n": int(r["count"]), "engagement": float(r["mean"])}
            for y, r in paired.iterrows()
        ],
        "balancedOrgCount": len(continuous_names),
    }, panel


def segmentation(latest, features):
    keys = list(features)
    eligible = latest[latest[keys].notna().all(axis=1)].copy()
    scaled = StandardScaler().fit_transform(eligible[keys])
    scores, models = {}, {}
    with threadpool_limits(limits=2):
        for k in range(2, min(6, len(eligible) // 10 + 1)):
            fitted = KMeans(n_clusters=k, n_init=30, random_state=SEED).fit(scaled)
            scores[k], models[k] = float(silhouette_score(scaled, fitted.labels_)), fitted
        k = max(scores, key=scores.get)
        fitted = models[k]
        level_labels = KMeans(n_clusters=k, n_init=30, random_state=SEED).fit_predict(
            scaled.mean(axis=1).reshape(-1, 1)
        )
        level_agreement = float(adjusted_rand_score(fitted.labels_, level_labels))
        pca = PCA(n_components=2).fit(scaled)
        coordinates = pca.transform(scaled)
        rng = np.random.default_rng(SEED)
        stability = []
        for _ in range(30):
            subset = rng.choice(len(eligible), size=int(len(eligible) * 0.8), replace=False)
            labels = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit_predict(scaled[subset])
            stability.append(float(adjusted_rand_score(fitted.labels_[subset], labels)))
    eligible["cluster"] = fitted.labels_
    profiles = []
    for cluster, group in eligible.groupby("cluster"):
        values = group[keys].mean()
        relative = values - eligible[keys].mean()
        strongest = relative.idxmax()
        weakest = relative.idxmin()
        profiles.append(
            {
                "cluster": int(cluster),
                "name": f"Profile {int(cluster) + 1}",
                "n": len(group),
                "features": {key: float(values[key]) for key in keys},
                "engagement": float(group.engagement.mean()),
                "strongest": features[strongest],
                "weakest": features[weakest],
            }
        )
    return {
        "k": int(k),
        "silhouette": scores[k],
        "stability": float(np.mean(stability)),
        "levelCheck": {
            "n": len(eligible),
            "k": int(k),
            "adjustedRand": level_agreement,
            "interpretation": (
                "Compare the full-feature partition with K-means on just the average "
                "standardized input score, using the same agencies and k. "
                "ARI=1 means identical assignments up to label permutation; "
                "this is a descriptive simplification check, not independent validation."
            ),
        },
        "candidateScores": [{"k": int(k), "score": v} for k, v in scores.items()],
        "variance": [float(v) for v in pca.explained_variance_ratio_],
        "loadings": [
            {
                "feature": key,
                "pc1": float(pca.components_[0, i]),
                "pc2": float(pca.components_[1, i]),
            }
            for i, key in enumerate(keys)
        ],
        "points": [
            {
                "organization": row.organization,
                "x": float(coordinates[i, 0]),
                "y": float(coordinates[i, 1]),
                "cluster": int(row.cluster),
                "engagement": float(row.engagement),
            }
            for i, row in enumerate(eligible.itertuples())
        ],
        "profiles": profiles,
    }
