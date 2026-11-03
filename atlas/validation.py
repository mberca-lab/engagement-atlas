"""Retrospective audits, separate from the published locked forecast."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error
from threadpoolctl import threadpool_limits

from atlas.methods import interval_radius, make_forecast_panel
from atlas.modeling import candidates


def _rolling_partitions(panel):
    """Reserve the preceding target year for calibration at each audit origin."""
    for year in sorted(panel.target_year.unique())[2:]:
        train = panel[panel.target_year < year - 1]
        calibration = panel[panel.target_year == year - 1]
        test = panel[panel.target_year == year]
        if min(len(train), len(calibration), len(test)) >= 10:
            yield int(year), train, calibration, test


def _predict(specification, training, evaluation, keys):
    with threadpool_limits(limits=2):
        fitted = clone(specification).fit(training[keys], training.target)
        values = np.clip(fitted.predict(evaluation[keys]), 0, 100)
    return values


def rolling_origin_audit(frame, features):
    """Audit each eligible origin using only strictly earlier selection folds.

    ``features`` is the same key-to-label mapping accepted by ``forecast``.
    All year fields describe forecast *target* years, not predictor years.
    Candidate configurations and feature definitions are fixed retrospectively;
    this function neither changes nor supplies the original forecast winner.
    """
    keys = ["engagement", *features]
    if len(set(keys)) != len(keys) or set(features) & {
        "organization",
        "year",
        "target",
        "target_year",
    }:
        raise ValueError("Features must be distinct predictor columns excluding reserved fields.")
    panel = make_forecast_panel(frame, list(features))
    values = panel[["engagement", "target", *features]].to_numpy(dtype=float)
    if np.isinf(values).any():
        raise ValueError("Forecast inputs must not contain infinite values.")
    if not panel[["engagement", "target"]].apply(lambda column: column.between(0, 100).all()).all():
        raise ValueError("Engagement and target values must be within 0–100.")
    specs = candidates()
    origins, predictions = [], []
    for year, development, calibration, test in _rolling_partitions(panel):
        training_years = sorted(int(y) for y in development.target_year.unique())
        folds = []
        for validation_year in training_years[2:]:
            training = development[development.target_year < validation_year]
            validation = development[development.target_year == validation_year]
            if min(len(training), len(validation)) >= 10:
                folds.append((validation_year, training, validation))
        if not folds:
            continue
        scores = {"Persistence": []} | {name: [] for name in specs}
        for _, training, validation in folds:
            scores["Persistence"].append(
                float(mean_absolute_error(validation.target, validation.engagement))
            )
            for name, specification in specs.items():
                predicted = _predict(specification, training, validation, keys)
                scores[name].append(float(mean_absolute_error(validation.target, predicted)))
        selection = sorted(
            ({"name": name, "mae": float(np.mean(errors))} for name, errors in scores.items()),
            key=lambda row: (row["mae"], row["name"] != "Persistence", row["name"]),
        )
        selected = selection[0]["name"]
        # A single frozen development fit predicts calibration and test; calibration
        # labels set only the interval radius, never the model or its parameters.
        evaluation = pd.concat([calibration, test])
        all_predictions = {"Persistence": evaluation.engagement.to_numpy()}
        for name, specification in specs.items():
            all_predictions[name] = _predict(specification, development, evaluation, keys)
        selected_predictions = all_predictions[selected]
        calibration_prediction = selected_predictions[: len(calibration)]
        predicted = selected_predictions[len(calibration) :]
        baseline = test.engagement.to_numpy()
        radius = interval_radius(calibration.target.to_numpy() - calibration_prediction)
        lower, upper = np.maximum(0, predicted - radius), np.minimum(100, predicted + radius)
        covered = int(np.sum((test.target.to_numpy() >= lower) & (test.target.to_numpy() <= upper)))
        mae = float(mean_absolute_error(test.target, predicted))
        baseline_mae = float(mean_absolute_error(test.target, baseline))
        prior_ridge = _predict(specs["Ridge"], development, test, ["engagement"])
        prior_mae = float(mean_absolute_error(test.target, prior_ridge))
        full_ridge = all_predictions["Ridge"][len(calibration) :]
        full_mae = float(mean_absolute_error(test.target, full_ridge))
        origins.append(
            {
                "year": year,
                "testYear": year,
                "selected": selected,
                "n": len(test),
                "mae": mae,
                "baselineMae": baseline_mae,
                "improvement": baseline_mae - mae,
                "coverage": covered / len(test),
                "nominal": 0.90,
                "width": float(np.mean(upper - lower)),
                "covered": covered,
                "nCalibration": len(calibration),
                "nTraining": len(development),
                "calibrationYear": int(calibration.target_year.iloc[0]),
                "selectionYears": [fold[0] for fold in folds],
                "trainingYears": training_years,
                "selection": selection,
                "candidates": [
                    {
                        "name": row["name"],
                        "selectionMae": row["mae"],
                        "mae": float(
                            mean_absolute_error(
                                test.target, all_predictions[row["name"]][len(calibration) :]
                            )
                        ),
                        "n": len(test),
                    }
                    for row in selection
                ],
                "ablation": {
                    "priorOnlyRidgeMae": prior_mae,
                    "fullRidgeMae": full_mae,
                    "incrementalFeatureImprovement": prior_mae - full_mae,
                    "priorOnlyVsPersistence": baseline_mae - prior_mae,
                },
            }
        )
        predictions.extend(
            {
                "year": year,
                "organization": row.organization,
                "actual": float(row.target),
                "predicted": float(predicted[i]),
                "baseline": float(baseline[i]),
                "lower": float(lower[i]),
                "upper": float(upper[i]),
                "priorOnlyRidge": float(prior_ridge[i]),
                "fullRidge": float(full_ridge[i]),
            }
            for i, row in enumerate(test.itertuples())
        )
    if not origins:
        raise ValueError(
            "No eligible audit origins: need at least five forecast target years, "
            "two initial training years, an earlier selection fold, preceding-year "
            "calibration, and at least ten observations per partition and fold."
        )

    def mean(key):
        return float(np.mean([origin[key] for origin in origins]))

    prior_mae = float(np.mean([r["ablation"]["priorOnlyRidgeMae"] for r in origins]))
    full_mae = float(np.mean([r["ablation"]["fullRidgeMae"] for r in origins]))
    return {
        "origins": origins,
        "summary": {
            "nOrigins": len(origins),
            "years": [origin["year"] for origin in origins],
            "n": sum(origin["n"] for origin in origins),
            "mae": mean("mae"),
            "baselineMae": mean("baselineMae"),
            "improvement": mean("improvement"),
            "coverage": mean("coverage"),
            "nominal": 0.90,
            "width": mean("width"),
            "covered": sum(origin["covered"] for origin in origins),
            "originsImproved": sum(origin["improvement"] > 0 for origin in origins),
            "priorOnlyRidgeMae": prior_mae,
            "fullRidgeMae": full_mae,
            "incrementalFeatureImprovement": prior_mae - full_mae,
        },
        "predictions": predictions,
        "notes": [
            "Retrospective expanding-origin sensitivity audit, not fresh independent holdouts. "
            "The same organizations and years recur across origins; later development sets "
            "include earlier audit outcomes. Do not treat origins as independent replications.",
            "All year lists are forecast target years; predictors come from the preceding "
            "survey year. Each origin requires two initial training years, then earlier-only "
            "expanding validation folds. Selection averages MAE equally across validation years; "
            "exact ties prefer persistence. Every fit uses a fresh cloned preprocessing pipeline.",
            "Only development-fold MAE selects the full-feature strategy or persistence. "
            "The winner is frozen before preceding-year calibration and target-year evaluation. "
            "Final training excludes calibration labels; calibration sets only the 90% interval "
            "radius. This audit does not replace the original published selection or test result.",
            "MAE, improvement, and interval width are engagement-index points (0–100). "
            "Positive improvement means baseline MAE minus strategy MAE. Summary metrics are "
            "equal-origin means, not pooled-row estimates; n counts organization-year predictions, "
            "not distinct agencies. No minimum practically meaningful gain was prespecified; "
            "small positive differences alone do not establish actionable benefit.",
            "The Ridge ablation holds alpha, training rows, and preprocessing specification "
            "fixed, comparing prior engagement alone with prior engagement plus all features. "
            "It is diagnostic, not another selection candidate or evidence of causal drivers. "
            "Candidate test errors are post-selection descriptions, not selection inputs.",
            "Intervals use finite-sample absolute calibration residuals and are clipped to "
            "0–100. Nominal 90% coverage is not guaranteed under temporal shift or agency "
            "dependence. Skipped origins lack sufficient earlier folds or partition observations.",
            "Published historical revisions and the globally defined feature set were not "
            "reconstructed as contemporaneous data vintages; this is not a real-time backtest.",
        ],
    }
