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
            color_scheme="light",
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
        years = payload["meta"]["years"]
        for chart in ["annual-chart", "living-chart", "trajectory-chart"]:
            assert page.locator(f"#{chart} .x-tick").all_text_contents() == [
                str(year) for year in sorted(years)
            ], f"{chart} should display years without numeric grouping."
        by_agency = {}
        for row in payload["rows"]:
            by_agency.setdefault(row["organization"], {})[row["year"]] = row
        complete = {
            name: observations
            for name, observations in by_agency.items()
            if all(
                year in observations and isinstance(observations[year]["engagement"], (int, float))
                for year in years
            )
        }
        assert page.locator("#living-chart .atlas-path").count() == len(complete)
        assert str(len(complete)) in page.locator("#living-heading").inner_text()
        changes = [
            observations[max(years)]["engagement"] - observations[min(years)]["engagement"]
            for observations in complete.values()
        ]
        assert page.locator("#living-metrics strong").nth(0).inner_text() == str(
            sum(change > 0 for change in changes)
        )
        assert page.locator("#living-metrics strong").nth(1).inner_text() == str(
            sum(change < 0 for change in changes)
        )
        level_paths = page.locator("#living-chart .atlas-path").evaluate_all(
            "els => els.map(el => el.getAttribute('d'))"
        )
        page.locator("#atlas-change").click()
        assert page.locator("#atlas-change").get_attribute("aria-pressed") == "true"
        change_paths = page.locator("#living-chart .atlas-path").evaluate_all(
            "els => els.map(el => el.getAttribute('d'))"
        )
        assert level_paths != change_paths, "Atlas mode must change real path coordinates."
        assert len({path.split(" ")[0] for path in change_paths}) == 1, (
            "All baseline-relative paths must share their first-year origin."
        )
        assert "Change since" in page.locator("#living-chart .axis-title").all_text_contents()[1]
        assert "median of agency changes" in page.locator("#atlas-status").inner_text()
        agency_selector = page.locator("#atlas-agency")
        agency_options = agency_selector.locator("option").evaluate_all(
            "els => els.map(el => el.value)"
        )
        agency_selector.select_option(agency_options[-1])
        assert agency_options[-1] in page.locator("#atlas-detail").inner_text()
        selected_path = page.locator("#living-chart .atlas-path[tabindex='0']")
        selected_path.focus()
        selected_path.press("Home")
        assert agency_selector.input_value() == agency_options[0]
        page.locator("#living-chart .atlas-path[tabindex='0']").press("ArrowRight")
        assert agency_selector.input_value() == agency_options[1]
        assert (
            page.locator("#living-chart .atlas-path.is-selected")
            .get_attribute("aria-label")
            .startswith(agency_options[1])
        )
        page.locator("#living-chart .atlas-path[tabindex='0']").press("Escape")
        assert not page.locator("#tooltip").is_visible()
        page.locator("#atlas-level").click()
        assert (
            page.locator("#living-chart .atlas-path").evaluate_all(
                "els => els.map(el => el.getAttribute('d'))"
            )
            == level_paths
        )
        assert page.locator("#score-chart .mark").count() == len(payload["clusters"]["points"])
        assert "partly mechanical" in page.locator("#score-note").inner_text()
        assert page.locator("#paired-model").input_value() == payload["models"]["explanationModel"]
        paired_reference = {row["organization"]: row for row in payload["models"]["predictions"]}
        paired_names = page.locator("#paired-model option").evaluate_all(
            "els => els.map(el => el.value)"
        )
        paired_extent = page.locator("#paired-error-chart").get_attribute("data-extent")

        def verify_paired_errors(name):
            page.locator("#paired-model").select_option(name)
            expected_pairs = {
                row["organization"]: row
                for row in payload["models"]["modelPredictions"]
                if row["model"] == name
            }
            dots = page.locator("#paired-error-chart .error-dot").evaluate_all(
                """els => els.map(el => ({
                    agency: el.dataset.agency, difference: Number(el.dataset.difference),
                    x: Number(el.getAttribute("cx")), y: Number(el.getAttribute("cy")),
                    r: Number(el.getAttribute("r"))
                }))"""
            )
            assert len(dots) == len(expected_pairs) == len(paired_reference)
            assert {dot["agency"] for dot in dots} == set(paired_reference)
            assert page.locator("#paired-error-chart").get_attribute("data-extent") == paired_extent
            differences = []
            for dot in dots:
                row = expected_pairs[dot["agency"]]
                reference = paired_reference[dot["agency"]]
                assert row["actual"] == reference["actual"]
                assert row["baseline"] == reference["baseline"]
                difference = abs(row["actual"] - row["baseline"]) - abs(
                    row["actual"] - row["predicted"]
                )
                differences.append(difference)
                assert abs(dot["difference"] - difference) < 1e-10
                expected_x = (
                    48 + (difference + float(paired_extent)) / (2 * float(paired_extent)) * 804
                )
                assert abs(dot["x"] - expected_x) < 1e-8
            for index, dot in enumerate(dots):
                for other in dots[index + 1 :]:
                    assert (dot["x"] - other["x"]) ** 2 + (dot["y"] - other["y"]) ** 2 >= (
                        dot["r"] + other["r"] + 2
                    ) ** 2 - 1e-5
            summary_values = page.locator("#paired-error-summary strong").all_text_contents()
            assert int(summary_values[0]) == sum(value < 0 for value in differences)
            assert int(summary_values[1]) == sum(value > 0 for value in differences)
            assert abs(float(summary_values[2]) - sum(differences) / len(differences)) <= 0.00051
            assert page.locator("#paired-error-table tbody tr").count() == len(dots)
            assert (
                payload["models"]["selected"] in page.locator("#paired-error-status").inner_text()
            )
            return {dot["agency"]: dot["x"] for dot in dots}

        original_paired_positions = verify_paired_errors(payload["models"]["explanationModel"])
        agency_names = sorted(paired_reference)
        page.locator("#paired-agency").select_option(agency_names[-1])
        assert agency_names[-1] in page.locator("#paired-error-detail").inner_text()
        moved = False
        for name in paired_names:
            positions = verify_paired_errors(name)
            moved = moved or positions != original_paired_positions
            assert page.locator("#paired-agency").input_value() == agency_names[-1]
        assert moved, "Switching models must change the actual agency error positions."
        page.locator("#paired-model").select_option(paired_names[0])
        assert page.locator("#paired-error-chart").evaluate(
            """el => {
                const animations = el.getAnimations({subtree:true});
                return animations.length > 0 && animations.every(animation =>
                    animation.effect.getComputedTiming().iterations === 1 &&
                    animation.effect.getComputedTiming().endTime <= 600);
            }"""
        ), "Paired-error transitions must be finite and brief."
        selected_error = page.locator("#paired-error-chart .error-dot[tabindex='0']")
        selected_error.focus()
        selected_error.press("Home")
        assert page.locator("#paired-agency").input_value() == agency_names[0]
        page.locator("#paired-error-chart .error-dot[tabindex='0']").press("ArrowRight")
        assert page.locator("#paired-agency").input_value() == agency_names[1]
        assert (
            page.locator("#paired-error-chart .is-selected").get_attribute("aria-pressed") == "true"
        )
        page.locator("#paired-error-chart .error-dot[tabindex='0']").press("Escape")
        assert not page.locator("#tooltip").is_visible()
        verify_paired_errors(payload["models"]["explanationModel"])
        origins = payload.get("rollingAudit", {}).get("origins", [])
        if origins:
            assert page.locator("#audit-chart .x-tick").all_text_contents() == [
                str(origin["year"]) for origin in sorted(origins, key=lambda row: row["year"])
            ], "Audit year ticks should not contain thousands separators."
            audit_rows = page.locator("#audit-table tbody tr")
            assert audit_rows.count() == len(origins)
            for index, origin in enumerate(sorted(origins, key=lambda row: row["year"])):
                cells = audit_rows.nth(index).locator("th, td").all_text_contents()
                assert cells[:3] == [
                    str(origin["year"]),
                    origin["selected"],
                    str(origin["n"]),
                ]
                for column, key in [(3, "mae"), (4, "baselineMae"), (5, "improvement")]:
                    assert abs(float(cells[column].replace(",", "")) - origin[key]) <= 0.00051
            assert page.locator("#audit-chart .mark").count() == len(origins)
            assert "not independent" in page.locator("#audit-note").inner_text()
            summary = payload["rollingAudit"]["summary"]
            if "incrementalFeatureImprovement" in summary:
                assert page.locator("#audit-ablation").is_visible()
                values = page.locator("#audit-ablation strong").all_text_contents()
                for value, key in zip(
                    values,
                    ["priorOnlyRidgeMae", "fullRidgeMae", "incrementalFeatureImprovement"],
                    strict=True,
                ):
                    assert abs(float(value.replace(" points", "")) - summary[key]) <= 0.00051
                assert "not a new selection" in page.locator("#audit-ablation").inner_text()
        else:
            assert "not available" in page.locator("#audit-summary").inner_text()
            assert page.locator("#audit-chart .mark").count() == 0
        if args.screenshots:
            folder = ROOT / "docs" / "assets"
            folder.mkdir(parents=True, exist_ok=True)
            figures = ROOT / "outputs" / "figures"
            figures.mkdir(parents=True, exist_ok=True)
            screenshot_style = ".masthead, .skip { visibility: hidden !important; }"
            page.locator(".living-atlas").screenshot(
                path=str(figures / "story-living-level.png"), style=screenshot_style
            )
            page.locator("#atlas-change").click()
            page.wait_for_timeout(650)
            page.locator(".living-atlas").screenshot(
                path=str(figures / "story-living-change.png"), style=screenshot_style
            )
            page.locator("#paired-errors").screenshot(
                path=str(figures / "story-paired-errors.png"), style=screenshot_style
            )
            page.locator("#atlas-level").click()
            page.wait_for_timeout(650)
            page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
            page.screenshot(path=str(folder / "preview.png"))
            page.screenshot(
                path=str(ROOT / "outputs" / "figures" / "story-desktop.png"), full_page=True
            )
        initial_theme = page.locator("html").get_attribute("data-theme")
        page.locator("#theme-toggle").click()
        assert page.locator("html").get_attribute("data-theme") != initial_theme
        if args.screenshots:
            page.locator(".living-atlas").screenshot(
                path=str(ROOT / "outputs" / "figures" / "story-living-dark.png"),
                style=screenshot_style,
            )
            page.locator("#paired-errors").screenshot(
                path=str(ROOT / "outputs" / "figures" / "story-paired-errors-dark.png"),
                style=screenshot_style,
            )
            page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
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
        page.locator("#cluster-evidence > summary").click()
        page.get_by_role("button", name="Profile 2", exact=True).click()
        page.locator("#prediction-select").select_option("Office of Personnel Management")
        assert not errors, errors
        for width, height in [(320, 844), (390, 844), (768, 1024), (1440, 1050)]:
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(200)
            page.locator("#paired-agency").select_option(agency_names[0])
            assert page.locator("#paired-error-chart").evaluate(
                """el => {
                    const viewport = el.getBoundingClientRect();
                    const point = el.querySelector(".is-selected").getBoundingClientRect();
                    return point.left >= viewport.left - 1 && point.right <= viewport.right + 1;
                }"""
            ), f"The selected agency must remain visible at {width}px."
            for theme in ["light", "dark"]:
                page.evaluate("theme => document.documentElement.dataset.theme = theme", theme)
                assert page.locator("#living-chart").evaluate(
                    """el => {
                        const selected = getComputedStyle(el.querySelector(".is-selected"));
                        const background = getComputedStyle(
                            el.querySelector(".atlas-path:not(.is-selected)"));
                        return Number(background.opacity) > 0
                            && Number(selected.opacity) > Number(background.opacity)
                            && selected.stroke !== background.stroke;
                    }"""
                ), f"The selected rose path must remain distinct in {theme}."
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
                    f"Horizontal overflow at {width}px in {theme}"
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
        page.locator("#atlas-change").click()
        assert page.locator("#living-chart").get_attribute("data-mode") == "change"
        assert page.locator("#living-chart").evaluate(
            "el => el.getAnimations({subtree:true}).length === 0"
        ), "Reduced motion should not animate the data transformation."
        page.locator("#paired-model").select_option(paired_names[0])
        assert page.locator("#paired-error-chart .error-dot").count() == len(paired_reference)
        assert page.locator("#paired-error-chart").evaluate(
            "el => el.getAnimations({subtree:true}).length === 0"
        ), "Reduced motion should show the new model without animating dots."
        for theme in ["light", "dark"]:
            separator = "&" if "?" in url else "?"
            page.goto(f"{url}{separator}scoutTheme={theme}", wait_until="load")
            assert page.locator("html").get_attribute("data-theme") == theme
        if args.screenshots:
            page.set_viewport_size({"width": 390, "height": 844})
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(ROOT / "outputs" / "figures" / "story-mobile.png"))
        html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        without_audit = dict(payload)
        without_audit.pop("rollingAudit", None)
        missing_html = re.sub(
            r"const DATA = .*?;\s*(?=\(\(\) =>)",
            lambda _: f"const DATA = {json.dumps(without_audit)};\n",
            html,
            count=1,
            flags=re.DOTALL,
        )
        page.goto("about:blank")
        page.set_content(missing_html, wait_until="load")
        assert "not available" in page.locator("#audit-summary").inner_text()
        assert page.locator("#audit-chart .mark").count() == 0
        assert "No audit origins supplied" in page.locator("#audit-table").text_content()
        assert not errors, errors
        incomplete_pairs = json.loads(json.dumps(payload))
        default_model = payload["models"]["explanationModel"]
        first_pair = next(
            row
            for row in incomplete_pairs["models"]["modelPredictions"]
            if row["model"] == default_model
        )
        incomplete_pairs["models"]["modelPredictions"].remove(first_pair)
        incomplete_html = re.sub(
            r"const DATA = .*?;\s*(?=\(\(\) =>)",
            lambda _: f"const DATA = {json.dumps(incomplete_pairs)};\n",
            html,
            count=1,
            flags=re.DOTALL,
        )
        page.goto("about:blank")
        page.set_content(incomplete_html, wait_until="load")
        assert default_model not in page.locator("#paired-model option").evaluate_all(
            "els => els.map(el => el.value)"
        ), "An incomplete model must not silently change the comparison cohort."
        assert page.locator("#paired-error-chart .error-dot").count() == len(paired_reference)
        incomplete_pairs["models"].pop("modelPredictions")
        missing_pairs_html = re.sub(
            r"const DATA = .*?;\s*(?=\(\(\) =>)",
            lambda _: f"const DATA = {json.dumps(incomplete_pairs)};\n",
            html,
            count=1,
            flags=re.DOTALL,
        )
        page.goto("about:blank")
        page.set_content(missing_pairs_html, wait_until="load")
        assert page.locator("#paired-model").is_disabled()
        assert page.locator("#paired-error-chart .error-dot").count() == 0
        assert "not available" in page.locator("#paired-error-chart").inner_text()
        assert not errors, errors
        browser.close()
    print("PASS: paired agency errors, living paths, temporal audit, keyboard, themes and mobile.")


if __name__ == "__main__":
    main()
