# The Engagement Atlas — findings

An independent study of real, public OPM FEVS reporting-agency aggregates.

## Executive interpretation

- 630 public organization-year estimates across 85 distinct reporting names and 8 survey years; no individual records.
- The organization median is 74.8 in 2024, compared with 69.4 in 2017. The reporting cohort changes; this is not an official governmentwide respondent-weighted trend.
- Earlier rolling validation selects Persistence. On the untouched 2024 holdout its MAE is 3.34 points, versus 3.34 for persistence (+0.0% relative error reduction).
- Intervals calibrated for nominal 90% coverage cover 86.4% of the later test observations; average width 12.5 points. Temporal distribution shift means coverage is not guaranteed.
- Latest-year K-means selects 2 descriptive profiles, with silhouette 0.43 and mean subsample agreement 0.89. Agreement with a one-score partition is 1.000 (ARI; 1 means identical assignments). These are descriptive score profiles, not validated experience types.
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

### Paired differences versus persistence

Positive differences mean lower MAE than persistence on the same held-out agencies. Percentile 95% intervals use 5,000 paired agency resamples with seed 42. These post-hoc diagnostics do not change validation-based model selection, adjust for five comparisons, or include model-training uncertainty. Related agencies may weaken the independent-agency resampling assumption.

| Model | MAE improvement (points) | Paired 95% interval | Agencies |
|---|---:|---:|---:|
| Extra trees | 0.074 | -0.522–0.921 | 81 |
| Ridge | 0.049 | -0.320–0.449 | 81 |
| Elastic net | 0.043 | -0.344–0.465 | 81 |
| Gradient boosting | -0.086 | -0.758–0.792 | 81 |
| Random forest | -0.155 | -0.770–0.680 | 81 |

## Consistent-cohort sensitivity

The same 72 reporting names observed every year have mean engagement 70.48 in 2017 and 76.03 in 2024: a mean paired change of +5.55 points (95% agency-bootstrap interval 3.73–7.24).
Sensitivity comparison: the same reporting names in every observed year. Paired agency-bootstrap intervals describe this observed cohort, not national employee sampling uncertainty. Related agencies weaken the resampling assumption. Names do not guarantee unchanged agency boundaries or workforces.

## Interval coverage context

70 of 81 held-out outcomes are covered (86.4%, nominal 90%). Illustrative 95% Wilson interval: 77.3%–92.2%. The illustrative 95% Wilson interval assumes independent coverage events and fixed predictions; it does not correct agency dependence or temporal shift. This does not establish calibration or correct the temporal coverage shortfall.

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
Its in-sample R² is 0.99993; a close compositional fit is not external validation.

## Profile distinctiveness check

Compare the full-feature partition with K-means on just the average standardized input score, using the same agencies and k. ARI=1 means identical assignments up to label permutation; this is a descriptive simplification check, not independent validation.
Observed adjusted Rand agreement: 1.000.

## Intention-to-leave sensitivity and coverage

Among 34 linked agencies, Spearman rho is -0.62 (95% paired agency-bootstrap interval -0.85–-0.27); leaving out one agency at a time gives -0.73 to -0.58 across 34 defined estimates.
A distinct same-survey question, not an external or causal validation. Agency-bootstrap and leave-one-out checks are conditional on the selected linked agencies; they do not correct nonresponse, selection, or common-method bias.
Agency sizes without linked observations: Very Small.

| Agency size | Linked | Not linked |
|---|---:|---:|
| Large | 9 | 0 |
| Medium | 16 | 0 |
| Small | 3 | 26 |
| Very Large | 6 | 3 |
| Very Small | 0 | 18 |

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
