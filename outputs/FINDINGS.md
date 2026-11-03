# The Engagement Atlas — findings

An independent study of real, public OPM FEVS reporting-agency aggregates.

## Executive interpretation

- 630 public organization-year estimates across 85 distinct reporting names and 8 survey years; no individual records.
- The organization median is 74.8 in 2024, compared with 69.4 in 2017. The reporting cohort changes; this is not an official governmentwide respondent-weighted trend.
- Within the same 72 continuously observed names, 58 increased and 14 declined between 2017 and 2024 (0 unchanged). A rising average does not describe every agency.
- Earlier rolling validation selects Persistence. On the untouched 2024 holdout its MAE is 3.34 points, versus 3.34 for persistence (+0.0% relative error reduction).
- Intervals calibrated for nominal 90% coverage cover 86.4% of the later test observations; average width 12.5 points. Temporal distribution shift means coverage is not guaranteed.
- Latest-year K-means selects 2 descriptive profiles, with silhouette 0.43 and mean subsample agreement 0.89. Agreement with a one-score partition is 1.000 (ARI; 1 means identical assignments). These are descriptive score profiles, not validated experience types.
- A separate nested rolling-origin audit covers target years 2022, 2023, 2024. Selection, fitting and calibration use earlier target years at each origin. Equal-year MAE is 2.829 for the selected strategy versus 2.766 for persistence. This retrospective sensitivity analysis is not new independent evidence or a vintage-authentic forecast.
- In the matched Ridge ablation, adding the other prior-year indexes changes equal-year MAE from 2.916 to 2.877: an improvement of +0.038 points. This is descriptive incremental prediction evidence, not an equivalence test or a causal effect.
- Among 34 explicitly linked agency aggregates, engagement and stated intention to leave have Spearman rho -0.62. Intention is not actual turnover, and this relationship is not causal.

## One rising average, different journeys

Follow the same reporting names across all observed years rather than comparing a changing roster. Endpoint directions describe published scores, not statistically significant agency-level changes or improvements caused by an intervention.

## Rolling-origin forecast audit

Retrospective expanding-origin sensitivity audit, not fresh independent holdouts. The same organizations and years recur across origins; later development sets include earlier audit outcomes. Do not treat origins as independent replications.
All year lists are forecast target years; predictors come from the preceding survey year. Each origin requires two initial training years, then earlier-only expanding validation folds. Selection averages MAE equally across validation years; exact ties prefer persistence. Every fit uses a fresh cloned preprocessing pipeline.
Only development-fold MAE selects the full-feature strategy or persistence. The winner is frozen before preceding-year calibration and target-year evaluation. Final training excludes calibration labels; calibration sets only the 90% interval radius. This audit does not replace the original published selection or test result.
MAE, improvement, and interval width are engagement-index points (0–100). Positive improvement means baseline MAE minus strategy MAE. Summary metrics are equal-origin means, not pooled-row estimates; n counts organization-year predictions, not distinct agencies. No minimum practically meaningful gain was prespecified; small positive differences alone do not establish actionable benefit.
The Ridge ablation holds alpha, training rows, and preprocessing specification fixed, comparing prior engagement alone with prior engagement plus all features. It is diagnostic, not another selection candidate or evidence of causal drivers. Candidate test errors are post-selection descriptions, not selection inputs.
Intervals use finite-sample absolute calibration residuals and are clipped to 0–100. Nominal 90% coverage is not guaranteed under temporal shift or agency dependence. Skipped origins lack sufficient earlier folds or partition observations.
Published historical revisions and the globally defined feature set were not reconstructed as contemporaneous data vintages; this is not a real-time backtest.

| Target year | Earlier-selected strategy | Agencies | MAE | Persistence MAE | Improvement | Coverage | Interval width |
|---|---|---:|---:|---:|---:|---:|---:|
| 2022 | Extra trees | 73 | 2.435 | 2.020 | -0.415 | 97.3% | 17.44 |
| 2023 | Extra trees | 77 | 2.712 | 2.940 | +0.228 | 80.5% | 9.84 |
| 2024 | Persistence | 81 | 3.340 | 3.340 | +0.000 | 86.4% | 12.48 |

### Do the extra indexes add predictive information?

Matched Ridge configurations use the same earlier-only training and target agencies. Positive improvement favors the full feature set; no equivalence or causal claim is made.

| Target year | Prior-EEI-only Ridge MAE | Full Ridge MAE | Extra-feature improvement |
|---|---:|---:|---:|
| 2022 | 2.336 | 2.319 | +0.018 |
| 2023 | 3.067 | 3.023 | +0.044 |
| 2024 | 3.343 | 3.290 | +0.053 |

No compatible independently measured turnover outcome has been validated for this panel. Intention-to-leave remains a selected same-survey association, not external outcome validation. A turnover linkage requires documented organization scope, time alignment and workforce denominators before it can support claims.

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
Endpoint directions: 58 increased, 14 declined, 0 unchanged. These are descriptive directions, not agency-level significance tests.
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

## Measurement demonstration: annual change in a composite index

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

## Continuous profiles before discrete clusters

The primary profile view is continuous: the mean of standardized input indexes. K-means is retained as a simplification diagnostic, not a discovery of distinct types.

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
