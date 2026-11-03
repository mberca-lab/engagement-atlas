# Engagement Atlas: methodology and interpretation contract

## 1. Purpose

This portfolio asks a practical HR question: **how can published workforce-survey
aggregates support organizational conversations without pretending to measure
individual employees or causal intervention effects?**

The analytical sequence is deliberately demanding: audit provenance and coverage;
describe heterogeneity; compare annual compositions; distinguish level associations
from change associations; benchmark predictive models against persistence; assess
temporal uncertainty; and describe exploratory organizational profiles.

The notebook consumes persisted pipeline outputs. It does not train expensive ML
models again, and this document does not pre-write or invent empirical results.
Every displayed finding is calculated from the downloaded publications or the
pipeline's CSV/JSON evidence.

## 2. Public, non-personal data and provenance

**Publisher:** US Office of Personnel Management (OPM), Federal Employee Viewpoint
Survey (FEVS). **Scope:** published agency-level aggregates covering 2017–2024.
There are no individual response records, employee identifiers, private customer
records, synthetic replacement observations, or inferred employee profiles.
Public agency names and their published aggregate values may be displayed.

The authoritative landing page is:
<https://www.opm.gov/fevs/reports/data-reports/>.

`atlas/source.py` is the executable URL registry. It downloads:

- 2021 and 2024 Employee Engagement Index (EEI) agency-result XLSX editions;
- 2021 and 2024 Global Satisfaction Index (GSI) agency-result XLSX editions;
- the 2024 response-rate-by-agency XLSX;
- the 2024 unweighted demographic-question-by-agency XLSX, including intention
  to leave the organization.

The 2021 and 2024 index publications contain rolling historical columns; an
edition year is not the year of every observation in that workbook. The newer
edition takes precedence for overlapping organization-year values. Raw workbooks
are retained, and the pipeline records source URLs, byte lengths, retrieval date,
and SHA-256 hashes. Cached-file retrieval dates indicate the pipeline's access
date, not necessarily an original download timestamp. Publication revisions can
change results, so compare hashes when reproducing an older run.

