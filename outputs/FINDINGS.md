# The Engagement Atlas — findings

An independent study of real, public OPM FEVS reporting-agency aggregates.

## Executive interpretation

- 630 public organization-year estimates across 85 distinct reporting names and 8 survey years; no individual records.
- The organization median is 74.8 in 2024, compared with 69.4 in 2017. The reporting cohort changes; this is not an official governmentwide respondent-weighted trend.
- Earlier rolling validation selects Persistence. On the untouched 2024 holdout its MAE is 3.34 points, versus 3.34 for persistence (+0.0% relative error reduction).
- Intervals calibrated for nominal 90% coverage cover 86.4% of the later test observations; average width 12.5 points. Temporal distribution shift means coverage is not guaranteed.
- Latest-year K-means selects 2 descriptive profiles, with silhouette 0.43 and mean subsample agreement 0.89. These are organization profiles, not employee types.
- Among 34 explicitly linked agency aggregates, engagement and stated intention to leave have Spearman rho -0.62. Intention is not actual turnover, and this relationship is not causal.

## The model comparison

Model selection uses earlier expanding-window validation, not the final-test ranking.
All final-test results are reported, including models that did not win selection.

| Model | Test MAE | 95% bootstrap interval | RMSE | R² |
|---|---:|---:|---:|---:|
| Extra trees | 3.266 | 2.385–4.307 | 5.384 | 0.581 |
| Ridge | 3.290 | 2.255–4.644 | 6.337 | 0.419 |
| Elastic net | 3.296 | 2.258–4.649 | 6.315 | 0.423 |
| Persistence | 3.340 | 2.172–4.909 | 6.991 | 0.293 |
| Gradient boosting | 3.426 | 2.541–4.456 | 5.506 | 0.562 |
| Random forest | 3.494 | 2.587–4.509 | 5.537 | 0.557 |

## Cross-sectional associations

Latest-year reporting organizations. Shared content and index composition can make
these associations partly mechanical. BH q-values adjust this family of tests.

| Measure | Spearman ρ | BH q | Organizations |
|---|---:|---:|---:|
| Leaders lead | 0.936 | 4.62e-37 | 81 |
| Intrinsic work experience | 0.923 | 3.18e-34 | 81 |
| Global satisfaction | 0.901 | 2.44e-30 | 81 |
| Supervisory support | 0.848 | 1.87e-23 | 81 |

## Annual change, adjusted for survey year

Coefficients describe associations in index-point change per one SD of feature
change, conditional on the other changes and year effects. They are not causal.

| Measure | Estimate | Clustered 95% interval | BH q |
|---|---:|---:|---:|
| Leaders lead | 2.714 | 2.694–2.733 | 9.44e-125 |
| Supervisory support | 1.842 | 1.829–1.856 | 1.78e-124 |
| Intrinsic work experience | 1.650 | 1.633–1.667 | 8.47e-112 |
| Global satisfaction | 0.008 | -0.010–0.025 | 0.395 |

The engagement subindices are components of the target: the change regression
is partly a decomposition of a composite index, **not discovery of independent HR drivers**.

## Practical HR questions

- Use the atlas to frame agency-level listening questions; triangulate with local survey comments, response patterns, job context, and independently measured outcomes.
- Treat high component correlations as measurement structure, not proof that a leadership intervention will raise engagement.
- Before operational use, validate on a new survey year and a new organization cohort, inspect nonresponse bias, and test decision consequences.
- Do not rank individual employees, infer demographic fairness, diagnose burnout, or allocate employment opportunities from these aggregate models.

## Data quality and limits

- Only public reporting-organization aggregates; no employee-level records.
- Governmentwide and size-tier totals, plus Defense parent rollup, are excluded.
- Organization names match exactly; renames and reorganizations are not guessed.
- The latest rolling publication supersedes the earlier edition for overlapping keys.
- Only consecutive survey years form forecast and first-difference pairs.
- Response counts and intention measures are available only in the 2024 supplement.
- Intention-to-leave figures are unweighted; index estimates may use survey weights.
- Intention joins use an explicit manually reviewed abbreviation mapping, not an official OPM harmonization table; ambiguous Defense component scopes are excluded.
- Means, medians and uncertainty here describe organizations, not official national estimates.
- Three predictors are engagement-index constituents; related satisfaction items may overlap.
- Survey nonresponse, rounded estimates, changing cohorts, and common-method bias remain.
- Descriptive clusters and retrospective prediction do not establish individual-level fairness or intervention effectiveness.

See [methodology](../METHODOLOGY.md) and [sources](../DATA_SOURCES.md).
