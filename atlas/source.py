from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://www.opm.gov/fevs/reports/data-reports/"
SOURCE_URL = "https://www.opm.gov/fevs/reports/data-reports/"
LICENSE_URL = "https://www.law.cornell.edu/uscode/text/17/105"
DOWNLOADS = {
    f"{year}-ee.xlsx": BASE
    + f"index-results-by-agency/employee-engagement-index-results-by-agency/{year}/{year}-ee-report-excel.xlsx"
    for year in [2021, 2024]
}
DOWNLOADS.update(
    {
        f"{year}-gs.xlsx": BASE
        + f"index-results-by-agency/global-satisfaction-index-results-by-agency/{year}/{year}-gs-report-excel.xlsx"
        for year in [2021, 2024]
    }
)
DOWNLOADS.update(
    {
        "2024-responses.xlsx": BASE
        + "data-reports/response-rate-by-agency/2024/2024-response-rate-by-agency-excel.xlsx",
        "2024-intentions.xlsx": BASE
        + "data-reports/report-on-demographic-questions-by-agency/2024/2024-unweighted-demographics-report-excel.xlsx",
    }
)
CORE = {
    "leaders": "Leaders lead",
    "supervisors": "Supervisory support",
    "intrinsic": "Intrinsic work experience",
    "satisfaction": "Global satisfaction",
}
INTENTION_CROSSWALK = {
    "USDA": "Department of Agriculture",
    "DHS": "Department of Homeland Security",
    "DOJ": "Department of Justice",
    "HHS": "Department of Health and Human Services",
    "USDT": "Department of the Treasury",
    "DOC": "Department of Commerce",
    "DOE": "Department of Energy",
    "DOI": "Department of the Interior",
    "DOL": "Department of Labor",
    "DOT": "Department of Transportation",
    "State": "Department of State",
    "EPA": "Environmental Protection Agency",
    "GSA": "General Services Administration",
    "SSA": "Social Security Administration",
    "CSOSA": "Court Services and Offender Supervision Agency",
    "ED": "Department of Education",
    "HUD": "Department of Housing and Urban Development",
    "EEOC": "Equal Employment Opportunity Commission",
    "FCC": "Federal Communications Commission",
    "FERC": "Federal Energy Regulatory Commission",
    "FTC": "Federal Trade Commission",
    "NARA": "National Archives and Records Administration",
    "NCUA": "National Credit Union Administration",
    "NLRB": "National Labor Relations Board",
    "NRC": "Nuclear Regulatory Commission",
    "NSF": "National Science Foundation",
    "OPM": "Office of Personnel Management",
    "SBA": "Small Business Administration",
    "USAGM": "U.S. Agency for Global Media",
    "USAID": "U.S. Agency for International Development",
    "OMB": "Office of Management and Budget",
    "PBGC": "Pension Benefit Guaranty Corporation",
    "RRB": "Railroad Retirement Board",
    "Air Force": "United States Department of the Air Force",
}


def download_sources():
    folder = ROOT / "data" / "raw"
    folder.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, url in DOWNLOADS.items():
        path = folder / name
        if not path.exists():
            response = requests.get(url, timeout=120)
            response.raise_for_status()
            if not response.content.startswith(b"PK"):
                raise ValueError(f"Expected an XLSX ZIP container: {name}")
            path.write_bytes(response.content)
        raw = path.read_bytes()
        manifest.append(
            {
                "file": name,
                "url": url,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "retrieved": datetime.now(timezone.utc).date().isoformat(),
            }
        )
    return manifest


def normalized_name(value):
    return re.sub(r"\s+", " ", str(value or "").replace("\xa0", " ")).strip()


def number(value):
    if value is None or normalized_name(value) in {"", "--", "*", "N/A", "NA"}:
        return None
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except ValueError:
        return None


def index_rows(path):
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    output = {}
    for sheet in workbook:
        rows = list(sheet.values)
        header_i = next(
            (
                i
                for i, row in enumerate(rows[:20])
                if any(normalized_name(v) in {"Agency Name", "Agency"} for v in row)
                and any(normalized_name(v) in {"Agency Size", "Size Category"} for v in row)
            ),
            None,
        )
        if header_i is None:
            continue
        headers = [normalized_name(v) for v in rows[header_i]]
        name_i = next(i for i, value in enumerate(headers) if value in {"Agency Name", "Agency"})
        size_i = next(
            i for i, value in enumerate(headers) if value in {"Agency Size", "Size Category"}
        )
        year_columns = {
            j: int(match.group(1))
            for j, value in enumerate(headers)
            if (match := re.search(r"(20\d{2})", value))
        }
        if not year_columns:
            raise ValueError(f"No year columns in {path.name}: {sheet.title}")
        records = []
        for row in rows[header_i + 1 :]:
            organization, size = normalized_name(row[name_i]), normalized_name(row[size_i])
            if (
                not size
                or not organization
                or organization.endswith(", Overall")
                or organization == "Governmentwide"
                or organization.endswith("Agencies Overall")
            ):
                continue
            for j, year in year_columns.items():
                value = number(row[j])
                if value is not None:
                    if not 0 <= value <= 100:
                        raise ValueError(
                            f"Index out of bounds: {organization}/{year}/{sheet.title}"
                        )
                    records.append(
                        {
                            "organization": organization,
                            "agency_size": size,
                            "year": year,
                            "value": value,
                        }
                    )
        output[sheet.title] = pd.DataFrame(records)
    workbook.close()
    return output


