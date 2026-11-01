import argparse
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url")
    parser.add_argument("--screenshots", action="store_true")
    args = parser.parse_args()
    url = args.url or (ROOT / "docs" / "index.html").as_uri()
    payload = json.loads((ROOT / "outputs" / "atlas.json").read_text(encoding="utf-8"))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel="msedge" if sys.platform == "win32" else None, headless=True
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1050}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url, wait_until="load")
        page.wait_for_timeout(1000)
        body = page.inner_text("body")
        assert "ENGAGEMENT" in body.upper()
        assert str(payload["meta"]["rowCount"]) in body
        assert page.locator("svg").count() >= 5
        assert not errors, errors
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
            "Desktop overflow"
        )
        if args.screenshots:
            folder = ROOT / "docs" / "assets"
            folder.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(folder / "preview.png"))
            page.screenshot(
                path=str(ROOT / "outputs" / "figures" / "story-desktop.png"), full_page=True
            )
        initial_theme = page.locator("html").get_attribute("data-theme")
        page.locator("#theme-toggle").click()
        assert page.locator("html").get_attribute("data-theme") != initial_theme
        if args.screenshots:
            page.screenshot(path=str(ROOT / "outputs" / "figures" / "story-dark.png"))
        page.locator("#theme-toggle").click()
        before = page.locator("svg").evaluate_all("(els) => els.map(e => e.outerHTML).join('')")
        page.locator("#explorer-year").select_option("2017")
        after = page.locator("svg").evaluate_all("(els) => els.map(e => e.outerHTML).join('')")
        assert before != after, "Year selection did not update plotted observations."
        page.locator("#organization-search").fill("xyzz-no-such-organization")
        assert (
            page.get_by_text(re.compile(r"No .*match|No .*organization|No .*data", re.I)).count()
            > 0
        )
        page.locator("#explorer-reset").click()
        assert page.locator("#organization-search").input_value() == ""
        page.locator("#explorer-year").select_option("2024")
        before = page.locator("svg").evaluate_all("(els) => els.map(e => e.outerHTML).join('')")
        page.locator("#explorer-feature").select_option("intent_leave")
        after = page.locator("svg").evaluate_all("(els) => els.map(e => e.outerHTML).join('')")
        assert before != after, "Supplementary intention view did not update the chart."
        page.locator("#explorer-reset").click()
        trajectory = page.locator("#trajectory-0")
        options = trajectory.locator("option").evaluate_all("(els) => els.map(e => e.value)")
        value = next(value for value in options if value and value != trajectory.input_value())
        before = page.locator("svg").evaluate_all("(els) => els.map(e => e.outerHTML).join('')")
        trajectory.select_option(value)
        after = page.locator("svg").evaluate_all("(els) => els.map(e => e.outerHTML).join('')")
        assert before != after, "Trajectory selection did not update the chart."
        page.get_by_role("button", name="Profile 2", exact=True).click()
        page.locator("#prediction-select").select_option("Office of Personnel Management")
        assert not errors, errors
        for width, height in [(390, 844), (768, 1024)]:
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(200)
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
                f"Horizontal overflow at {width}px"
            )
            assert not errors, errors
        page.emulate_media(reduced_motion="reduce")
        page.reload(wait_until="load")
        assert page.locator("svg").count() >= 5
        if args.screenshots:
            page.set_viewport_size({"width": 390, "height": 844})
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(ROOT / "outputs" / "figures" / "story-mobile.png"))
        browser.close()
    print(
        "PASS: real-data charts, filters, empty states, trajectories, profiles, themes and mobile."
    )


if __name__ == "__main__":
    main()
