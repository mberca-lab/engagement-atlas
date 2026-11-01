# Data source, reuse, and boundaries

## Real, public, organization-level HR statistics

The **US Office of Personnel Management Federal Employee Viewpoint Survey
(OPM FEVS)** publishes agency-level employee survey reports. This project uses
only those public aggregated results—not public-use employee microdata.

Publication hub: https://www.opm.gov/fevs/reports/data-reports/

| Edition | Report | Direct source |
|---|---|---|
| 2021 | Employee Engagement Index, with historical columns 2017–2021 | [XLSX](https://www.opm.gov/fevs/reports/data-reports/index-results-by-agency/employee-engagement-index-results-by-agency/2021/2021-ee-report-excel.xlsx) |
| 2024 | Employee Engagement Index, with historical columns 2020–2024 | [XLSX](https://www.opm.gov/fevs/reports/data-reports/index-results-by-agency/employee-engagement-index-results-by-agency/2024/2024-ee-report-excel.xlsx) |
| 2021 | Global Satisfaction Index and available component sheets | [XLSX](https://www.opm.gov/fevs/reports/data-reports/index-results-by-agency/global-satisfaction-index-results-by-agency/2021/2021-gs-report-excel.xlsx) |
| 2024 | Global Satisfaction Index and available component sheets | [XLSX](https://www.opm.gov/fevs/reports/data-reports/index-results-by-agency/global-satisfaction-index-results-by-agency/2024/2024-gs-report-excel.xlsx) |
| 2024 | Agency response rates | [XLSX](https://www.opm.gov/fevs/reports/data-reports/data-reports/response-rate-by-agency/2024/2024-response-rate-by-agency-excel.xlsx) |
| 2024 | Unweighted demographic report, intention-to-leave question only | [XLSX](https://www.opm.gov/fevs/reports/data-reports/data-reports/report-on-demographic-questions-by-agency/2024/2024-unweighted-demographics-report-excel.xlsx) |

The demographic workbook is used **only for published agency totals on the
intention-to-leave question**. Its protected-characteristic tables are neither
extracted into the analysis nor used to score employees or evaluate demographic
fairness.

## Data dictionary

| Variable | Meaning | Unit |
|---|---|---|
| `organization` | Published reporting agency/component name | Public organization name |
| `agency_size` | Source reporting size category | Categorical; historical values from retained edition |
| `year` | Survey year of the published estimate | Integer |
| `engagement` | Employee Engagement Index | Published percentage index, 0–100 |
| `leaders` | EEI Leaders Lead subindex | Published percentage index, 0–100 |
| `supervisors` | EEI Supervisors subindex | Published percentage index, 0–100 |
| `intrinsic` | EEI Intrinsic Work Experience subindex | Published percentage index, 0–100 |
| `satisfaction` | Global Satisfaction Index | Published percentage index, 0–100 |
| `pay_satisfaction`, `job_satisfaction`, `organization_satisfaction`, `recommendation` | Component sheets if available consistently across years | Published favorable percentage, 0–100 |
| `response_count`, `surveyed` | Responses and invitations in response-rate report | Counts; 2024 only |
| `response_rate` | Published response percentage | Percent; 2024 only |
| `intent_leave` | Sum of four published "Yes" intention-to-leave categories | Percent; 2024 only |
| `intent_retire`, `intent_external` | "Yes, to retire" and "Yes, to other job outside Govt" | Percent; 2024 only |
| `intent_source_code`, `intent_response_count` | Published agency abbreviation and respondent total in the unweighted report | Provenance; 2024 only |

The EEI is a composite of its three subindices. Global satisfaction and
recommendation measures can share content with engagement items. Relationships
between overlapping indexes **must not be marketed as independent causal
drivers**. Models forecast a future aggregate; they do not validate the survey's
psychometrics.

## Integrity and continuity

- SHA-256, file size, download URL, and retrieval date are persisted in
  `outputs/source_manifest.json`.
- For overlapping organization-years, the 2024 edition supersedes the 2021
  edition. The panel includes agencies observed in either edition, not a
  fixed population of continuously operating agencies.
- A forecast pair is created only for identical public organization names and
  consecutive years. This is conservative: it may lose renamed agencies.
  It does not assert legal organizational continuity.
- Blank size-tag governmentwide and size-tier rollups are removed.
  The `Department of Defense, Overall` parent rollup is also removed while
  its component reporting organizations are retained.
- Missing values and published suppression markers are not converted to zero.
  No respondent counts or confidence limits are reconstructed from rounded
  percentages.
- Source response-count totals need not equal item-level response bases.
  Intention percentages come from the **unweighted** demographic report;
  they are not necessarily directly comparable to weighted index estimates.

### Intention-report crosswalk

The demographic report uses agency abbreviations rather than full names.
`INTENTION_CROSSWALK` in `atlas/source.py` is an explicit, manually reviewed
mapping between those public abbreviations and names in the index report.
**It is not an OPM-published harmonization table**; no single official
crosswalk was located. No fuzzy matching is used, and a mapped name must
also exist in the 2024 index cohort to be retained.

Governmentwide, size-tier, and Defense-parent rollups are excluded. Army,
Navy, Marine Corps, USACE, and the Defense 4th Estate are deliberately not
linked: item-report exclusions or naming/scope differences would need
separate reconciliation. The Air Force's direct matching label is retained.
The project publishes the source abbreviation alongside each linked
aggregate so the join can be inspected. This conservative supplement
covers a subset of the main agency cohort, not all reporting organizations.

## Reuse

These publications are US federal government works. Such works are not subject
to US copyright under [17 USC §105](https://www.law.cornell.edu/uscode/text/17/105).
OPM is credited as the data publisher. Public-domain source statistics and
original MIT-licensed project code have distinct provenance.

This project does not redistribute third-party photographs, logos, survey
microdata, or privately supplied HR records. No real individual is identified,
scored, or represented as a modeled employee.

## Why not the familiar synthetic attrition dataset?

The project deliberately does **not** use the IBM synthetic HR attrition dataset.
The requirement is real, public, non-personal HR evidence. Organization-level
FEVS statistics satisfy that boundary while preserving an actual engagement
measurement focus.
