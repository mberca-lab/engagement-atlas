"""Publish the verified atlas and its prepared profile link using the signed-in gh account."""

import base64
import json
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "mberca/engagement-atlas"
URL = "https://mberca.github.io/engagement-atlas/"
TRAILERS = (
    "\n\nCo-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
    "\nCopilot-Session: 39116952-ee4a-435b-b203-6270df3fdd43"
)


def run(arguments, cwd=ROOT, check=True):
    result = subprocess.run(
        [str(value) for value in arguments],
        cwd=cwd,
        text=True,
        capture_output=True,
        encoding="utf-8",
        timeout=120,
    )
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result


def git(arguments, cwd=ROOT, check=True):
    return run(["git", *arguments], cwd=cwd, check=check)


def commit_owned_files(paths, message, cwd=ROOT):
    staged = git(["diff", "--cached", "--name-only"], cwd).stdout.strip()
    if staged:
        raise RuntimeError("Existing staged changes found; publication will not commit them.")
    git(["add", "--", *paths], cwd)
    if git(["diff", "--cached", "--quiet"], cwd, check=False).returncode:
        git(["commit", "-m", message + TRAILERS], cwd)


def main():
    account = json.loads(run(["gh", "api", "user"]).stdout)
    if account["login"] != "mberca":
        raise RuntimeError("Publication requires the signed-in mberca GitHub account.")
    for check in ["check_site.py", "check_browser.py"]:
        run([sys.executable, ROOT / "scripts" / check])
    identity = f"{account['id']}+mberca@users.noreply.github.com"
    git(["config", "user.name", "mberca"])
    git(["config", "user.email", identity])
    commit_owned_files(
        [
            ".github",
            ".gitignore",
            "LICENSE",
            "README.md",
            "DATA_SOURCES.md",
            "METHODOLOGY.md",
            "atlas",
            str(Path("data") / "processed"),
            "docs",
            "notebooks",
            "outputs",
            "pyproject.toml",
            "requirements.txt",
            "requirements-lock.txt",
            "scripts",
            "tests",
        ],
        "Create the Engagement Atlas from real public HR survey aggregates",
    )
    existing = run(["gh", "repo", "view", REPOSITORY, "--json", "nameWithOwner"], check=False)
    if existing.returncode:
        run(
            [
                "gh",
                "repo",
                "create",
                REPOSITORY,
                "--public",
                "--description",
                "Real public HR survey data, thoughtful machine learning, and an interactive engagement atlas.",
                "--source",
                ROOT,
                "--remote",
                "origin",
            ]
        )
    elif git(["remote", "get-url", "origin"], check=False).returncode:
        git(["remote", "add", "origin", f"https://github.com/{REPOSITORY}.git"])
    remote = git(["remote", "get-url", "origin"]).stdout.strip()
    if remote not in {f"https://github.com/{REPOSITORY}.git", f"git@github.com:{REPOSITORY}.git"}:
        raise RuntimeError("Unexpected project remote; refusing to publish.")
    git(["push", "-u", "origin", "main"])
    run(
        [
            "gh",
            "repo",
            "edit",
            REPOSITORY,
            "--homepage",
            URL,
            "--add-topic",
            "people-analytics",
            "--add-topic",
            "employee-engagement",
            "--add-topic",
            "machine-learning",
            "--add-topic",
            "data-storytelling",
            "--add-topic",
            "public-data",
        ]
    )
    pages = run(["gh", "api", f"repos/{REPOSITORY}/pages"], check=False)
    method = "PUT" if pages.returncode == 0 else "POST"
    run(
        [
            "gh",
            "api",
            "--method",
            method,
            f"repos/{REPOSITORY}/pages",
            "-f",
            "source[branch]=main",
            "-f",
            "source[path]=/docs",
        ]
    )
    deployed = False
    expected_rows = json.loads((ROOT / "outputs" / "atlas.json").read_text(encoding="utf-8"))[
        "meta"
    ]["rowCount"]
    for _ in range(18):
        try:
            response = requests.get(URL, timeout=20)
            deployed = (
                response.status_code == 200
                and "The Engagement Atlas" in response.text
                and "__ATLAS_DATA__" not in response.text
                and f'"rowCount": {expected_rows}' in response.text
            )
        except requests.RequestException:
            deployed = False
        if deployed:
            break
        time.sleep(15)
    if not deployed:
        raise RuntimeError("Repository pushed; Pages is not yet verified. Profile was not pushed.")
    run([sys.executable, ROOT / "scripts" / "check_site.py", "--url", URL])
    profile = ROOT.parent / "mberca"
    if not profile.is_dir():
        raise RuntimeError("Site is live, but the prepared profile repository is not available.")
    profile_remote = git(["remote", "get-url", "origin"], profile).stdout.strip()
    if profile_remote != "https://github.com/mberca/mberca.git":
        raise RuntimeError("Unexpected profile remote; refusing to publish.")
    content = (profile / "README.md").read_text(encoding="utf-8")
    if URL not in content or "## Projects" not in content:
        raise RuntimeError("Prepared profile Projects section was not found.")
    git(["config", "user.name", "mberca"], profile)
    git(["config", "user.email", identity], profile)
    commit_owned_files(["README.md"], "Feature the real-data Engagement Atlas in Projects", profile)
    git(["push", "origin", "main"], profile)
    published = run(["gh", "api", "repos/mberca/mberca/readme", "--jq", ".content"]).stdout
    assert URL in base64.b64decode(published).decode("utf-8")
    print(f"VERIFIED: {URL} and https://github.com/mberca#projects")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"Publication incomplete: {error}", file=sys.stderr)
        sys.exit(1)
