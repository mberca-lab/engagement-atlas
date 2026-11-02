"""Build an evidence-first notebook; optionally execute in this Python environment."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from textwrap import dedent
from uuid import uuid4

import nbformat

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "engagement_atlas.ipynb"


def build_notebook():
    cells = []

    def markdown(text):
        cells.append(nbformat.v4.new_markdown_cell(dedent(text).strip()))

    def code(text):
        cells.append(nbformat.v4.new_code_cell(dedent(text).strip()))

    markdown(r"""
    # Engagement Atlas
    ## What public workforce surveys can—and cannot—tell an HR leader

    **Margarita Bermejo Cano · HR analytics portfolio · Public organization aggregates**

    A reproducible investigation of the US Office of Personnel Management's Federal
    Employee Viewpoint Survey (FEVS), using published agency-level index results for
    2017–2024. No employee records, simulated outcomes, private customer data, or
    invented survey scores are used.

    **Reading route:** evidence audit → distributions → trends → associations →
    annual changes → next-year prediction → uncertainty → organizational profiles →
    responsible HR decisions.

    Scores are **0–100 published favorable-response index values**, not a validated
    individual engagement scale. A one-point difference is one index point; it is
    not a one-point change on a 0–10 employee rating scale.

    Run the parent pipeline first; this notebook reads its persisted evidence and
    does **not** retrain the headline forecasting or full-feature clustering models.
    Lightweight sensitivity diagnostics are recomputed and checked below. See
    `METHODOLOGY.md` for assumptions, equations, sources, and execution instructions.
    """)
    markdown(r"""
    ## 0. Decision log: freeze the question before looking at results

    | Decision | Rationale / boundary |
    |---|---|
    | Source | Fully public OPM agency aggregates; never respondent microdata |
    | Scope | Rolling 2021 and 2024 EEI/GSI publications, yielding 2017–2024 |
    | Unit | Organization-year for panel descriptions; organization for latest-year views |
    | Sampling | Full processed panel; pair plots alone may use a seeded display sample |
    | EDA depth | Quick + standard + in-depth, with tests limited to meaningful units |
    | Missingness | Preserve unknown / unmatched values; no zero filling |
    | Outliers | Flag plausible extremes for review; retain, never automatically trim |
    | Comparison | Equal organization weighting, not a national employee estimate |
    | Forecast | Predict next-year agency EEI using only prior-year published indexes |
    | Selection | Expanding-window development CV; calibration then final temporal test |
    | Interpretation | Associations and exploratory profiles, not intervention effects |
    | Review gate | Source comparability, index overlap, nonresponse, and coverage |

    **Open questions:** How much do agency entry/exit and name changes affect trends?
    Does persistence beat additional predictors? Are intervals sufficiently reliable
    under year-to-year shifts? What complementary qualitative evidence would change
    an HR decision? Dynamic evidence below answers the empirical parts without
    pre-writing favorable results.
    """)
    code(r"""
    import json
    import platform
    import sys
    from importlib.metadata import version
    from pathlib import Path

    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import seaborn as sns
    from IPython.display import Markdown, display
    from scipy import stats

    candidates = [Path.cwd(), *Path.cwd().parents]
    ROOT = next((p for p in candidates if (p / "atlas" / "source.py").is_file()), None)
    if ROOT is None:
        raise RuntimeError("Start this notebook from engagement-atlas or its notebooks directory.")
    sys.path.insert(0, str(ROOT))
    from atlas.methods import benjamini_hochberg, paired_error_comparison
    from atlas.source import CORE, DOWNLOADS, INTENTION_CROSSWALK, LICENSE_URL, SOURCE_URL
    from atlas.statistics import balanced_longitudinal, intention_analysis

    FIGURES = ROOT / "outputs" / "figures"
    FIGURES.mkdir(parents=True, exist_ok=True)
    SEED = 42
    sns.set_style("whitegrid")
    sns.set_palette("colorblind")
    plt.rcParams.update({"figure.figsize": (10, 5), "axes.spines.top": False,
                         "axes.spines.right": False})
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.max_rows", 35)

    def finish(fig, name):
        fig.savefig(FIGURES / f"notebook_{name}.png", dpi=100, bbox_inches="tight")
        plt.show()
        plt.close(fig)

    required = {
        "agency_panel": ROOT / "data" / "processed" / "agency_panel.csv",
        "atlas": ROOT / "outputs" / "atlas.json",
        "forecast_panel": ROOT / "outputs" / "forecast_panel.csv",
        "annual_changes": ROOT / "outputs" / "annual_changes.csv",
    }
    missing_files = [str(p.relative_to(ROOT)) for p in required.values() if not p.is_file()]
    if missing_files:
        raise FileNotFoundError("Run the parent pipeline first. Missing: " + ", ".join(missing_files))
    df = pd.read_csv(required["agency_panel"])
    evidence = json.loads(required["atlas"].read_text(encoding="utf-8"))
    forecast_panel = pd.read_csv(required["forecast_panel"])
    deltas = pd.read_csv(required["annual_changes"])
    if df.empty or df.duplicated(["organization", "year"]).any():
        raise ValueError("Expected a nonempty, unique organization-year panel; investigate ingestion.")

    def find_section(required_keys, node=evidence):
        # Identify persisted method outputs by their documented schema, not display names.
        if isinstance(node, dict):
            if set(required_keys).issubset(node):
                return node
            for child in node.values():
                found = find_section(required_keys, child)
                if found is not None:
                    return found
        elif isinstance(node, list):
            for child in node:
                found = find_section(required_keys, child)
                if found is not None:
                    return found
        return None

    forecast_result = find_section(["selected", "cv", "interval", "metrics"])
    changes_result = find_section(["coefficients", "correlations", "conditionNumber"])
    clusters = find_section(["candidateScores", "profiles", "points", "variance"])
    if any(item is None for item in [forecast_result, changes_result, clusters]):
        raise ValueError("atlas.json lacks the expected forecasting/change/clustering evidence.")
    labels = {"engagement": "Employee Engagement Index", **CORE,
              "pay_satisfaction": "Pay satisfaction", "job_satisfaction": "Job satisfaction",
              "organization_satisfaction": "Organization satisfaction",
              "recommendation": "Recommendation"}
    index_cols = [c for c in labels if c in df and df[c].notna().any()]
    latest_year = int(df.year.max())
    latest = df.loc[df.year.eq(latest_year)].copy()
    print("Python version:", platform.python_version())
    display(pd.DataFrame({"package": ["pandas", "numpy", "scipy", "scikit-learn",
                                     "seaborn", "nbformat", "nbclient"],
                          "version": [version(p) for p in ["pandas", "numpy", "scipy",
                                                          "scikit-learn", "seaborn",
                                                          "nbformat", "nbclient"]]}))
    """)
    markdown(r"""
    ## 1. Provenance and responsible use

    These rows are **public organization aggregates**, so displaying agency names
    and aggregate values is permissible. Survey respondents remain unobserved.
    Published federal-government works are generally public domain under
    [17 USC §105](https://www.law.cornell.edu/uscode/text/17/105); that does not
    license every third-party asset, OPM mark, or linked work.

    The newer rolling edition takes precedence for overlapping agency-year values.
    Longitudinal names are whitespace-normalized and matched exactly—no fuzzy
    identity guesses. The separate intention-report join uses the manually reviewed
    abbreviation mapping documented in `DATA_SOURCES.md`, not an official OPM
    harmonization table.
    Blank-size governmentwide/tier summaries and overlapping overall parent rows
    are excluded upstream. Defense components may remain; they are not necessarily
    statistically independent institutions.
    """)
    code(r"""
    display(pd.DataFrame([{"publication": name, "url": url}
                          for name, url in DOWNLOADS.items()]))
    print("Source landing page:", SOURCE_URL)
    print("Public-domain legal reference:", LICENSE_URL)
    print("Persisted JSON sections:", list(evidence))
    manifest = find_section(["sha256", "url", "file"])
    if manifest is not None:
        display(pd.DataFrame([manifest]))
    print("All persisted source metadata and findings remain inspectable in the final appendix.")
    """)
    markdown(r"""
    ## 2. Evidence audit: what is actually in the panel?

    Repeated agency observations are **not independent respondents**. Distinguish
    organization-year rows, unique agencies, and available survey respondents.
    Response counts refer to the published 2024 response-rate report, not necessarily
    the denominator of each weighted index or unweighted intention item.
    """)
    code(r"""
    overview = pd.Series({
        "organization_year_rows": len(df),
        "organizations": df.organization.nunique(),
        "columns": len(df.columns),
        "first_year": int(df.year.min()),
        "last_year": latest_year,
        "memory_MB": df.memory_usage(deep=True).sum() / 1024**2,
        "identical_duplicate_rows": int(df.duplicated().sum()),
        "duplicate_organization_years": int(df.duplicated(["organization", "year"]).sum()),
    }, name="value")
    display(overview.to_frame())
    schema = pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "nonmissing": df.notna().sum(),
        "missing_n": df.isna().sum(),
        "missing_pct": df.isna().mean() * 100,
        "unique": df.nunique(),
    })
    schema["cardinality_ratio"] = schema["unique"] / len(df)
    display(schema)
    display(df.head())
    display(df.tail())
    display(df.select_dtypes("number").describe().T)
    for col in df.select_dtypes(include=["object", "category"]):
        print(col, "distinct categories:", df[col].nunique())
        display(df[col].value_counts(dropna=False).head(10).to_frame("organization-year rows"))
    print("Dtype review: year is an integer time key; organization is an identifier, not a predictor.")
    """)
    code(r"""
    missing_by_year = df.groupby("year")[index_cols + [
        c for c in ["response_rate", "response_count", "intent_leave"] if c in df
    ]].agg(lambda s: s.isna().mean() * 100)
    fig, ax = plt.subplots(figsize=(12, 5))
    sns.heatmap(missing_by_year.T, cmap="mako_r", vmin=0, vmax=100,
                cbar_kws={"label": "Missing (%)"}, ax=ax)
    ax.set(title="Coverage, not zero scores: missingness by survey year",
           xlabel="Survey year", ylabel="Published measure")
    finish(fig, "missingness")

    quality = []
    for col in index_cols + [c for c in ["response_rate", "intent_leave",
                                       "intent_retire", "intent_external"] if c in df]:
        values = df[col].dropna()
        q1, q3 = values.quantile([0.25, 0.75])
        lo, hi = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
        quality.append({"measure": col, "n": len(values),
                        "IQR_flags_retained": int(((values < lo) | (values > hi)).sum()),
                        "outside_0_100": int(((values < 0) | (values > 100)).sum())})
    display(pd.DataFrame(quality))
    print("IQR flags are descriptive review signals, not deletion rules. "
          "2024-only auxiliary measures are structurally missing in earlier years.")
    print("Response-count availability:",
          latest["response_count"].notna().sum() if "response_count" in latest else 0,
          "of", len(latest), "latest-year organizations.")
    """)
    markdown(r"""
    ## 3. Distribution atlas: variation is the first HR question

    Use the latest year to avoid treating repeated agencies as independent.
    Histograms show distribution shape; box/violin plots reveal spread and overlap.
    IQR extremes may reflect genuine organizational experiences. Normality tests
    below are shape diagnostics—not an automatic switch between methods.

    Available pay, job, organization-satisfaction, and recommendation measures are
    included in latest-year distributions and correlations even when insufficient
    historical coverage excludes them from forecasting. Descriptive availability
    is not a license to impute an invented historical series.
    """)
    code(r"""
    cols = [c for c in index_cols if latest[c].notna().sum() >= 3]
    predictive_keys = {item["feature"] for item in forecast_result["importance"]}
    display(pd.DataFrame([
        {"measure": col, "latest_year_n": int(latest[col].notna().sum()),
         "role": "Forecast input and EDA" if col in predictive_keys else
                 "Supplemental latest-year EDA; not a forecast input"}
        for col in cols
    ]))
    fig, axes = plt.subplots(len(cols), 2, figsize=(12, 2.6 * len(cols)), squeeze=False)
    for row, col in enumerate(cols):
        sns.histplot(latest, x=col, bins=15, ax=axes[row, 0])
        axes[row, 0].set(title=labels[col], xlabel="Published index (0–100)",
                         ylabel="Organizations")
        sns.boxplot(latest, x=col, ax=axes[row, 1])
        axes[row, 1].set(title=f"{labels[col]}: spread", xlabel="Published index (0–100)")
    fig.tight_layout()
    finish(fig, "distributions")

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.violinplot(latest, x="agency_size", y="engagement", inner="box", cut=0, ax=ax)
    ax.set(title=f"Engagement distributions by OPM agency-size category · {latest_year}",
           xlabel="Published agency-size category", ylabel="EEI (0–100)")
    ax.tick_params(axis="x", rotation=25)
    finish(fig, "size_violin")
    display(latest.groupby("agency_size").engagement.agg(["count", "median", "mean", "std"]))

    shape_rows = []
    for col in cols:
        values = latest[col].dropna()
        if values.nunique() < 2:
            continue
        probe = values.sample(min(len(values), 5000), random_state=SEED)
        statistic, p = stats.shapiro(probe)
        shape_rows.append({"measure": col, "n_organizations": len(values),
                           "skewness": values.skew(), "excess_kurtosis": values.kurt(),
                           "shapiro_W": statistic, "diagnostic_p": p})
    display(pd.DataFrame(shape_rows))
    print("Do not interpret a nonsignificant Shapiro result as proof of normality.")
    """)
    markdown(r"""
    ## 4. Relationships: covariance is not leverage

    Pearson describes **linear** association; Spearman describes **monotonic rank**
    association and is useful with bounded, rounded published values. Both are
    ecological agency-level summaries. Leaders, supervisors, and intrinsic work
    experience are EEI components; satisfaction items may also share content.
    High correlations therefore partly reflect the measurement architecture, not
    independently discovered management drivers.

    The latest-year tests below form one explicitly defined BH-adjusted exploratory
    family: each available index versus engagement. They do not prove causality,
    nor account fully for related agencies or selective response.
    """)
    code(r"""
    corr_cols = [c for c in index_cols if latest[c].notna().mean() > 0.4
                 and latest[c].nunique() > 1]
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    for ax, method in zip(axes, ["pearson", "spearman"]):
        corr = latest[corr_cols].corr(method=method, min_periods=5)
        sns.heatmap(corr, vmin=-1, vmax=1, center=0, annot=True, fmt=".2f",
                    cmap="vlag", ax=ax, cbar_kws={"label": "Agency-level correlation"})
        ax.set(title=f"{method.title()} · {latest_year}", xlabel="Index", ylabel="Index")
    fig.tight_layout()
    finish(fig, "correlations")
    high = []
    corr = latest[corr_cols].corr(method="spearman", min_periods=5)
    for i, first in enumerate(corr_cols):
        for second in corr_cols[i + 1:]:
            value = corr.loc[first, second]
            if abs(value) > 0.7:
                high.append({"index_1": first, "index_2": second, "Spearman_rho": value})
    display(pd.DataFrame(high))

    association_rows = []
    for col in corr_cols:
        if col == "engagement":
            continue
        pair = latest[[col, "engagement"]].dropna()
        if len(pair) >= 5 and pair.nunique().min() > 1:
            rho, p = stats.spearmanr(pair[col], pair.engagement)
            association_rows.append({"feature": col, "rho": rho, "p_exploratory": p,
                                     "n_organizations": len(pair)})
    associations = pd.DataFrame(association_rows)
    if not associations.empty:
        associations["q_BH"] = benjamini_hochberg(associations.p_exploratory)
        display(associations.sort_values("q_BH"))
    pair_cols = corr_cols[:5]
    if len(pair_cols) >= 2:
        sample = latest[pair_cols].sample(min(1000, len(latest)), random_state=SEED)
        grid = sns.pairplot(sample, diag_kind="hist", plot_kws={"alpha": 0.55, "s": 22})
        grid.fig.suptitle(f"Index overlap and nonlinearity · {latest_year} · display only", y=1.02)
        finish(grid.fig, "pairplot")
    """)
    markdown(r"""
    ## 5. Time: compare composition before telling a national story

    Each annual mean/median weights observed agencies equally. The 95% median
    intervals resample agencies within that year; they are **not survey-design
    confidence intervals for the federal workforce**.

    The balanced cohort below requires an exact-name agency with nonmissing EEI in
    **every observed year**, matching the pipeline's persisted `balancedTrend`
    and `balancedOrgCount`. It is not merely the final forecast-test roster.
    Balancing does not solve survivorship or name-change bias.
    Context around 2020 may affect comparability: consult OPM's year-specific
    technical reports before asserting specific redesign, mode, or fieldwork facts.
    """)
    code(r"""
    rng = np.random.default_rng(SEED)
    annual_rows = []
    for year, group in df.groupby("year"):
        values = group.engagement.dropna().to_numpy()
        boot = np.median(values[rng.integers(0, len(values), (2000, len(values)))], axis=1)
        low, high = np.quantile(boot, [0.025, 0.975])
        annual_rows.append({"year": int(year), "n_organizations": len(values),
                            "mean": values.mean(), "median": np.median(values),
                            "median_low": low, "median_high": high})
    annual = pd.DataFrame(annual_rows)
    wide = df.pivot(index="organization", columns="year", values="engagement")
    balanced = wide.dropna()
    if len(balanced) != forecast_result["balancedOrgCount"]:
        raise ValueError("Balanced-cohort count differs between CSV and JSON; regenerate the pipeline.")
    persisted_balanced = pd.DataFrame(forecast_result["balancedTrend"]).set_index("year")
    if len(balanced) and not np.allclose(
        balanced.mean().to_numpy(),
        persisted_balanced.loc[balanced.columns, "engagement"].to_numpy()
    ):
        raise ValueError("Balanced-cohort means differ between CSV and JSON; regenerate the pipeline.")
    display(annual)
    print("Balanced exact-name agencies:", len(balanced), "of", df.organization.nunique())
    cohort_check = balanced_longitudinal(df)
    if not np.allclose(
        [cohort_check[k] for k in ["meanChange", "low", "high"]],
        [evidence["cohortSensitivity"][k] for k in ["meanChange", "low", "high"]]
    ):
        raise ValueError("Balanced endpoint diagnostics disagree with persisted evidence.")
    display(pd.Series({k: cohort_check[k] for k in
                       ["n", "firstYear", "lastYear", "meanChange", "low", "high"]}))
    print(cohort_check["interpretation"])
    fig, ax = plt.subplots()
    ax.plot(annual.year, annual["mean"], marker="o", label="All observed: mean")
    ax.plot(annual.year, annual["median"], marker="s", label="All observed: median")
    ax.fill_between(annual.year.to_numpy(), annual.median_low.to_numpy(),
                    annual.median_high.to_numpy(), alpha=0.18, label="95% agency-bootstrap median CI")
    if len(balanced):
        ax.plot(balanced.columns, balanced.mean(), marker="^", label="Balanced cohort: mean")
    ax.set(title="Equal-agency trends: composition is part of the signal",
           xlabel="Survey year", ylabel="EEI (0–100)")
    ax.legend(fontsize=8)
    finish(fig, "annual_trends")
    if len(balanced):
        fig, ax = plt.subplots()
        for organization in balanced.index:
            ax.plot(balanced.columns, balanced.loc[organization], color="gray", alpha=0.08)
        ax.plot(balanced.columns, balanced.median(), color=sns.color_palette()[0],
                linewidth=3, label="Balanced median")
        ax.set(title="Balanced-agency trajectories: heterogeneity behind the average",
               xlabel="Survey year", ylabel="EEI (0–100)")
        ax.legend()
        finish(fig, "balanced_trajectories")
    """)
    markdown(r"""
    ## 6. Annual changes: a more demanding association question

    Only consecutive-year, exact-name observations are differenced. The persisted
    regression adjusts for common year effects and simultaneous standardized
    feature changes; organization-clustered standard errors allow within-agency
    dependence. Coefficients mean **EEI points per one SD of annual feature change**,
    not points per one-unit level difference. BH correction applies to this
    coefficient family.

    Whole-agency trajectory bootstrap intervals accompany Spearman change
    correlations. The displayed `pNaive` ignores repeated agencies and is not the
    primary inferential evidence. Differencing does not remove changing response
    composition, reverse causality, index overlap, or time-varying confounding.
    """)
    code(r"""
    display(pd.Series({key: changes_result[key] for key in
                       ["n", "organizations", "r2", "conditionNumber"]}).to_frame("value"))
    change_corr = pd.DataFrame(changes_result["correlations"])
    coefficients = pd.DataFrame(changes_result["coefficients"])
    display(change_corr)
    display(coefficients)
    display(deltas.head())
    display(deltas.select_dtypes("number").describe().T)
    print("Rows in persisted annual-change panel:", len(deltas),
          "| Unique organizations:", deltas.organization.nunique())
    if not coefficients.empty:
        ordered = coefficients.sort_values("estimate")
        fig, ax = plt.subplots(figsize=(10, 5))
        positions = np.arange(len(ordered))
        ax.hlines(positions, ordered.low, ordered.high, color=sns.color_palette()[0])
        ax.scatter(ordered.estimate, positions)
        ax.axvline(0, color="gray", linestyle="--")
        ax.set_yticks(positions, ordered.label)
        ax.set(title="Annual-change regression: clustered 95% coefficient intervals",
               xlabel="EEI points per SD of feature change", ylabel="Index change")
        finish(fig, "change_coefficients")
    display(Markdown("**Collinearity gate:** Review the condition number and interval widths. "
                     "Shared index components can make adjusted signs unstable; "
                     "a surprising coefficient is not an intervention recommendation."))
    """)
    markdown(r"""
    ## 7. Forecasting lab: does complexity beat last year's score?

    **Target:** next-year published agency EEI. Exact-name joins require consecutive
    years. Prior-year EEI and source-selected index features are used; 2024-only
    response and intention measures are excluded from forecasting.

    **Development:** target years 2018–2022. The first two supply warm-up training;
    expanding-window scored folds therefore begin later than 2018. Mean fold MAE
    (equal weighting of folds, not agencies pooled across years) selects persistence
    or one of five fixed configurations: Ridge, ElasticNet, Random Forest,
    Extra Trees, and histogram gradient boosting. Imputation/scaling fit within
    each training partition. Predictions are clipped to the index's 0–100 domain.

    Models are frozen after training on targets before 2023. **2023 calibrates**
    uncertainty; **2024 is the final temporal test**, never a model-selection set.
    The retrospective table includes all candidates for transparency, not to
    replace the development winner with the best test score.
    """)
    code(r"""
    split_rows = []
    for name, subset in [
        ("Development", forecast_panel[forecast_panel.target_year <
                                        forecast_result["calibrationYear"]]),
        ("Calibration", forecast_panel[forecast_panel.target_year ==
                                        forecast_result["calibrationYear"]]),
        ("Final test", forecast_panel[forecast_panel.target_year == forecast_result["testYear"]]),
    ]:
        split_rows.append({"partition": name, "organization_year_rows": len(subset),
                           "organizations": subset.organization.nunique(),
                           "target_years": sorted(subset.target_year.unique().tolist())})
    display(pd.DataFrame(split_rows))
    cv = pd.DataFrame(forecast_result["cv"])
    display(cv.pivot(index="year", columns="name", values="mae"))
    selection = pd.DataFrame(forecast_result["selection"])
    display(selection.rename(columns={"mae": "mean_development_fold_MAE"}))
    metrics = pd.DataFrame(forecast_result["metrics"])
    metrics["selected_by_development"] = metrics.name.eq(forecast_result["selected"])
    display(metrics.rename(columns={"low": "MAE_CI_low", "high": "MAE_CI_high"}))
    print("Locked winner:", forecast_result["selected"])
    print("Final test year:", forecast_result["testYear"])
    comparison_predictions = pd.DataFrame(forecast_result["modelPredictions"])
    comparisons = pd.DataFrame(forecast_result["pairedComparisons"])
    for row in comparisons.itertuples():
        candidate = comparison_predictions[comparison_predictions.model == row.name]
        check = paired_error_comparison(candidate.actual, candidate.predicted, candidate.baseline)
        if not np.allclose([check[k] for k in ["difference", "low", "high"]],
                           [row.difference, row.low, row.high]):
            raise ValueError(f"Paired forecast comparison mismatch: {row.name}")
    display(comparisons)
    print(forecast_result["comparisonNotes"])
    fig, ax = plt.subplots(figsize=(11, 5))
    sns.lineplot(cv, x="year", y="mae", hue="name", marker="o", ax=ax)
    ax.set(title="Expanding-window validation: no future-year training",
           xlabel="Held-out target year", ylabel="MAE (EEI points)")
    ax.legend(title="Candidate", fontsize=8)
    finish(fig, "temporal_cv")
    """)
    markdown(r"""
    ## 8. Calibration and error: uncertainty is part of the product

    A split-conformal-style radius uses the finite-sample order statistic of 2023
    absolute residuals, with 90% nominal coverage. The clipped intervals are
    evaluated in 2024. Temporal shifts and related agencies undermine exchangeability:
    **nominal coverage is an aspiration, not a guaranteed future-year promise**.

    MAE confidence intervals resample final-test organizations (one row per agency).
    They quantify uncertainty conditional on the observed organizations and year,
    not model-selection uncertainty or all future workforce environments.
    """)
    code(r"""
    predictions = pd.DataFrame(forecast_result["predictions"])
    predictions["residual"] = predictions.actual - predictions.predicted
    predictions["absolute_error"] = predictions.residual.abs()
    predictions["covered"] = predictions.actual.between(predictions.lower, predictions.upper)
    predictions["interval_width"] = predictions.upper - predictions.lower
    display(pd.Series(forecast_result["interval"]).to_frame("interval evidence"))
    display(predictions.sort_values("absolute_error", ascending=False).head(10))
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    axes[0].scatter(predictions.actual, predictions.predicted, alpha=0.6)
    axes[0].plot([0, 100], [0, 100], "--", color="gray")
    axes[0].set(title="Locked model: final-test predictions", xlabel="Observed EEI",
                ylabel="Predicted EEI")
    axes[1].scatter(predictions.predicted, predictions.residual, alpha=0.6)
    axes[1].axhline(0, color="gray", linestyle="--")
    axes[1].set(title="Residual diagnostic", xlabel="Predicted EEI",
                ylabel="Observed − predicted (points)")
    finish(fig, "forecast_diagnostics")
    sample = predictions.sort_values("predicted").iloc[
        np.linspace(0, len(predictions) - 1, min(30, len(predictions)), dtype=int)
    ]
    fig, ax = plt.subplots(figsize=(12, 5))
    positions = np.arange(len(sample))
    ax.vlines(positions, sample.lower, sample.upper, alpha=0.55, label="Calibrated interval")
    ax.scatter(positions, sample.predicted, label="Predicted")
    ax.scatter(positions, sample.actual, marker="x", label="Observed")
    ax.set(title="Final-test intervals · evenly spaced ordered display sample",
           xlabel="Organization order by prediction (not identity)", ylabel="EEI (0–100)")
    ax.legend()
    finish(fig, "forecast_intervals")
    error_audit = predictions.merge(latest[["organization", "agency_size"]], on="organization",
                                    how="left", validate="one_to_one")
    display(error_audit.groupby("agency_size").agg(
        n_organizations=("organization", "size"), MAE=("absolute_error", "mean"),
        observed_coverage=("covered", "mean"), mean_width=("interval_width", "mean")))
    print("Size-category diagnostics are organizational error checks, not employee fairness tests.")
    """)
    markdown(r"""
    ## 9. Model explanation and transportability: distinct questions

    Permutation importance explains the **best development-CV ML model**, even if
    persistence won selection. Positive importance means worse MAE after
    shuffling that input on the final test. It does not measure causal leverage;
    correlated features can substitute for one another. Importance uses the
    estimator's raw predictions, whereas reported metrics clip predictions.
    Its repeat standard deviation is not a confidence interval.

    Five-fold GroupKFold holds entire agencies out **within development** as an
    unseen-agency sensitivity check. It mixes years and is not prospective
    temporal validation or evidence of deployment performance in a new year.
    """)
    code(r"""
    print("Permutation explanation model:", forecast_result["explanationModel"])
    importance = pd.DataFrame(forecast_result["importance"]).sort_values("mean")
    display(importance)
    display(pd.Series(forecast_result["transportability"]).to_frame("group-holdout sensitivity"))
    fig, ax = plt.subplots()
    ax.barh(importance.label, importance["mean"], xerr=importance["std"], alpha=0.8)
    ax.axvline(0, color="gray", linestyle="--")
    ax.set(title="Predictive reliance, not HR intervention impact",
           xlabel="Increase in MAE when shuffled (± repeat SD)", ylabel="Prior-year input")
    finish(fig, "permutation_importance")
    """)
    markdown(r"""
    ## 10. Profile studio: describe similarities without labeling people

    Latest-year complete profiles are standardized; **engagement is excluded from
    clustering inputs**. KMeans candidates range from k=2 to k=5 when sample size
    permits; maximum silhouette selects k. PCA provides a two-dimensional view,
    not the space in which clustering is fitted.

    Stability is mean adjusted Rand agreement across 30 seeded 80% subsamples
    against the full solution, on common organizations. Scaling is held fixed
    from the full eligible sample, so this is conditional assignment stability,
    not a complete pipeline uncertainty estimate.

    Profile numbers are arbitrary. They are **not diagnoses, causal segments,
    employee archetypes, or labels such as “toxic” or “high risk.”**
    """)
    code(r"""
    display(pd.Series({key: clusters[key] for key in
                       ["k", "silhouette", "stability", "variance"]}).to_frame("value"))
    display(pd.DataFrame(clusters["candidateScores"]))
    from sklearn.cluster import KMeans
    from sklearn.metrics import adjusted_rand_score
    from sklearn.preprocessing import StandardScaler
    from threadpoolctl import threadpool_limits

    cluster_features = [row["feature"] for row in clusters["loadings"]]
    eligible = latest.dropna(subset=cluster_features)
    scaled = StandardScaler().fit_transform(eligible[cluster_features])
    with threadpool_limits(limits=2):
        level_labels = KMeans(n_clusters=clusters["k"], n_init=30, random_state=SEED).fit_predict(
            scaled.mean(axis=1).reshape(-1, 1)
        )
    full_labels = pd.DataFrame(clusters["points"]).set_index("organization").loc[
        eligible.organization, "cluster"
    ]
    level_agreement = adjusted_rand_score(full_labels, level_labels)
    if not np.isclose(level_agreement, clusters["levelCheck"]["adjustedRand"]):
        raise ValueError("One-score cluster diagnostic disagrees with persisted evidence.")
    display(pd.Series(clusters["levelCheck"]).to_frame("one-score simplification check"))
    loadings = pd.DataFrame(clusters["loadings"])
    display(loadings)
    points = pd.DataFrame(clusters["points"])
    points["profile"] = points.cluster.map(lambda value: f"Profile {int(value) + 1}")
    print("Eligible latest-year organizations:", len(points), "of", len(latest))
    fig, ax = plt.subplots()
    sns.scatterplot(points, x="x", y="y", hue="profile", alpha=0.8, ax=ax)
    ax.set(title=f"Organizational survey profiles · {latest_year}",
           xlabel=f"PC1 ({clusters['variance'][0]:.1%} explained variance)",
           ylabel=f"PC2 ({clusters['variance'][1]:.1%} explained variance)")
    ax.legend(title="Exploratory profile")
    finish(fig, "cluster_pca")
    profile_rows = [
        {"profile": item["name"], "n": item["n"],
         "engagement_context_only": item["engagement"], **item["features"]}
        for item in clusters["profiles"]
    ]
    profile_table = pd.DataFrame(profile_rows).set_index("profile")
    display(profile_table)
    feature_keys = loadings.feature.tolist()
    fig, ax = plt.subplots(figsize=(12, 5))
    sns.heatmap(profile_table[feature_keys], annot=True, fmt=".1f", cmap="viridis",
                vmin=0, vmax=100, ax=ax, cbar_kws={"label": "Mean published index"})
    ax.set(title="Profiles: raw-index means for interpretation", xlabel="Input index",
           ylabel="Arbitrary profile")
    finish(fig, "cluster_profiles")
    """)
    markdown(r"""
    ## 11. Retention lens: intentions are not exits

    The 2024 demographic report is **unweighted**. `intent_leave` combines the
    published “yes” categories for intending to leave the organization; retirement
    and external departure are distinct motives. Inspect workbook headers before
    giving a more specific interpretation to derived categories.

    This is neither actual turnover nor employee-level attrition prediction.
    The response-rate report has a different purpose and denominator. Associations
    with EEI cannot be translated into an individual's departure probability,
    headcount at risk, or the expected ROI of a retention intervention.

    **Join limitation:** `atlas.source.INTENTION_CROSSWALK` is an explicit,
    manually reviewed acronym-to-name mapping—not an official OPM harmonization
    table. A mapped name must also exist in the latest index cohort. Army, Navy,
    Marine Corps, USACE, and Defense 4th Estate are excluded because naming,
    exclusions, or reporting scope require separate reconciliation; Air Force is
    retained. No fuzzy matching or automatic component-to-parent merging is used.
    Linked agencies are a selected supplement, not the entire cohort.
    """)
    code(r"""
    retention_cols = [c for c in ["intent_leave", "intent_retire", "intent_external",
                                  "response_rate", "response_count", "surveyed"] if c in latest]
    intention_pairs = latest.dropna(subset=["engagement", "intent_leave"])
    print("Linked organizations with engagement and intention to leave:",
          len(intention_pairs), "of", len(latest), "latest-year organizations.")
    if len(intention_pairs) != evidence["intentionAnalysis"]["n"]:
        raise ValueError("Intention sample differs between CSV and JSON; regenerate the pipeline.")
    intention_check = intention_analysis(latest)
    for key in ["rho", "low", "high", "leaveOneOutLow", "leaveOneOutHigh"]:
        if not np.isclose(intention_check[key], evidence["intentionAnalysis"][key]):
            raise ValueError(f"Intention sensitivity diagnostic mismatch: {key}")
    display(pd.Series({k: intention_check[k] for k in
                       ["n", "rho", "low", "high", "leaveOneOutLow", "leaveOneOutHigh",
                        "leaveOneOutValid", "bootstrapValid", "bootstrapDraws"]}))
    display(pd.DataFrame(intention_check["selection"]))
    display(pd.DataFrame(intention_check["sizeComposition"]))
    print(intention_check["interpretation"])
    print("Sizes with no linked agencies:", intention_check["unrepresentedSizes"])
    provenance_cols = ["organization", "intent_leave"] + [
        c for c in ["intent_source_code", "intent_response_count"] if c in latest
    ]
    display(intention_pairs[provenance_cols].sort_values("organization"))
    display(pd.DataFrame([{"source_abbreviation": code, "mapped_organization": name}
                          for code, name in INTENTION_CROSSWALK.items()]))
    display(latest[retention_cols].describe().T)
    retention_rows = []
    for col in [c for c in retention_cols if c not in ["surveyed", "response_count"]]:
        pair = latest[["engagement", col]].dropna()
        if len(pair) >= 5 and pair.nunique().min() > 1:
            rho, p = stats.spearmanr(pair.engagement, pair[col])
            retention_rows.append({"measure": col, "n_organizations": len(pair),
                                   "rho": rho, "p_exploratory": p})
    retention_tests = pd.DataFrame(retention_rows)
    if not retention_tests.empty:
        retention_tests["q_BH_auxiliary_family"] = benjamini_hochberg(retention_tests.p_exploratory)
        display(retention_tests)
    if "intent_leave" in latest and latest.intent_leave.notna().sum() >= 3:
        fig, ax = plt.subplots()
        sns.scatterplot(latest, x="engagement", y="intent_leave", hue="agency_size",
                        alpha=0.7, ax=ax)
        ax.set(title=f"Agency-level intention to leave versus engagement · {latest_year}",
               xlabel="EEI (published favorable-response index)",
               ylabel="Intend to leave organization (unweighted %)")
        finish(fig, "intention_lens")
    """)
    markdown(r"""
    ## 12. HR decision briefing: evidence → question → safe next step

    | Evidence type | Appropriate use | Inappropriate use |
    |---|---|---|
    | Distribution / trend | Identify variation and comparability questions | National employee trend from equal-agency means |
    | Concurrent index association | Describe co-occurring perceptions | Call a shared component an independent driver |
    | Annual-change association | Prioritize hypotheses for triangulation | Claim that an intervention causes the coefficient |
    | Locked forecast | Benchmark next-year organization-level expectations | Predict individual performance or departures |
    | Calibrated interval | Communicate uncertainty and observed coverage | Promise nominal coverage under arbitrary shifts |
    | Profile cluster | Structure exploratory leadership conversations | Diagnose organizations or classify employees |
    | Intention aggregate | Discuss reasons people consider leaving | Estimate realized turnover or monetary ROI |

    **A practical action sequence**
    1. Verify source coverage and year comparability with the public technical reports.
    2. Bring domain experts into interpretation; compare index overlap with item wording.
    3. Use interviews or approved local research to triangulate a specific hypothesis.
    4. Design a prospective evaluation with a comparison group before claiming impact.
    5. Monitor forecast errors, interval coverage, response patterns, and composition
       at the next release; freeze a new evaluation plan before opening its outcomes.

    No respondent-level psychometric reliability, measurement invariance,
    protected-group fairness, or individual-level causal inference can be estimated
    from this panel. Organization-size error checks do not substitute for those tests.
    """)
    code(r"""
    winner = metrics.loc[metrics.name.eq(forecast_result["selected"])].iloc[0]
    baseline = metrics.loc[metrics.name.eq("Persistence")].iloc[0]
    display(Markdown(
        f"### Evidence-led summary\n"
        f"- Panel: **{len(df):,} organization-years**, **{df.organization.nunique():,} "
        f"exact-name organizations**, {int(df.year.min())}–{latest_year}.\n"
        f"- Balanced all-year cohort: **{len(balanced):,} organizations**; compare its trajectory "
        f"with all-observed means before attributing change.\n"
        f"- Development-selected forecast: **{forecast_result['selected']}**. "
        f"Final-test MAE **{winner.mae:.2f} EEI points** "
        f"(agency-bootstrap 95% CI {winner.low:.2f}–{winner.high:.2f}); "
        f"persistence MAE **{baseline.mae:.2f}**. This is not a causal or individual model.\n"
        f"- Final-test interval coverage: **{forecast_result['interval']['coverage']:.1%}**, "
        f"versus nominal **{forecast_result['interval']['nominal']:.0%}**; "
        f"mean width **{forecast_result['interval']['width']:.2f} points**.\n"
        f"- Exploratory profiles: **{clusters['k']}**, silhouette "
        f"**{clusters['silhouette']:.3f}**, conditional mean subsample ARI "
        f"**{clusters['stability']:.3f}**. Do not turn them into diagnostic labels.\n"
        f"- Intention-to-leave supplement: **{len(intention_pairs):,} linked organizations** "
        f"using a manually reviewed, non-official abbreviation crosswalk; "
        f"intentions are not actual turnover.\n"
        f"- Outstanding limitations: overlapping index content, response selection, "
        f"agency dependence, publication rounding, temporal comparability, and "
        f"unobserved respondent composition."
    ))
    print("Notebook figures saved to:", FIGURES.relative_to(ROOT).as_posix())
    """)
    markdown(r"""
    ## Appendix: the complete persisted evidence

    Tables and plots above are rendered from processed files; the full JSON below
    preserves upstream findings and source metadata, including sections not
    summarized in the narrative. There are no hardcoded empirical findings.
    """)
    code(r"""
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    """)

    notebook = nbformat.v4.new_notebook(cells=cells)
    notebook.metadata = {
        "kernelspec": {
            "display_name": "Python (engagement-atlas environment)",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": platform_version()},
    }
    nbformat.validate(notebook)
    return notebook


def platform_version():
    return ".".join(str(part) for part in sys.version_info[:3])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute using this exact Python interpreter (run the pipeline first).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Per-cell execution timeout in seconds (default: 300).",
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    notebook = build_notebook()
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, NOTEBOOK)
    if args.execute:
        from jupyter_client import AsyncKernelManager
        from jupyter_client.kernelspec import KernelSpec
        from nbclient import NotebookClient

        connection_file = NOTEBOOK.parent / f".engagement-atlas-kernel-{uuid4().hex}.json"
        manager = AsyncKernelManager(kernel_name="python3", connection_file=str(connection_file))
        # Avoid global kernelspec installation and unrelated system Python kernels.
        manager._kernel_spec = KernelSpec(
            argv=[sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            display_name="Python (engagement-atlas environment)",
            language="python",
        )
        client = NotebookClient(
            notebook, km=manager, timeout=args.timeout, resources={"metadata": {"path": str(ROOT)}}
        )
        try:
            client.execute(cwd=str(ROOT), cleanup_kc=True)
        finally:
            # Preserve diagnostic outputs on failure without claiming a successful run.
            nbformat.write(notebook, NOTEBOOK)
            connection_file.unlink(missing_ok=True)
    print(f"{'Executed' if args.execute else 'Created'} {NOTEBOOK}")


if __name__ == "__main__":
    main()