def sheet_key(title):
    title = title.lower()
    if "leader" in title:
        return "leaders"
    if "supervis" in title:
        return "supervisors"
    if "intrinsic" in title:
        return "intrinsic"
    if title.strip() in {"eei", "overall eei", "employee engagement index"}:
        return "engagement"
    if "pay" in title:
        return "pay_satisfaction"
    if "job" in title:
        return "job_satisfaction"
    if "recommend" in title:
        return "recommendation"
    if "organization" in title or "organisation" in title:
        return "organization_satisfaction"
    if "global" in title or title.strip() in {"gsi", "gs"}:
        return "satisfaction"
    return None


def response_rows(path):
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    records = []
    for sheet in workbook:
        rows = list(sheet.values)
        header_i = next(
            (
                i
                for i, row in enumerate(rows[:20])
                if "Responded" in [normalized_name(v) for v in row]
            ),
            None,
        )
        if header_i is None:
            continue
        headers = [normalized_name(v) for v in rows[header_i]]
        org_i = next(i for i, h in enumerate(headers) if h in {"Agency", "Agency Name"})
        response_i, rate_i = headers.index("Responded"), headers.index("Percentage")
        surveyed_i = headers.index("Surveyed")
        for row in rows[header_i + 1 :]:
            name = normalized_name(row[org_i])
            if name and number(row[response_i]) is not None:
                records.append(
                    {
                        "organization": name,
                        "year": 2024,
                        "response_count": number(row[response_i]),
                        "response_rate": number(row[rate_i]),
                        "surveyed": number(row[surveyed_i]),
                    }
                )
    workbook.close()
    return pd.DataFrame(records).drop_duplicates(["organization", "year"])


def intention_rows(path):
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    records = []
    for sheet in workbook:
        rows = list(sheet.values)
        header_i = next(
            (
                i
                for i, row in enumerate(rows[:20])
                if any(
                    normalized_name(v).lower().startswith("yes")
                    and "retire" in normalized_name(v).lower()
                    for v in row
                )
            ),
            None,
        )
        if header_i is None:
            continue
        headers = [normalized_name(v) for v in rows[header_i]]
        org_i = next((i for i, h in enumerate(headers) if h in {"Agency", "Agency Name"}), 0)
        no_i = next((i for i, h in enumerate(headers) if h.lower() == "no"), None)
        yes_columns = [i for i, h in enumerate(headers) if h.lower().startswith("yes")]
        if no_i is None or len(yes_columns) != 4:
            continue
        for row in rows[header_i + 1 :]:
            name = normalized_name(row[org_i])
            values = [number(row[i]) for i in yes_columns]
            no_value = number(row[no_i])
            if name and no_value is not None and all(v is not None for v in values):
                total = sum(values)
                if abs(total + no_value - 100) > 2:
                    raise ValueError(f"Intention percentages do not sum to 100: {name}")
                records.append(
                    {
                        "organization": name,
                        "year": 2024,
                        "intent_leave": total,
                        "intent_retire": values[0],
                        "intent_external": values[2],
                        "intent_response_count": number(row[1]),
                    }
                )
    workbook.close()
    return pd.DataFrame(records).drop_duplicates(["organization", "year"])


def ingest():
    manifest = download_sources()
    frames = {}
    source_sheets = {}
    for edition in [2021, 2024]:
        for family in ["ee", "gs"]:
            for title, table in index_rows(
                ROOT / "data" / "raw" / f"{edition}-{family}.xlsx"
            ).items():
                key = sheet_key(title)
                source_sheets[f"{edition}-{family}:{title}"] = key
                if key is None:
                    continue
                table = table.rename(columns={"value": key})
                frames.setdefault(key, []).append(table)
    if not {"engagement", *CORE}.issubset(frames):
        raise ValueError(f"Required index sheets not found: {source_sheets}")
    measures = {}
    for key, parts in frames.items():
        merged = pd.concat(parts).drop_duplicates(["organization", "year"], keep="last")
        measures[key] = merged
    frame = measures.pop("engagement")
    for key, table in measures.items():
        frame = frame.merge(
            table[["organization", "year", key]],
            on=["organization", "year"],
            how="left",
            validate="one_to_one",
        )
    frame = frame.merge(
        response_rows(ROOT / "data" / "raw" / "2024-responses.xlsx"),
        on=["organization", "year"],
        how="left",
        validate="one_to_one",
    )
    intentions = intention_rows(ROOT / "data" / "raw" / "2024-intentions.xlsx")
    if intentions.empty:
        raise ValueError("Turnover-intention aggregate table was not found.")
    intentions["intent_source_code"] = intentions["organization"]
    intentions["organization"] = intentions["organization"].map(INTENTION_CROSSWALK)
    intentions = intentions.dropna(subset=["organization"])
    valid_names = set(frame.loc[frame.year == 2024, "organization"])
    intentions = intentions[intentions.organization.isin(valid_names)]
    if len(intentions) < 25:
        raise ValueError("Too few explicitly crosswalked intention-to-leave reporting agencies.")
    frame = frame.merge(intentions, on=["organization", "year"], how="left", validate="one_to_one")
    frame = frame.sort_values(["year", "organization"]).reset_index(drop=True)
    features = dict(CORE)
    additional = {
        "pay_satisfaction": "Pay satisfaction",
        "job_satisfaction": "Job satisfaction",
        "organization_satisfaction": "Organization satisfaction",
        "recommendation": "Recommendation",
    }
    for key, label in additional.items():
        if key in frame and frame[key].notna().mean() >= 0.85:
            features[key] = label
    return frame, features, manifest, source_sheets
