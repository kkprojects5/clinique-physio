"""Write docs/management/activity-log.md from the Git history of main.

For each sprint (one week, Monday to Sunday) it lists the days worked and the changes merged,
taken from the commits. It gives the facts for the sprint reports and the timesheet; the hours
are added by hand in timesheet.md.

With --hours-per-day, it also writes docs/management/timesheet.md: one row per day with
commits, that day's changes, a category taken from the commit type, and the hours given.
Generate it once, then correct it by hand (it overwrites the file).

Usage (from the repository root):
    python scripts/activity_log.py                     # sprint 1 = week of the first commit
    python scripts/activity_log.py --start 2026-10-12  # or give the first Monday yourself
    python scripts/activity_log.py --hours-per-day 8   # also write the timesheet
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "management" / "activity-log.md"
TIMESHEET = ROOT / "docs" / "management" / "timesheet.md"
CATEGORIES = {
    "feat": "Development",
    "fix": "Development",
    "refactor": "Development",
    "test": "Testing",
    "docs": "Documentation",
    "ci": "DevOps",
    "build": "DevOps",
    "chore": "DevOps",
}
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def commits(branch: str) -> list[tuple[date, str]]:
    """(day, subject) of every commit on the branch, oldest first, in local time."""
    git = shutil.which("git") or "git"
    result = subprocess.run(  # noqa: S603  # nosec B603  (fixed arguments, no shell)
        [git, "log", branch, "--reverse", "--date=short", "--pretty=format:%ad|%s"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        sys.exit(f"git log failed:\n{result.stderr.strip()}")
    found = []
    for line in result.stdout.splitlines():
        day, _, subject = line.partition("|")
        found.append((date.fromisoformat(day), subject.strip()))
    return found


def monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def render(history: list[tuple[date, str]], start: date) -> str:
    by_sprint: dict[int, list[tuple[date, str]]] = defaultdict(list)
    for day, subject in history:
        if day >= start:
            by_sprint[(day - start).days // 7 + 1].append((day, subject))

    lines = [
        "# Activity log",
        "",
        "Generated from the Git history of `main` by `scripts/activity_log.py`;",
        "do not edit by hand.",
        "Each sprint is one week, Monday to Sunday. Each line is a change merged into `main`",
        "(usually one pull request). Hours are recorded in [timesheet.md](timesheet.md).",
        "",
        "| Sprint | Dates | Days with commits | Changes merged |",
        "|---|---|---|---|",
    ]
    for n in sorted(by_sprint):
        first = start + timedelta(days=7 * (n - 1))
        last = first + timedelta(days=6)
        days = {d for d, _ in by_sprint[n]}
        lines.append(
            f"| [Sprint {n}](#sprint-{n}) | {first:%Y-%m-%d} to {last:%Y-%m-%d} "
            f"| {len(days)} | {len(by_sprint[n])} |"
        )
    for n in sorted(by_sprint):
        first = start + timedelta(days=7 * (n - 1))
        lines += ["", f"## Sprint {n}", "", f"Week of {first:%Y-%m-%d}.", ""]
        lines += ["| Day | Change |", "|---|---|"]
        for day, subject in by_sprint[n]:
            safe = subject.replace("|", "\\|")
            lines.append(f"| {DAY_NAMES[day.weekday()]} {day:%Y-%m-%d} | {safe} |")
    return "\n".join(lines) + "\n"


def category(subject: str) -> str:
    kind = re.match(r"^(\w+)", subject)
    return CATEGORIES.get(kind.group(1).lower(), "Development") if kind else "Development"


def short(subject: str) -> str:
    """'feat(auth): add login (closes #12) (#13)' -> 'add login (#13)'"""
    text = re.sub(r"^\w+(\([^)]*\))?!?:\s*", "", subject)
    text = re.sub(r"\s*\((closes|fixes) #\d+\)", "", text, flags=re.IGNORECASE)
    return text.replace("|", "\\|").strip()


def render_timesheet(history: list[tuple[date, str]], start: date, hours: float) -> str:
    by_day: dict[date, list[str]] = defaultdict(list)
    for day, subject in history:
        if day >= start:
            by_day[day].append(subject)
    sprints: dict[int, list[date]] = defaultdict(list)
    for day in sorted(by_day):
        sprints[(day - start).days // 7 + 1].append(day)

    def fmt(value: float) -> str:
        return f"{value:g}"

    lines = [
        "# Timesheet",
        "",
        f"Hours spent on the project. First version generated from the Git history with "
        f"{fmt(hours)} hours per working day",
        "(`python scripts/activity_log.py --hours-per-day N`), then corrected by hand. Days worked",
        "without a commit (setup, learning, meetings) are added by hand.",
        "",
        "**Categories:** Setup, Development, Testing, DevOps (CI, deployment), Documentation,",
        "Learning, Meeting.",
        "",
        "## Summary",
        "",
        "| Sprint | Dates | Days | Hours |",
        "|---|---|---|---|",
    ]
    total_days = 0
    for n, days in sprints.items():
        first = start + timedelta(days=7 * (n - 1))
        last = first + timedelta(days=6)
        sprint_hours = fmt(len(days) * hours)
        lines.append(
            f"| {n} | {first:%Y-%m-%d} to {last:%Y-%m-%d} | {len(days)} | {sprint_hours} |"
        )
        total_days += len(days)
    lines.append(f"| **Total** | | **{total_days}** | **{fmt(total_days * hours)}** |")

    for n, days in sprints.items():
        lines += [
            "",
            f"## Sprint {n}",
            "",
            "| Date | Activity | Category | Hours |",
            "|---|---|---|---|",
        ]
        for day in days:
            subjects = by_day[day]
            activity = "; ".join(short(s) for s in subjects)
            kinds = ", ".join(dict.fromkeys(category(s) for s in subjects))
            label = f"{DAY_NAMES[day.weekday()]} {day:%Y-%m-%d}"
            lines.append(f"| {label} | {activity} | {kinds} | {fmt(hours)} |")
        lines.append(f"| | **Sprint {n} total** | | **{fmt(len(days) * hours)}** |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the activity log from Git.")
    parser.add_argument("--start", type=date.fromisoformat, help="first day of sprint 1")
    parser.add_argument("--branch", default="main")
    parser.add_argument(
        "--hours-per-day", type=float, help="also write timesheet.md with these hours per day"
    )
    args = parser.parse_args()

    history = commits(args.branch)
    if not history:
        sys.exit("No commits found.")
    start = args.start or monday(history[0][0])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(history, start), encoding="utf-8", newline="\n")
    print(f"Written: {OUTPUT.relative_to(ROOT)} (sprint 1 starts {start})")
    if args.hours_per_day:
        TIMESHEET.write_text(
            render_timesheet(history, start, args.hours_per_day), encoding="utf-8", newline="\n"
        )
        print(f"Written: {TIMESHEET.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
