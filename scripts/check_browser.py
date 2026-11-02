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
        page = browser.new_page(
            viewport={"width": 1440, "height": 1050},
            device_scale_factor=1,
            reduced_motion="no-preference",
        )
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url, wait_until="load")
        page.wait_for_timeout(1000)
        body = page.inner_text("body")
        assert "ENGAGEMENT" in body.upper()
        assert str(payload["meta"]["rowCount"]) in body
        assert page.locator("svg").count() >= 5
        assert page.locator("#cohort-sensitivity").inner_text().startswith("Coverage check:")
        assert (
            "overall survey-score level alone" in page.locator("#cluster-level-check").inner_text()
        )
        assert page.locator("#paired-comparison-table tbody tr").count() == len(
            payload["models"]["pairedComparisons"]
        )
        assert "not a new winner" in page.locator("#model-insight").inner_text()
        assert "Wilson interval" in page.locator("#interval-insight").inner_text()
        assert not errors, errors
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
            "Desktop overflow"
        )
        assert page.locator("#hero-route").count() == 0, "The left-side route was removed."
        assert page.locator("#hero-art").evaluate(
            """el => {
                const animations = el.getAnimations({subtree: true});
                return animations.length > 0 && animations.every(animation => {
                    const timing = animation.effect.getComputedTiming();
                    return timing.iterations === 1 && timing.endTime <= 5000;
                });
            }"""
        ), "Decorative atlas should assemble once and finish within five seconds."
        page.wait_for_function(
            """() => {
                const hero = document.querySelector(".hero");
                return [...hero.querySelectorAll(".atlas-contour")].every(el =>
                    parseFloat(getComputedStyle(el).strokeDashoffset) === 0)
                    && hero.getAnimations({subtree: true}).every(animation =>
                        animation.playState === "finished");
            }""",
            timeout=5500,
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
        assert page.locator("#intention-audit").is_visible()
        assert "Leaving out one agency" in page.locator("#intention-context").inner_text()
        assert page.locator("#intention-size-table tbody tr").count() == len(
            payload["intentionAnalysis"]["sizeComposition"]
        )
        context = page.locator("#intention-context").inner_text()
        page.locator("#organization-search").fill("Office")
        assert page.locator("#intention-context").inner_text() == context
        page.locator("#explorer-reset").click()
        assert not page.locator("#intention-audit").is_visible()
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
        for width, height in [(320, 844), (390, 844), (768, 1024), (1440, 1050)]:
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(200)
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
                f"Horizontal overflow at {width}px"
            )
            assert page.locator("#hero-title").evaluate(
                """el => {
                    const range = document.createRange();
                    range.selectNodeContents(el);
                    const bounds = el.getBoundingClientRect();
                    return [...range.getClientRects()].every(rect =>
                        rect.left >= bounds.left - 1 && rect.right <= bounds.right + 1);
                }"""
            ), f"Title is clipped at {width}px"
            assert not errors, errors
        page.emulate_media(reduced_motion="reduce")
        page.reload(wait_until="load")
        assert page.locator("svg").count() >= 5
        assert page.locator("#hero-art").evaluate(
            "el => el.getAnimations({subtree: true}).length === 0"
        ), "Reduced-motion visitors should see a static atlas."
        assert page.locator("#hero-art .atlas-landmark").first.evaluate(
            "el => Number(getComputedStyle(el).opacity) > 0"
        ), "The static atlas should retain its landmarks."
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
