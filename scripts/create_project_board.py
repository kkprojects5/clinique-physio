"""Create the GitHub project board and fill it with the backlog issues.

What it does (safe to run again):
  1. Finds your project "Clinique Physio Mont-Royal", or creates it.
  2. Adds every issue of the repository that is not on the board yet.
  3. Sets the Status column: Done (closed issues), In Progress (stories partly done
     in docs/backlog.json), Todo (everything else). Statuses you changed by hand on
     the board are kept, except that closed issues always move to Done.

Needs the GitHub CLI with the "project" permission (once):
    gh auth refresh -s project

Usage (from the repository root):
    python scripts/create_project_board.py
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "docs" / "backlog.json"
TITLE = "Clinique Physio Mont-Royal"
OWNER = "@me"  # the project belongs to your account and can hold the repository's issues
PAUSE = 0.5


def gh(*args: str) -> str:
    result = subprocess.run(  # noqa: S603  # nosec B603  (fixed program, no shell)
        [shutil.which("gh") or "gh", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip()
        if "project" in message and ("scope" in message or "permission" in message.lower()):
            message += "\n\nRun this once, then try again:  gh auth refresh -s project"
        sys.exit(f"gh {' '.join(args[:3])} failed:\n{message}")
    return result.stdout


def gh_json(*args: str) -> dict | list:
    return json.loads(gh(*args) or "{}")


def find_or_create_project() -> tuple[int, str, str]:
    projects = gh_json("project", "list", "--owner", OWNER, "--format", "json", "--limit", "100")
    for project in projects.get("projects", []):
        if project["title"] == TITLE:
            print(f"1. Project found: {project['url']}")
            return project["number"], project["id"], project["url"]
    project = gh_json("project", "create", "--owner", OWNER, "--title", TITLE, "--format", "json")
    print(f"1. Project created: {project['url']}")
    return project["number"], project["id"], project["url"]


def status_field(number: int) -> tuple[str, dict[str, str]]:
    fields = gh_json("project", "field-list", str(number), "--owner", OWNER, "--format", "json")
    for field in fields.get("fields", []):
        if field["name"] == "Status":
            return field["id"], {o["name"]: o["id"] for o in field.get("options", [])}
    sys.exit("The project has no Status field.")


def partial_story_ids() -> set[str]:
    stories = json.loads(BACKLOG.read_text(encoding="utf-8"))["stories"]
    return {s["id"] for s in stories if s["status"] == "partial"}


def wanted_status(issue: dict, partial: set[str]) -> str:
    if issue["state"] == "CLOSED":
        return "Done"
    match = re.match(r"\[(US-[A-Z]+-\d+[a-z]?)\]", issue["title"])
    return "In Progress" if match and match.group(1) in partial else "Todo"


def main() -> None:
    if not shutil.which("gh"):
        sys.exit("The GitHub CLI (gh) is not installed or not on PATH.")
    repo = json.loads(BACKLOG.read_text(encoding="utf-8"))["repository"]

    number, project_id, url = find_or_create_project()
    field_id, options = status_field(number)

    items = gh_json(
        "project", "item-list", str(number), "--owner", OWNER, "--format", "json", "--limit", "1000"
    )
    on_board = {}
    for item in items.get("items", []):
        content = item.get("content") or {}
        if content.get("repository", "").lower() == repo.lower() and "number" in content:
            on_board[content["number"]] = {"id": item["id"], "status": item.get("status")}

    issues = gh_json(
        "issue",
        "list",
        "--repo",
        repo,
        "--state",
        "all",
        "--limit",
        "1000",
        "--json",
        "number,title,state,url",
    )
    partial = partial_story_ids()
    added = updated = 0
    print(f"2. {len(issues)} issues in {repo}, {len(on_board)} already on the board")
    for issue in sorted(issues, key=lambda i: i["number"]):
        status = wanted_status(issue, partial)
        item = on_board.get(issue["number"])
        if item is None:
            new = gh_json(
                "project",
                "item-add",
                str(number),
                "--owner",
                OWNER,
                "--url",
                issue["url"],
                "--format",
                "json",
            )
            item = {"id": new["id"], "status": None}
            added += 1
            time.sleep(PAUSE)
        keep_manual = item["status"] and status != "Done"
        if item["status"] == status or keep_manual:
            continue
        gh(
            "project",
            "item-edit",
            "--id",
            item["id"],
            "--project-id",
            project_id,
            "--field-id",
            field_id,
            "--single-select-option-id",
            options[status],
        )
        updated += 1
        time.sleep(PAUSE)
    print(f"3. {added} issues added, {updated} statuses set")
    print(f"Finished. Open the board: {url}")


if __name__ == "__main__":
    main()
