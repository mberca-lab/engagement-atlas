from __future__ import annotations

import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

from atlas.methods import feature_correlations
from atlas.modeling import forecast, segmentation
from atlas.source import INTENTION_CROSSWALK, LICENSE_URL, ROOT, SOURCE_URL, ingest
from atlas.statistics import annual_summary, change_analysis


def clean_json(value):
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    return value


def save_json(path, payload):
    path.write_text(
        json.dumps(clean_json(payload), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def export_figures(data, frame):
    folder = ROOT / "outputs" / "figures"
    folder.mkdir(parents=True, exist_ok=True)
    sns.set_style("whitegrid")
    sns.set_palette("colorblind")
    plt.rcParams.update(
        {
            "figure.facecolor": "#f7f4ef",
            "axes.facecolor": "#fcfbf8",
            "text.color": "#242424",
            "axes.labelcolor": "#242424",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.size": 11,
            "svg.fonttype": "none",
        }
    )
    accent = "#b11f4b"
    latest = frame[frame.year == data["meta"]["latestYear"]]
    features = {r["key"]: r["label"] for r in data["meta"]["features"]}

    def save(name, fig):
        fig.tight_layout()
        for extension in ["png", "svg"]:
            path = folder / f"{name}.{extension}"
            fig.savefig(path, dpi=150, bbox_inches="tight")
            if extension == "svg":
                path.write_text(
                    "\n".join(
                        line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()
                    )
                    + "\n",
                    encoding="utf-8",
                )
        plt.close(fig)

    annual = pd.DataFrame(data["annual"])
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.fill_between(
        annual.year,
        annual["min"],
        annual["max"],
        color=accent,
        alpha=0.07,
        label="Range of reporting organizations",
    )
    ax.fill_between(
        annual.year,
        annual.low,
        annual.high,
        color=accent,
        alpha=0.18,
        label="95% organization-bootstrap interval for median",
    )
    ax.plot(
        annual.year, annual["median"], marker="o", color=accent, lw=3, label="Organization median"
    )
    balanced = pd.DataFrame(data["models"]["balancedTrend"])
    ax.plot(
        balanced.year,
        balanced.engagement,
        color="#5c5c5c",
        ls="--",
        label=f"Mean in continuously observed names (n={data['models']['balancedOrgCount']})",
    )
    ax.set(
        title="Engagement over time: trend, spread, and a changing cohort",
        xlabel="Survey year",
        ylabel="Published engagement index (0–100)",
    )
    ax.legend(fontsize=8, loc="lower left")
    save("01-engagement-trajectory", fig)

    fig, ax = plt.subplots(figsize=(10, 6))
    columns = ["engagement", *features]
    names = {"engagement": "Engagement", **features}
    correlation = latest[columns].corr(method="spearman").rename(index=names, columns=names)
    sns.heatmap(
        correlation,
        annot=True,
        fmt=".2f",
        cmap="RdBu_r",
        vmin=-1,
        vmax=1,
        ax=ax,
        square=True,
        cbar_kws={"label": "Spearman rank correlation"},
    )
    ax.set_title(
        "Shared patterns, not independent causal drivers\nLatest-year organization-level indexes; some measures overlap"
    )
    save("02-index-correlation", fig)

    fig, ax = plt.subplots(figsize=(11, 5))
    sizes = ["Very Small", "Small", "Medium", "Large", "Very Large"]
    sns.violinplot(
        data=latest,
        x="agency_size",
        y="engagement",
        order=[s for s in sizes if s in set(latest.agency_size)],
        inner="box",
        color="#d7a6b5",
        ax=ax,
        cut=0,
    )
    ax.set(
        title="Different reporting contexts, different engagement distributions",
        xlabel="Published agency size category",
        ylabel="Engagement index (0–100)",
    )
    save("03-agency-size-distributions", fig)

    metrics = pd.DataFrame(data["models"]["metrics"]).sort_values("mae", ascending=False)
    fig, ax = plt.subplots(figsize=(10, 5))
    positions = np.arange(len(metrics))
    ax.barh(
        positions,
        metrics.mae,
        color=[accent if n == data["models"]["selected"] else "#919191" for n in metrics.name],
    )
    ax.errorbar(
        metrics.mae,
        positions,
        xerr=np.vstack([metrics.mae - metrics.low, metrics.high - metrics.mae]),
        fmt="none",
        ecolor="#242424",
        capsize=4,
    )
    ax.set_yticks(positions, metrics.name)
    ax.set(
        title=f"Does complexity help? Final {data['models']['testYear']} temporal holdout",
        xlabel="Mean absolute error (engagement-index points); 95% organization-bootstrap interval",
        ylabel="Forecast model",
    )
    save("04-model-tournament", fig)

    predictions = pd.DataFrame(data["models"]["predictions"])
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(predictions.actual, predictions.predicted, c=accent, alpha=0.7, s=32)
    ax.plot([0, 100], [0, 100], "--", color="#919191")
    low = min(predictions.actual.min(), predictions.predicted.min()) - 5
    ax.set(
        xlim=(low, 100),
        ylim=(low, 100),
        title=f"Forecast reality check: {data['models']['selected']}",
        xlabel="Observed next-year engagement",
        ylabel="Predicted next-year engagement",
    )
    save("05-predicted-observed", fig)

    points = pd.DataFrame(data["clusters"]["points"])
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(
        data=points, x="x", y="y", hue="cluster", palette="colorblind", s=55, alpha=0.8, ax=ax
    )
    variance = data["clusters"]["variance"]
    ax.set(
        title="A landscape of reporting-agency experience profiles\nDescriptive PCA and K-means; engagement excluded from clustering",
        xlabel=f"Principal component 1 ({variance[0]:.1%} variance)",
        ylabel=f"Principal component 2 ({variance[1]:.1%} variance)",
    )
    save("06-experience-landscape", fig)

    coefficients = pd.DataFrame(data["changeAnalysis"]["coefficients"]).sort_values("estimate")
    fig, ax = plt.subplots(figsize=(11, 5))
    positions = np.arange(len(coefficients))
    ax.errorbar(
        coefficients.estimate,
        positions,
        xerr=np.vstack(
            [coefficients.estimate - coefficients.low, coefficients.high - coefficients.estimate]
        ),
        fmt="o",
        color=accent,
        capsize=5,
    )
    ax.axvline(0, ls="--", color="#919191")
    ax.set_yticks(positions, coefficients.label)
    ax.set(
        title="When experience changes, does engagement change with it?\nYear-adjusted first differences; organization-clustered 95% intervals",
        xlabel="Engagement-index change per one SD of feature change (association, not causation)",
        ylabel="Published survey measure",
    )
    save("07-within-agency-change", fig)

    intention = latest[["engagement", "intent_leave"]].dropna()
    if len(intention) >= 10:
        fig, ax = plt.subplots(figsize=(9, 6))
        ax.scatter(intention.engagement, intention.intent_leave, color=accent, s=40, alpha=0.8)
        ax.set(
            title="Staying is a question, not an observed outcome\n2024 agency aggregates; weighted indexes vs unweighted intentions",
            xlabel="Employee Engagement Index (0–100)",
            ylabel="Considering leaving within next year (%)",
        )
        save("08-engagement-and-intention", fig)


def findings(data):
    meta, models = data["meta"], data["models"]
    latest = next(row for row in data["annual"] if row["year"] == meta["latestYear"])
    first = data["annual"][0]
    selected = next(row for row in models["metrics"] if row["name"] == models["selected"])
    baseline = next(row for row in models["metrics"] if row["name"] == "Persistence")
    relative = (baseline["mae"] - selected["mae"]) / baseline["mae"] * 100
    summary = [
        f"{meta['rowCount']:,} public organization-year estimates across {meta['orgCount']} distinct "
        f"reporting names and {len(meta['years'])} survey years; no individual records.",
        f"The organization median is {latest['median']:.1f} in {meta['latestYear']}, "
        f"compared with {first['median']:.1f} in {first['year']}. The reporting cohort changes; "
        "this is not an official governmentwide respondent-weighted trend.",
        f"Earlier rolling validation selects {models['selected']}. On the untouched "
        f"{models['testYear']} holdout its MAE is {selected['mae']:.2f} points, versus "
        f"{baseline['mae']:.2f} for persistence ({relative:+.1f}% relative error reduction).",
        f"Intervals calibrated for nominal 90% coverage cover {models['interval']['coverage']:.1%} "
        f"of the later test observations; average width {models['interval']['width']:.1f} points. "
        "Temporal distribution shift means coverage is not guaranteed.",
        f"Latest-year K-means selects {data['clusters']['k']} descriptive profiles, with silhouette "
        f"{data['clusters']['silhouette']:.2f} and mean subsample agreement "
        f"{data['clusters']['stability']:.2f}. These are organization profiles, not employee types.",
    ]
    if data["intentionAnalysis"]["n"] >= 10:
        intention = data["intentionAnalysis"]
        summary.append(
            f"Among {intention['n']} explicitly linked agency aggregates, engagement and stated "
            f"intention to leave have Spearman rho {intention['rho']:.2f}. Intention is not "
            "actual turnover, and this relationship is not causal."
        )
    recommendations = [
        "Use the atlas to frame agency-level listening questions; triangulate with local survey "
        "comments, response patterns, job context, and independently measured outcomes.",
        "Treat high component correlations as measurement structure, not proof that a leadership "
        "intervention will raise engagement.",
        "Before operational use, validate on a new survey year and a new organization cohort, "
        "inspect nonresponse bias, and test decision consequences.",
        "Do not rank individual employees, infer demographic fairness, diagnose burnout, "
        "or allocate employment opportunities from these aggregate models.",
    ]
    return {
        "headline": "Work is a relationship. Can we see it changing?",
        "summary": summary,
        "recommendations": recommendations,
    }


def write_report(data):
    lines = [
        "# The Engagement Atlas — findings",
        "",
        "An independent study of real, public OPM FEVS reporting-agency aggregates.",
        "",
        "## Executive interpretation",
        "",
        *[f"- {value}" for value in data["findings"]["summary"]],
        "",
        "## The model comparison",
        "",
        "Model selection uses earlier expanding-window validation, not the final-test ranking.",
        "All final-test results are reported, including models that did not win selection.",
        "",
        "| Model | Test MAE | 95% bootstrap interval | RMSE | R² |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in data["models"]["metrics"]:
        lines.append(
            f"| {row['name']} | {row['mae']:.3f} | {row['low']:.3f}–{row['high']:.3f} "
            f"| {row['rmse']:.3f} | {row['r2']:.3f} |"
        )
    lines += [
        "",
        "## Cross-sectional associations",
        "",
        "Latest-year reporting organizations. Shared content and index composition can make",
        "these associations partly mechanical. BH q-values adjust this family of tests.",
        "",
        "| Measure | Spearman ρ | BH q | Organizations |",
        "|---|---:|---:|---:|",
    ]
    for row in data["correlations"]:
        lines.append(f"| {row['label']} | {row['rho']:.3f} | {row['q']:.3g} | {row['n']} |")
    lines += [
        "",
        "## Annual change, adjusted for survey year",
        "",
        "Coefficients describe associations in index-point change per one SD of feature",
        "change, conditional on the other changes and year effects. They are not causal.",
        "",
        "| Measure | Estimate | Clustered 95% interval | BH q |",
        "|---|---:|---:|---:|",
    ]
    for row in data["changeAnalysis"]["coefficients"]:
        lines.append(
            f"| {row['label']} | {row['estimate']:.3f} | {row['low']:.3f}–{row['high']:.3f}"
            f" | {row['q']:.3g} |"
        )
    lines += [
        "",
        "The engagement subindices are components of the target: the change regression",
        "is partly a decomposition of a composite index, **not discovery of independent HR drivers**.",
        "",
        "## Practical HR questions",
        "",
        *[f"- {value}" for value in data["findings"]["recommendations"]],
        "",
        "## Data quality and limits",
        "",
        *[f"- {value}" for value in data["quality"]["notes"]],
        "",
        "See [methodology](../METHODOLOGY.md) and [sources](../DATA_SOURCES.md).",
        "",
    ]
    (ROOT / "outputs" / "FINDINGS.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    processed = ROOT / "data" / "processed"
    output = ROOT / "outputs"
    processed.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    if args.offline:
        frame = pd.read_csv(processed / "agency_panel.csv")
        meta_source = json.loads((processed / "schema.json").read_text(encoding="utf-8"))
        features = meta_source["features"]
    else:
        if args.refresh:
            for path in (ROOT / "data" / "raw").glob("*.xlsx"):
                if path.name in {
                    "2021-ee.xlsx",
                    "2024-ee.xlsx",
                    "2021-gs.xlsx",
                    "2024-gs.xlsx",
                    "2024-responses.xlsx",
                    "2024-intentions.xlsx",
                }:
                    path.unlink()
        frame, features, manifest, source_sheets = ingest()
        frame.to_csv(processed / "agency_panel.csv", index=False)
        save_json(processed / "schema.json", {"features": features, "sourceSheets": source_sheets})
        save_json(output / "source_manifest.json", manifest)
        save_json(output / "agency_crosswalk.json", INTENTION_CROSSWALK)
    duplicates = int(frame.duplicated(["organization", "year"]).sum())
    if duplicates:
        raise ValueError("Published panel has duplicate organization-year keys.")
    if frame.engagement.isna().any() or not frame.engagement.between(0, 100).all():
        raise ValueError("Engagement outcomes must be observed and on a 0–100 scale.")
    latest_year = int(frame.year.max())
    latest = frame[frame.year == latest_year]
    print(
        f"DATA: {len(frame)} organization-years, {frame.organization.nunique()} reporting names, "
        f"{latest_year} cohort {len(latest)}, predictors {list(features)}",
        flush=True,
    )
    print("Computing temporal forecasts...", flush=True)
    models, panel = forecast(frame, features)
    print("Computing descriptive profiles...", flush=True)
    clusters = segmentation(latest, features)
    print("Computing clustered annual-change uncertainty...", flush=True)
    change, deltas = change_analysis(frame, features)
    panel.to_csv(output / "forecast_panel.csv", index=False)
    deltas.to_csv(output / "annual_changes.csv", index=False)
    intention = latest[["engagement", "intent_leave"]].dropna()
    intention_analysis = {"n": len(intention), "rho": None, "p": None}
    if len(intention) >= 10:
        rho, p = stats.spearmanr(intention.engagement, intention.intent_leave)
        intention_analysis.update({"rho": float(rho), "p": float(p)})
    missing = [
        {
            "feature": key,
            "count": int(frame[key].isna().sum()),
            "pct": float(frame[key].isna().mean() * 100),
        }
        for key in ["engagement", *features, "response_count", "response_rate", "intent_leave"]
    ]
    notes = [
        "Only public reporting-organization aggregates; no employee-level records.",
        "Governmentwide and size-tier totals, plus Defense parent rollup, are excluded.",
        "Organization names match exactly; renames and reorganizations are not guessed.",
        "The latest rolling publication supersedes the earlier edition for overlapping keys.",
        "Only consecutive survey years form forecast and first-difference pairs.",
        "Response counts and intention measures are available only in the 2024 supplement.",
        "Intention-to-leave figures are unweighted; index estimates may use survey weights.",
        "Intention joins use an explicit manually reviewed abbreviation mapping, not an official "
        "OPM harmonization table; ambiguous Defense component scopes are excluded.",
        "Means, medians and uncertainty here describe organizations, not official national estimates.",
        "Three predictors are engagement-index constituents; related satisfaction items may overlap.",
        "Survey nonresponse, rounded estimates, changing cohorts, and common-method bias remain.",
        "Descriptive clusters and retrospective prediction do not establish individual-level fairness "
        "or intervention effectiveness.",
    ]
    data = {
        "meta": {
            "title": "The Engagement Atlas",
            "source": "US OPM Federal Employee Viewpoint Survey",
            "sourceUrl": SOURCE_URL,
            "licenseUrl": LICENSE_URL,
            "years": [int(y) for y in sorted(frame.year.unique())],
            "latestYear": latest_year,
            "orgCount": int(frame.organization.nunique()),
            "rowCount": len(frame),
            "latestOrgCount": len(latest),
            "features": [{"key": key, "label": label} for key, label in features.items()],
            "units": "Published percentage index, 0–100",
            "repositoryUrl": "https://github.com/mberca/engagement-atlas",
            "profileUrl": "https://github.com/mberca",
        },
        "annual": annual_summary(frame),
        "rows": frame.to_dict(orient="records"),
        "correlations": feature_correlations(latest, features),
        "models": models,
        "clusters": clusters,
        "changeAnalysis": change,
        "intentionAnalysis": intention_analysis,
        "quality": {"missing": missing, "duplicates": duplicates, "notes": notes},
    }
    data["findings"] = findings(data)
    save_json(output / "atlas.json", data)
    write_report(data)
    export_figures(data, frame)
    template = ROOT / "docs" / "template.html"
    if template.exists():
        html = template.read_text(encoding="utf-8")
        if html.count("__ATLAS_DATA__") != 1:
            raise ValueError("Story template must contain exactly one data placeholder.")
        payload = json.dumps(clean_json(data), ensure_ascii=False, allow_nan=False).replace(
            "</", "<\\/"
        )
        (ROOT / "docs" / "index.html").write_text(
            html.replace("__ATLAS_DATA__", payload), encoding="utf-8"
        )
        (ROOT / "docs" / ".nojekyll").touch()
    print(
        f"DONE: selected {models['selected']}; test cohort {models['nTest']}; "
        f"intention join {len(intention)}.",
        flush=True,
    )


if __name__ == "__main__":
    main()
