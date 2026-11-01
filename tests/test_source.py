import openpyxl

from atlas.source import index_rows, number, sheet_key


def test_legacy_and_current_source_headers_and_rollups(tmp_path):
    for headers in [
        ["Size Category", "Agency", "2017", "2018"],
        ["Agency Size", "Agency Name", "percentage_2017", "percentage_2018"],
    ]:
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Overall EEI"
        sheet.append(["Published agency-level index"])
        sheet.append(headers)
        sheet.append(["", "Governmentwide", 70, 71])
        sheet.append(["Very Large", "Department of Defense, Overall", 60, 61])
        sheet.append(["Small", "Example reporting agency", 65, "--"])
        path = tmp_path / "report.xlsx"
        workbook.save(path)
        results = index_rows(path)["Overall EEI"]
        assert results.organization.tolist() == ["Example reporting agency"]
        assert results.year.tolist() == [2017]
        assert results.value.tolist() == [65]
        assert sheet_key("Overall EEI") == "engagement"


def test_percent_strings_and_suppression_preserve_missingness():
    assert number("66.2 %\xa0") == 66.2
    assert number("674,207 \xa0") == 674207
    for marker in ["N<10", "--", None, "", "*"]:
        assert number(marker) is None


def test_recommendation_not_misclassified_as_organization_satisfaction():
    assert sheet_key("Recommend Organization") == "recommendation"
    assert sheet_key("Organization Satisfaction") == "organization_satisfaction"
    assert sheet_key("Overall Global Sat") == "satisfaction"
