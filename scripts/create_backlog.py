"""Create the product backlog on GitHub from docs/backlog.json.

What it does (safe to run again: nothing is created twice):
  1. Creates or updates the labels: user-story, priority:*, module:*.
  2. Creates the milestones D1, D2 and D3 if they are missing.
  3. Creates one issue per user story (skips stories whose issue already exists).
  4. Closes the stories that are already done, with a comment pointing to the evidence.
  5. Writes the issue numbers into the backlog table of docs/requirements.md.

Needs the GitHub CLI (gh), logged in, with write access to the repository.

Usage (from the repository root):
    python scripts/create_backlog.py --dry-run     # show what would happen
    python scripts/create_backlog.py               # do it
    python scripts/create_backlog.py --table-only  # only rewrite the table in requirements.md
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "docs" / "backlog.json"
REQUIREMENTS = ROOT / "docs" / "requirements.md"
TABLE_START = "<!-- BACKLOG-TABLE:START -->"
TABLE_END = "<!-- BACKLOG-TABLE:END -->"
PAUSE = 1.0  # seconds between calls that create something (GitHub limits fast creation)

PRIORITY_COLORS = {"Must": "b60205", "Should": "fbca04", "Could": "0e8a16"}
MODULE_COLORS = "1d76db"
MILESTONES = {
    "D1": "Deliverable 1 (end of week 3): foundations, authentication, availability",
    "D2": "Deliverable 2 (week 6): booking and payment, clinical, exercises, chatbot",
    "D3": "Deliverable 3 (week 8): front-desk offline mode, admin, Law 25, polish",
}
STATUS_TEXT = {"done": "Done", "partial": "In progress", "open": "To do"}


def gh(*args: str, dry: bool = False, soft: bool = False) -> str:
    """Run a gh command and return its output. In dry-run mode, only print it."""
    if dry:
        print("  [dry-run] gh", " ".join(a if " " not in a else f'"{a}"' for a in args[:6]), "...")
        return ""
    # Full path to gh, arguments as a list, no shell: nothing is interpreted by a shell.
    result = subprocess.run(  # noqa: S603  # nosec B603
        [shutil.which("gh") or "gh", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        if soft:
            return ""
        sys.exit(f"gh {' '.join(args[:3])} failed:\n{result.stderr.strip()}")
    return result.stdout


def issue_title(story: dict) -> str:
    return f"[{story['id']}] {story['title']}"


def issue_body(story: dict) -> str:
    def ticked(item: str) -> bool:
        if story["status"] == "done":
            return True
        return story["status"] == "partial" and "(done" in item

    lines = [
        f"**As a** {story['actor']}, **I want** {story['want']}, **so that** {story['so_that']}.",
        "",
        "### Acceptance criteria",
        *[f"- [{'x' if ticked(a) else ' '}] {a}" for a in story["acceptance"]],
        "",
        "| Priority | Module | Deliverable | Spec requirement |",
        "|---|---|---|---|",
        f"| {story['priority']} | {story['module']} | {story['deliverable']} "
        f"| {story['requirement']} |",
    ]
    if story.get("evidence"):
        lines += ["", f"**Evidence:** `{story['evidence']}`"]
    lines += ["", "_Created from `docs/backlog.json` by `scripts/create_backlog.py`._"]
    return "\n".join(lines)


def labels_for(story: dict) -> list[str]:
    return ["user-story", f"priority:{story['priority']}", f"module:{story['module']}"]


def ensure_labels(repo: str, stories: list[dict], dry: bool) -> None:
    print("1. Labels")
    wanted = {"user-story": ("5319e7", "A user story of the product backlog")}
    for prio, color in PRIORITY_COLORS.items():
        wanted[f"priority:{prio}"] = (color, f"MoSCoW priority: {prio} have")
    for module in sorted({s["module"] for s in stories}):
        wanted[f"module:{module}"] = (MODULE_COLORS, f"Module: {module}")
    for name, (color, description) in wanted.items():
        gh(
            "label",
            "create",
            name,
            "--color",
            color,
            "--description",
            description,
            "--force",
            "--repo",
            repo,
            dry=dry,
        )
    print(f"   {len(wanted)} labels ready")


def ensure_milestones(repo: str, dry: bool) -> None:
    print("2. Milestones")
    existing = set()
    if not dry:
        out = gh("api", f"repos/{repo}/milestones?state=all&per_page=100")
        existing = {m["title"] for m in json.loads(out or "[]")}
    for title, description in MILESTONES.items():
        if title in existing:
            print(f"   {title} already exists")
            continue
        gh(
            "api",
            f"repos/{repo}/milestones",
            "--method",
            "POST",
            "-f",
            f"title={title}",
            "-f",
            f"description={description}",
            dry=dry,
        )
        print(f"   {title} created")
        if not dry:
            time.sleep(PAUSE)


def existing_issues(repo: str, dry: bool, soft: bool = False) -> dict[str, dict]:
    """Map story id -> {number, state} for issues that already exist."""
    if dry:
        return {}
    out = gh(
        "issue",
        "list",
        "--repo",
        repo,
        "--state",
        "all",
        "--limit",
        "1000",
        "--json",
        "number,title,state",
        soft=soft,
    )
    found = {}
    for issue in json.loads(out or "[]"):
        match = re.match(r"\[(US-[A-Z]+-\d+[a-z]?)\]", issue["title"])
        if match:
            found[match.group(1)] = {"number": issue["number"], "state": issue["state"]}
    return found


def create_issues(repo: str, stories: list[dict], dry: bool) -> dict[str, int]:
    print("3. Issues")
    found = existing_issues(repo, dry)
    numbers: dict[str, int] = {}
    created = skipped = 0
    for story in stories:
        sid = story["id"]
        if sid in found:
            numbers[sid] = found[sid]["number"]
            skipped += 1
            continue
        args = [
            "issue",
            "create",
            "--repo",
            repo,
            "--title",
            issue_title(story),
            "--body",
            issue_body(story),
            "--milestone",
            story["deliverable"],
        ]
        for label in labels_for(story):
            args += ["--label", label]
        out = gh(*args, dry=dry)
        match = re.search(r"/issues/(\d+)", out)
        if match:
            numbers[sid] = int(match.group(1))
            found[sid] = {"number": numbers[sid], "state": "OPEN"}
            print(f"   #{numbers[sid]} {issue_title(story)}")
        created += 1
        if not dry:
            time.sleep(PAUSE)
    print(f"   {created} created, {skipped} already existed")
    close_done(repo, stories, found, dry)
    return numbers


def close_done(repo: str, stories: list[dict], found: dict[str, dict], dry: bool) -> None:
    print("4. Close the stories that are done")
    closed = 0
    for story in stories:
        info = found.get(story["id"])
        if story["status"] != "done" or (info and info["state"] != "OPEN"):
            continue
        number = str(info["number"]) if info else "<new>"
        comment = (
            f"Done in {story['deliverable']}. All acceptance criteria are met.\n\n"
            f"Evidence (automated tests run by CI): `{story.get('evidence') or 'see the PR'}`"
        )
        gh(
            "issue",
            "close",
            number,
            "--repo",
            repo,
            "--reason",
            "completed",
            "--comment",
            comment,
            dry=dry,
        )
        closed += 1
        if not dry:
            time.sleep(PAUSE)
    print(f"   {closed} closed")


def write_table(stories: list[dict], numbers: dict[str, int], repo: str) -> None:
    rows = [
        "| Issue | ID | User story | Priority | Deliverable | Status |",
        "|---|---|---|---|---|---|",
    ]
    for s in stories:
        n = numbers.get(s["id"])
        link = f"[#{n}](https://github.com/{repo}/issues/{n})" if n else "—"
        rows.append(
            f"| {link} | {s['id']} | {s['title']} | {s['priority']} | {s['deliverable']} "
            f"| {STATUS_TEXT[s['status']]} |"
        )
    text = REQUIREMENTS.read_text(encoding="utf-8")
    if TABLE_START not in text or TABLE_END not in text:
        sys.exit(f"Markers {TABLE_START} / {TABLE_END} not found in {REQUIREMENTS}")
    before, rest = text.split(TABLE_START, 1)
    _, after = rest.split(TABLE_END, 1)
    new = before + TABLE_START + "\n" + "\n".join(rows) + "\n" + TABLE_END + after
    REQUIREMENTS.write_text(new, encoding="utf-8", newline="\n")
    print(f"5. Table written in {REQUIREMENTS.relative_to(ROOT)} ({len(numbers)} issue links)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="show what would happen")
    parser.add_argument(
        "--table-only",
        action="store_true",
        help="only rewrite the table (issue numbers from GitHub if available)",
    )
    args = parser.parse_args()

    data = json.loads(BACKLOG.read_text(encoding="utf-8"))
    repo, stories = data["repository"], data["stories"]

    if args.table_only:
        numbers = {}
        if shutil.which("gh"):
            numbers = {k: v["number"] for k, v in existing_issues(repo, False, soft=True).items()}
        write_table(stories, numbers, repo)
        return

    if not args.dry_run:
        if not shutil.which("gh"):
            sys.exit("The GitHub CLI (gh) is not installed or not on PATH.")
        gh("auth", "status")

    print(
        f"Repository: {repo} — {len(stories)} user stories"
        + (" (DRY RUN, nothing is changed)" if args.dry_run else "")
    )
    ensure_labels(repo, stories, args.dry_run)
    ensure_milestones(repo, args.dry_run)
    numbers = create_issues(repo, stories, args.dry_run)
    if not args.dry_run:
        write_table(stories, numbers, repo)
    print("Finished.")


if __name__ == "__main__":
    main()
