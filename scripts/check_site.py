import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url")
    args = parser.parse_args()
    if args.url:
        import requests

        response = requests.get(args.url, timeout=60)
        response.raise_for_status()
        html = response.text
    else:
        html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    assert "__ATLAS_DATA__" not in html, "Data placeholder was not replaced."
    assert "data-theme" in html and "--cp-accent:" in html, "Required themes missing."
    assert "<title>" in html and 'name="viewport"' in html, "Page metadata missing."
    assert len(html) > 30000, "Expected complete story and embedded analytical outputs."
    assert not re.search(r"<script[^>]+src=", html), "Story must run without remote scripts."
    match = re.search(r"const DATA = (.*?);\s*\(\(\) =>", html, re.DOTALL)
    assert match, "Embedded analytical evidence is missing."
    payload = json.loads(match.group(1))
    expected = json.loads((ROOT / "outputs" / "atlas.json").read_text(encoding="utf-8"))
    assert payload == expected, "Served analytical evidence differs from the verified local build."
    assert len(payload["rows"]) == payload["meta"]["rowCount"]
    assert payload["meta"]["orgCount"] > 30
    assert len(payload["models"]["metrics"]) >= 5
    assert payload["models"]["testYear"] > payload["models"]["calibrationYear"]
    assert len(payload["models"]["pairedComparisons"]) == len(payload["models"]["metrics"]) - 1
    assert payload["cohortSensitivity"]["n"] == payload["models"]["balancedOrgCount"]
    assert payload["clusters"]["levelCheck"]["n"] == len(payload["clusters"]["points"])
    first_script = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
    assert first_script and "scoutTheme" in first_script.group(1), (
        "Theme detection must precede all other JavaScript."
    )
    assert '"Segoe UI", Aptos, Calibri' in html
    for selector in [
        "living-chart",
        "atlas-level",
        "atlas-change",
        "atlas-agency",
        "living-table",
        "score-chart",
        "cluster-evidence",
        "audit-chart",
        "audit-table",
        "paired-errors",
        "paired-model",
        "paired-agency",
        "paired-error-chart",
        "paired-error-table",
    ]:
        assert f'id="{selector}"' in html, f"Missing evidence interface: {selector}"
    assert "not an employee-weighted federal estimate" in html
    assert "not independent fresh holdouts" in html
    audit = payload.get("rollingAudit", {})
    origins = audit.get("origins", [])
    for origin in origins:
        assert origin["n"] > 0
        assert abs(origin["improvement"] - (origin["baselineMae"] - origin["mae"])) < 1e-8
        assert 0 <= origin["coverage"] <= 1
        assert origin["width"] >= 0
        assert max(origin["selectionYears"]) < origin["calibrationYear"] < origin["year"]
        assert max(origin["trainingYears"]) < origin["calibrationYear"]
    if origins:
        assert audit["summary"]["nOrigins"] == len(origins)
        assert len({origin["year"] for origin in origins}) == len(origins)
    print("PASS: published story, data contract, temporal partitions and offline assets.")


if __name__ == "__main__":
    main()