Federal-government works are generally public domain under
[17 USC §105](https://www.law.cornell.edu/uscode/text/17/105). This statement applies
to the government publications, not indiscriminately to third-party linked assets,
trademarks, or every file on a government website. The repository's software license
is separate. Cite OPM and retain the provenance manifest when sharing findings.

**Responsible-use boundary:** public availability does not justify attempts to
reidentify respondents. Conclusions remain at organization level. This project is
not a workflow for ingesting protected internal HR data.

## 3. Measurement contract and analytical units

| Field | Meaning | Interpretation boundary |
|---|---|---|
| `organization` | Normalized published agency name | Exact-name identity, not a stable administrative identifier |
| `agency_size` | Published OPM size category | Organizational category, not a respondent demographic |
| `year` | Survey-result year | Annual published observation, not employee event time |
| `engagement` | Published EEI, 0–100 | Favorable-response index, not a 0–10 individual rating |
| `leaders`, `supervisors`, `intrinsic` | Published EEI component indexes | Components overlap the target by construction |
| `satisfaction` | Published GSI | May share content or covary strongly with other indexes |
| Optional satisfaction/recommendation fields | Source-detected published index/item percentages | Availability varies; do not manufacture absent columns |
| `response_count`, `response_rate`, `surveyed` | 2024 response-rate report aggregates | Not automatically the denominator or weight for every index/item |
| `intent_leave`, `intent_retire`, `intent_external` | 2024 derived unweighted intention aggregates | Intentions, not realized turnover |

Source percentages are kept as publication values, rather than silently replacing
them with simulated 0–10 scores. Bounds checks flag values outside 0–100.
Published rounding and suppression limit precision; additional decimal places in
model output do not add measurement precision.

### Covariance and overlapping indexes

EEI components are not independent constructs accidentally correlated with EEI.
If a target is an aggregate of component scores, then covariance with a component
partly follows algebraically: for \(E=\sum_j w_jX_j\),
\(\operatorname{Cov}(X_i,E)=\sum_jw_j\operatorname{Cov}(X_i,X_j)\).
This equation explains the general structural issue; it is not a claim that the
pipeline has reconstructed OPM's exact weighting formula.

Concurrent correlations and regressions can therefore overstate apparent
"drivers." Even next-year prediction benefits from shared content and persistence.
Multicollinearity can produce unstable adjusted coefficients or surprising signs.
Do not convert their ranks, signs, or permutation importance into an action priority
without independent substantive evidence.

### Ecological inference and unavailable analyses

The panel contains organization-years, not people. A correlation between agency
means need not equal the within-agency employee relationship and may reverse it.
It cannot identify an individual's engagement, departure probability, protected
characteristics, performance, or response pattern.

Respondent-level reliability (e.g., Cronbach's alpha or omega), factor validity,
measurement invariance, respondent-level missingness, and protected-group fairness
cannot be established from these indexes. Aggregate agency-size error comparisons
are useful diagnostics, **not employee fairness tests**. No microdata are inferred
to fill these gaps.

## 4. Ingestion, inclusion, and quality checks

1. Read actual XLSX sheet headers; map recognized index sheets to named measures.
2. Normalize whitespace in agency names without fuzzy matching or heuristic mergers.
3. Parse publication numbers, preserve missing/suppressed values, and reject
   out-of-domain index values.
4. Prefer the 2024 rolling edition for overlapping keys.
5. Exclude blank-size governmentwide/tier summaries and overlapping overall parent
   rows, including the Defense overall parent, while retaining eligible components.
   The actual code excludes names ending in `, Overall`; verify the resulting
   organization roster against publication hierarchy.
6. Require unique organization-year keys for forecast construction and one-to-one
   joins for auxiliary reports. The intention supplement first uses the explicit,
   manually reviewed acronym mapping in `atlas.source.INTENTION_CROSSWALK`;
   this is not an official OPM harmonization table (see section 12).
7. Include optional predictive indexes only when the source parser recognizes
   them and their overall nonmissing coverage is at least 85%.

The forecast and change panels join **only exact names in consecutive years**.
An agency renamed, reorganized, omitted, or unmatched is not silently treated as
the same agency. This protects identity integrity but can create attrition and
survivorship bias. Defense components and other related agencies may still have
correlated experiences; excluding an overlapping parent does not guarantee
independence.

The notebook reports schema, memory use, first/last rows, descriptive statistics,
category cardinality, identical duplicates, duplicate keys, missingness by year,
and 0–100 violations. IQR outliers are flagged, **retained**, and interpreted in
context. No winsorization, automatic deletion, or zero filling is applied.
2024-only auxiliary measures are structurally missing before 2024, not negative
evidence about earlier workforce experiences.

Whole-panel coverage-based optional-feature selection is a source availability
decision, not target-driven model selection. Nevertheless, for strictly prospective
deployment the schema should also be frozen using information available at that
forecast origin.

## 5. EDA: descriptions before tests

The notebook integrates quick, standard, and in-depth EDA:

- row counts and **separate counts of unique organizations**;
- missingness, duplicates, bounded-score checks, and schema recommendations;
- numeric descriptions, histograms, box plots, and agency-size violin plots;
- latest-year shape diagnostics (skewness, excess kurtosis, Shapiro–Wilk);
- Pearson and Spearman heatmaps, high-correlation pairs, and pair plots limited
  to five features;
- annual trends, balanced-cohort trajectories, change distributions, persisted
  regression/forecast/interval tables, PCA profiles, and intention context.

Latest-year distribution and concurrent-test views use one row per organization.
Available pay satisfaction, job satisfaction, organization satisfaction, and
recommendation measures enter latest-year distributions, shape diagnostics, and
correlations even when sparse historical coverage excludes them from forecasting.
The notebook explicitly displays each measure's role and available organization
count. In the current source panel the four core indexes—leaders, supervisors,
intrinsic work experience, and global satisfaction—are the only additional
forecast predictors; prior-year EEI is also an input. Supplemental latest-year
availability does not justify reconstructing missing historical values.
Histograms and bounded rounded scores do not require normality. Shapiro–Wilk is a
shape diagnostic, not proof of normality when nonsignificant or an automatic
rule for choosing an inferential test. Sampling is used only for display-limited
pair plots, with a fixed seed; the main processed panel is not sampled away.

Chi-square tests on artificial engagement bins are intentionally omitted. These
are percentages with unavailable item-level cell counts, not a respondent
contingency table. Arbitrary cutoffs would discard information and suggest
unsupported precision.

All notebook figures use a white-grid style, colorblind-friendly categorical
palette, labeled axes, and titles. They are saved under `outputs\figures` with a
`notebook_` prefix. They supplement, rather than overwrite, parent-pipeline figures.

## 6. Annual descriptions and composition sensitivity

For each observed year, the pipeline describes the mean, median, range, and
number of organizations with engagement values. Each organization receives equal
weight. A 2,000-draw agency bootstrap estimates a percentile 95% interval for the
annual median.

These intervals describe agency resampling conditional on that year's observed
roster. They are **not** respondent-weighted national employee estimates,
design-based survey confidence intervals, or confidence intervals for temporal
differences. Related agencies weaken the independent-agency resampling assumption.
Do not use the 2024 response counts to retroactively weight earlier years or assume
they reproduce OPM's index weighting.

The notebook also constructs a true all-observed-years balanced cohort: an
exact-name agency must have nonmissing engagement in every observed year.
This matches the pipeline's `models.balancedTrend`, based on the intersection of
agency names present across all observed years, with its size recorded in
`models.balancedOrgCount`. It is not merely the final forecast-test roster.
The notebook checks its independently constructed count and annual means against
the persisted balanced evidence to detect stale or inconsistent artifacts.
Balanced and all-observed comparisons reveal composition sensitivity; they do not
eliminate survival bias or changes inside agencies.

The published `cohortSensitivity` diagnostic also computes each continuously
observed agency's last-minus-first change. A 5,000-draw paired agency bootstrap
(seed 42) gives a percentile 95% interval for their mean change. Each resample
retains an agency's endpoint pair. This is a coverage-sensitivity check conditional
on the observed roster, not a causal effect, a respondent-level confidence interval,
or a remedy for correlated agencies.

Pandemic-era organizational conditions, survey administration changes, nonresponse,
and revised measurement can affect temporal comparability. **Do not assert exact
2020 redesign, survey-mode, item, or fieldwork changes without checking OPM's
year-specific technical documentation.** The notebook makes no unsupported claim
about their precise direction or magnitude.

## 7. Concurrent associations and multiple testing

Pearson correlation describes linear co-variation in published continuous index
values. Spearman correlation describes monotonic rank association and tolerates
rounding, boundedness, and some nonlinearity; ties still affect interpretation.
Both use pairwise available observations, so sample sizes can vary.

The notebook's primary concurrent descriptive view is latest-year, one row per
organization. Its explicitly defined exploratory family tests each available
nonconstant index against engagement, followed by Benjamini–Hochberg (BH) adjusted
q-values. A separate auxiliary family covers intention/response-rate associations.
The upstream pipeline may also persist concurrent summaries; inspect their
population before equating them with the notebook's latest-year table.

Report effect sizes, denominators, and index overlap alongside p/q-values.
BH adjustment addresses multiplicity within the stated family under its dependence
conditions; it does not fix sampling bias, related agencies, structural covariance,
selective reporting, or causal identification. Very small p-values can coexist
with an uninformative management claim.

## 8. Annual-change inference

For feature \(X_j\), define consecutive-year agency changes:

\[
\Delta E_{it}=E_{it}-E_{i,t-1},\qquad
\Delta X_{jit}=X_{jit}-X_{ji,t-1}.
\]

The pipeline uses complete observations across all selected change features.
This keeps the correlation/regression populations aligned but can exclude agencies
with missing optional features. Inspect the retained row and organization counts
before generalizing.

### Correlations

Spearman change correlations are accompanied by percentile 95% intervals from
500 whole-agency trajectory bootstrap draws. A sampled agency brings all its
eligible changes, preserving within-agency temporal dependence. The bootstrap
assumes sufficiently independent agencies; cross-agency dependence remains.
The persisted `pNaive` treats changes as independent and is shown for transparency,
**not as the primary inferential basis**.

### Regression

\[
\Delta E_{it}=\alpha+\sum_j\beta_j Z(\Delta X_{jit})
             +\gamma_t+\varepsilon_{it}.
\]

Predictor changes are standardized using the analysis sample. Engagement changes
remain in index points. Thus \(\beta_j\) is EEI points per one sample SD of feature
change, conditional on the other selected changes and year indicators.
OLS includes year fixed effects, organization-clustered standard errors, and
cluster-based t inference. BH adjusts the selected feature-coefficient family;
year effects are nuisance adjustments, not substantive tested drivers.

First differencing removes stable agency-level additive effects, not changing
employee composition, omitted time-varying causes, reverse causality, shared item
content, or all measurement error. Inspect the condition number and interval
widths for collinearity. Few or related clusters compromise standard-error
reliability. A coefficient is not a predicted intervention effect.

**Role in the story:** this regression is a measurement demonstration rather
than the headline scientific result. Changes in constituent indexes can almost
reconstruct changes in their composite; very high in-sample fit and narrow
intervals therefore do not establish independently useful HR drivers.

## 9. Leakage-aware next-year forecasting

### Target and features

Predict \(E_{i,t+1}\) from prior-year \(E_{it}\) and available selected index features.
No future-year predictors, organization-name encoding, 2024 response data, or
2024 intention data enter the feature matrix. Exact consecutive-year matching
defines the forecast sample; it does not extrapolate across missing years.

### Temporal experiment

| Stage | Target years | What can happen here |
|---|---|---|
| Development | 2018–2022 | Expanding-window training/validation and selection |
| Calibration | 2023 | Estimate interval radius for the locked winner |
| Final test | 2024 | Evaluate frozen predictions and calibrated intervals |

The code derives the last two available target years as calibration/test; the
intended 2017–2024 panel produces the schedule above. Verify displayed partitions
if the source panel changes.

The first two development target years provide warm-up history. Scored folds
therefore use 2020–2022, training on strictly earlier target years each time.
Selection minimizes **mean fold MAE**, weighting each held-out year equally.
It is not a random row split, pooled cross-validation MAE, or a broad
hyperparameter search.

Persistence predicts the next index as the current index. Five fixed model
configurations benchmark additional complexity:

| Candidate | Key configuration |
|---|---|
| Ridge | Mean imputation, standardization, alpha 10 |
| ElasticNet | Mean imputation, standardization, alpha 0.1, L1 ratio 0.3 |
| Random Forest | Mean imputation; 250 trees, leaf minimum 5, feature fraction 0.8 |
| Extra Trees | Mean imputation; 250 trees, leaf minimum 5 |
| Histogram gradient boosting | Mean imputation; 150 iterations, 7 leaves, learning rate 0.05, L2 10 |

All preprocessing fits on each training fold only. Models use seed 42 where
applicable. Forecasts are clipped to 0–100; record this when comparing to another
implementation. `atlas/modeling.py` is authoritative for complete configurations.
The selected candidate is refitted using all development targets, **not 2023**.
The same frozen fit predicts calibration and final test.

### Evaluation and honest reporting

The final test reports MAE, RMSE, and R² for persistence and all candidates.
MAE/RMSE are in index points; R² can be negative and describes performance relative
to the test sample mean. A 2,000-draw bootstrap resamples final-test organizations
to give a percentile 95% MAE interval. One final-test row per organization makes
row and organization resampling equivalent here.

The test table is a retrospective transparency artifact: **do not select a new
winner from it**. Candidate comparisons share agencies; overlapping marginal
intervals do not constitute a paired significance test. Bootstrap intervals do
not capture training/model-selection uncertainty or generalize automatically to
future years.

The paired comparison resamples **within-agency absolute-error differences**:
`abs(actual − persistence) − abs(actual − candidate)`. Positive values favor the
candidate. Percentile 95% intervals use 5,000 agency draws with seed 42. Every
candidate uses exactly the same held-out agencies; `outputs/model_predictions.csv`
preserves all candidate predictions for independent inspection. These post-hoc
intervals are not adjusted for five comparisons, do not refit models, and do not
change the development-selected winner. Agency dependence remains a limitation;
an interval spanning zero is not proof of equivalence.

The paired-error swarm displays each held-out agency's absolute-error difference
on the same symmetric horizontal scale across ML comparators. Vertical packing
only prevents overlap; it encodes no additional variable. All comparisons require
the complete original test-agency roster, identical actual scores and identical
persistence forecasts. The default comparator is the development-selected ML
explanation model, not a new winner chosen using these dots. Lower-error counts,
the mean difference and the existing paired interval should be read together:
many small differences can offset a few large ones. No new inferential test or
model selection is introduced by this visualization.

This experiment backtests the last observed year. It is not a verified live
2025 forecast or a model of individual engagement.

### Separate nested rolling-origin robustness audit

`atlas/validation.py` repeats the protocol for each eligible target year:
reserve the immediately preceding target year for calibration; use only earlier
targets for development; select from persistence and the same five fixed ML
configurations using expanding-window folds within that development period;
fit the locked winner on development; calibrate and evaluate without refitting.
Two earlier target years provide warm-up before the first inner validation fold.
The current panel supports audit targets 2022, 2023 and 2024. The original
2024 headline model selection and predictions are not replaced.

Every origin records training, inner-selection, calibration and evaluation
years, per-agency predictions, MAE, baseline MAE, interval coverage and width.
Summaries weight eligible target years equally rather than pooling correlated
agency-years as independent observations. A matched Ridge ablation compares
prior EEI alone with prior EEI plus the other indexes under the same partitions
and preprocessing. Incremental predictive performance is not a causal effect.

**Information boundary:** this audit was added after the historical outcomes
were available. It is retrospective sensitivity analysis, not a set of fresh
independent tests. The panel combines rolling publications that may revise
historical values, and source-availability feature selection uses the full
published panel. Earlier-only observation-year fitting does not reconstruct
the data and feature schema actually available at each historical forecast
origin. An as-of-vintage prospective evaluation would require dated archived
publications and a frozen schema. Related agencies and repeated organizations
also prevent treating all audit rows as independent evidence.

### Predictive explanation and agency transportability

Thirty-repeat permutation importance on the final test describes the best
development-selected **ML** model, even when persistence is the operational
winner. Positive importance indicates increased MAE after shuffling; correlated
inputs can mask or redistribute importance. Repeat SD is not a confidence interval.
The importance routine uses raw estimator predictions while reported model metrics
are clipped; edge cases can therefore differ. Test-set explanations must not be
used to retune the already evaluated model.

Five-fold GroupKFold holds whole agencies out in development for that ML model.
It is an unseen-agency sensitivity analysis. Years can be mixed between training
and validation, so it is **not prospective temporal validation** and does not
replace the untouched-year test.

## 10. Calibrated intervals and distribution shift

For absolute calibration errors \(r_i=|E_i-\hat E_i|\), take the sorted error at
rank \(\lceil(n+1)\times0.90\rceil\) as radius \(q\), using one-based indexing.
If that rank exceeds the calibration sample, the implementation returns an
infinite radius. Prediction intervals are
\([\max(0,\hat E-q),\min(100,\hat E+q)]\).

The notebook reports nominal coverage, observed 2024 coverage, mean interval
width, and the calibration radius. It also visualizes residuals, observed versus
predicted values, and an evenly spaced display sample of intervals.

Finite-sample conformal coverage reasoning requires exchangeability between
calibration and test examples. Successive survey years, related agencies,
selection changes, and workforce shocks can violate that requirement.
Consequently these are **split-conformal-style temporal intervals, not an
unconditional coverage guarantee**. An observed coverage shortfall should be
reported rather than corrected using the final test.

The story also reports the covered count and an illustrative 95% **Wilson binomial
interval** around the observed coverage fraction. Its independence and fixed-
prediction assumptions are not guaranteed for related agencies in one target year.
Including nominal coverage does not establish calibration; this diagnostic is
context, not a reason to retune intervals on test outcomes.

Latest-year agency-size MAE/coverage tables are exploratory organizational
diagnostics. Small category samples and selection make them unstable; they
cannot establish protected-group employee fairness.

## 11. Exploratory profiles: PCA and KMeans

**Presentation decision:** show a continuous landscape first, colored by each
eligible agency's mean standardized input index. This is a descriptive summary
with no validated cutoff, not a new psychometric scale. The KMeans partitions
remain available as a diagnostic of whether discretization adds information.
If the one-score partition is identical, do not claim distinct experience types.

The latest-year clustering sample requires complete values across selected input
features. It excludes engagement as a clustering input, standardizes the remaining
indexes, and fits KMeans in the full standardized feature space.

Candidates k=2–5 are considered when the sample-size rule permits them. The rule
limits candidate k using total sample size; it does **not** guarantee at least
ten agencies in every resulting cluster. The maximum silhouette score selects k.
KMeans uses 30 initializations and a fixed seed.

PCA is fitted to the standardized input features and projects organizations into
two dimensions for visualization. Displayed explained variance and loadings clarify
what is lost and what contributes to the plot. Cluster membership is not fitted
in the two-dimensional PCA display.

Thirty 80% subsamples are reclustered, and adjusted Rand agreement with the full
solution is computed on common agencies. The full-sample scaling is held fixed,
so this is **conditional assignment stability**, not end-to-end preprocessing
stability or confirmation of a true population segmentation.

A separate simplification check averages each agency's standardized input scores
and fits one-dimensional KMeans with the **same eligible agencies and selected k**.
Adjusted Rand agreement compares it with the unchanged full-feature assignments.
ARI=1 means identical partitions up to arbitrary label numbering. High agreement
shows how much grouping can be obtained from overall score level alone; it does
not validate distinct experience types or independently confirm a segmentation.

Profile means are shown on the raw index scale. Engagement is context after
clustering, not an input. Cluster numbers are arbitrary; use neutral “Profile N”
labels. Correlated/overlapping input indexes can implicitly overweight common
constructs. These profiles are exploratory conversational aids, not diagnoses,
causal segments, independent validation of survey constructs, or employee types.

## 12. Intention to leave: a descriptive retention lens

### Explicit mapping, provenance, and coverage limitations

The unweighted demographic report identifies agencies by abbreviations, whereas
the index panel uses full names. `atlas.source.INTENTION_CROSSWALK` is an explicit,
**manually reviewed acronym-to-name mapping, not an official OPM harmonization
table**. No single official harmonization table was located. A mapped name must
also exist in the 2024 index cohort before its aggregate is retained. This
auxiliary mapping is separate from the exact-name longitudinal forecast/change
joins; no fuzzy matching is used.

Army, Navy, Marine Corps, USACE, and Defense 4th Estate are deliberately excluded
from this supplement because item-report exclusions or ambiguous naming/reporting
scope require separate reconciliation. Air Force's directly matching label is
retained. These choices do not imply that excluded Defense components are removed
from the main index panel.

`intent_source_code` preserves the original publication abbreviation, and
`intent_response_count` preserves the unweighted report's respondent total. The
notebook displays linked provenance, the explicit mapping, and the current paired
sample count from CSV/JSON rather than hardcoding it. Selected matching agencies
are a subset of the index cohort, not representative of all agencies; conclusions
must be bounded to this supplement. See `DATA_SOURCES.md` for source-join details.

### Outcome meaning

The 2024 **unweighted** demographic publication contains “yes” intention categories.
The parser sums the four published “yes” columns for `intent_leave`, retains the
first as `intent_retire`, and the third as `intent_external`. It checks their total
with the “no” category against approximately 100%, allowing publication rounding.
**Inspect the original header wording and ordering** before assigning more
specific substantive meanings to the derived subcategories.

Retirement, moves within government, and departure outside the organization can
have different HR implications. Do not treat this derived measure as realized
turnover, an attrition label, a headcount forecast, or an individual probability.
Item nonresponse and unweighted demographic percentages mean the response-rate
count is not automatically their denominator. Weighted index results and
unweighted intention aggregates are not interchangeable statistics.

The notebook's agency-level scatter and BH-adjusted auxiliary correlations describe
co-occurrence only. They cannot estimate retention-intervention ROI or causal effects.

For the complete engagement/intention pairs, a 3,000-draw paired agency bootstrap
(seed 42) reports a percentile 95% Spearman interval. Constant-score resamples are
undefined and excluded, with the retained count disclosed. Leave-one-agency-out
correlations show sensitivity to single agencies; undefined deletions are counted
rather than treated as zero. Neither check corrects selection or common-method bias.
Linked versus unlinked counts, median engagement, median response rate, and agency-
size composition make coverage differences visible. These are descriptive
comparisons, not a missing-at-random test or a guarantee of representativeness.

### Independent outcome validation: deliberately not claimed

OPM publishes actual separation counts through its
[federal workforce datasets](https://www.opm.gov/data/datasets/) and
[FedScope separations catalog](https://catalog.data.gov/dataset/fedscope-separations-cubes).
Availability alone does not establish a valid join. FEVS reporting organizations
and personnel-system agency/subagency codes can have different scopes; counts
also require compatible workforce denominators and a justified time window.
No validated scope-preserving crosswalk and denominator alignment was established
for this panel in the bounded source review. No such outcome was therefore
ingested or imputed. The matched lagged-feature ablation tests incremental
prediction within the existing survey, not external criterion validity.

## 13. HR interpretation and decision gates

An appropriate briefing separates **observation**, **hypothesis**, **uncertainty**,
and **next evidence needed**:

1. Confirm coverage, organization hierarchy, name continuity, and year comparability.
2. Inspect effect magnitude and structural index overlap before saying “driver.”
3. Triangulate an organizational hypothesis with domain experts and qualitative
   research conducted under the appropriate local data governance.
4. If intervention impact matters, design prospective evaluation with defensible
   comparison groups; these aggregates alone do not supply causal identification.
5. At the next release, monitor composition, response availability, error by
   organizational context, and interval coverage before revising the model.
6. Freeze a new prospective validation plan before examining its held-out outcomes.

Avoid rankings that imply validated agency quality, personnel decisions, employee
diagnoses, or “toxic” clusters. Public sector findings need not transport to
private employers, other countries, or another measurement system.

## 14. Reproduction and notebook execution

Run from the project root in PowerShell, using the project's existing environment:

```powershell
Set-Location C:\Users\mbermejocano\DEV\engagement-atlas
.\.venv\Scripts\python.exe scripts\create_notebook.py
```

Default behavior creates `notebooks\engagement_atlas.ipynb` without executing it.
First run the parent data/analysis pipeline documented in the repository README.
The notebook requires:

- `data\processed\agency_panel.csv`;
- `outputs\atlas.json`;
- `outputs\forecast_panel.csv`;
- `outputs\annual_changes.csv`.

Then execute and persist outputs:

```powershell
.\.venv\Scripts\python.exe scripts\create_notebook.py --execute --timeout 300
```

The generator uses `nbformat`; execution uses `nbclient` with an explicit kernel
launch command pointing to **the same `sys.executable` as the generator**. It does
not rely on an unrelated global Jupyter kernel or install a global kernelspec.
The notebook prints Python and package versions, plus a project-relative figure
path, without publishing the local interpreter or home-directory path. Missing input artifacts
produce an actionable failure instead of fabricated fallback data.

Interactive runs should select the same environment. Root discovery accepts the
project root or a descendant such as `notebooks`. Notebook plots are saved to
`outputs\figures\notebook_*.png`; source and analysis artifacts remain unchanged.
The final JSON appendix preserves all upstream findings. A failing executed cell
is persisted for diagnosis and the command returns failure; a partially executed
notebook is not a successful run.

The notebook deliberately avoids retraining ML or KMeans. Lightweight EDA,
descriptive bootstrapping, and latest-year association diagnostics are recomputed
from the saved panel. Seeds make these calculations reproducible within the
recorded package environment; different library versions, updated workbooks, or
changed upstream methods can still alter results.

## 15. Limitations checklist for every portfolio presentation

- Organization aggregation and ecological fallacy; no individual-level conclusions.
- Overlapping index components and correlated measurement content.
- Unavailable reliability, factor validity, employee fairness, and respondent data.
- Publication rounding, suppression, optional-feature coverage, and complete-case selection.
- Exact-name matching, agency reorganizations, survivorship, and changing composition.
- Related agencies and imperfect independent-organization resampling assumptions.
- Nonresponse, unknown item denominators, weighting differences, and survey comparability.
- Pandemic-era context without unsupported precise survey-redesign assertions.
- Fixed-model search scope, limited scored temporal folds, and single final test year.
- Temporal exchangeability limits for calibrated uncertainty.
- Conditional clustering stability, arbitrary labels, and no causal segment interpretation.
- Intentions versus actual turnover; no invented business-impact or ROI estimates.

**Bottom line:** the strongest portfolio result is not necessarily the most complex
model or the smallest p-value. It is an auditable chain from public evidence to an
honest, bounded HR decision.
