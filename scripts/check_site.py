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
    payload = json.loads((ROOT / "outputs" / "atlas.json").read_text(encoding="utf-8"))
    assert len(payload["rows"]) == payload["meta"]["rowCount"]
    assert payload["meta"]["orgCount"] > 30
    assert len(payload["models"]["metrics"]) >= 5
    assert payload["models"]["testYear"] > payload["models"]["calibrationYear"]
    print("PASS: published story, data contract, temporal partitions and offline assets.")


if __name__ == "__main__":
    main()
