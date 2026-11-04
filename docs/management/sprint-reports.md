# Sprint reports

One-week sprints, Monday to Sunday; sprint 1 starts on 2026-10-05. The days worked and the
changes merged in each sprint are in [activity-log.md](activity-log.md), generated from Git
(numbers like #13 are pull requests). Stories refer to the
[product backlog](../requirements.md#8-product-backlog).

## Summary

| Sprint | Dates | Goal | Result |
|---|---|---|---|
| 1 | 2026-10-05 to 10-11 | Start: project chosen, repository, environment | Done; no code commits (setup) |
| 2 | 2026-10-12 to 10-18 | Development environment and accounts ready | Done; no code commits (setup) |
| 3 | 2026-10-19 to 10-25 | Repository structure, API skeleton, data model | Done; **D1 not complete at its due date** |
| 4 | 2026-10-26 to 11-01 | All D1 features in the API and the three clients | Done |
| 5 | 2026-11-02 to 11-08 | D1 documents and the last D1 story | **D1 complete on 2026-11-04** |

D1 was due at the end of sprint 3 (2026-10-25). The features were finished in sprint 4 and the
documents in sprint 5, so D1 was completed on 2026-11-04.

---

## Sprint 1 — Start (2026-10-05 to 2026-10-11)

**Goal:** choose the project and prepare to work.

**Done**

- Project B (Clinique Physio Mont-Royal) chosen; the specification (cahier des charges) read and
  its requirements listed
- Repository `stevatak/Khadizhat-Synth` created by the supervisor (2026-10-07), with write access
- Start of the development environment on Windows

**Retrospective**

| Went well | Was difficult | Action |
|---|---|---|
| Clear choice of one project, worked on alone | Large specification for one person | Rank every requirement with MoSCoW and plan by deliverable |

---

## Sprint 2 — Environment and accounts (2026-10-12 to 2026-10-18)

**Goal:** every tool installed and checked; accounts for the hosting services.

**Done**

- Installed and checked: Python 3.14, Node.js 24, .NET 8 SDK, Visual Studio, Docker Desktop with
  WSL 2, Git, the GitHub CLI
- PostgreSQL 16 runs in Docker (no local installation needed)
- Accounts: Neon (database), Render (API), Vercel (website), Expo (mobile)

**Retrospective**

| Went well | Was difficult | Action |
|---|---|---|
| Docker removed the need to install PostgreSQL itself | `dotnet` not found after installing (PATH); an older PostgreSQL installation caused confusion; WSL had no Linux distribution | Check each tool with a version command right after installing it |
| | Setup takes days and shows no commits | Record setup time in the timesheet as its own category |

---

## Sprint 3 — Structure and data model (2026-10-19 to 2026-10-25)

**Goal:** the repository structure, a running API and the data model. D1 due at the end of the sprint.

**Done** (#2 to #6)

- Monorepo structure (`api`, `web`, `desktop`, `mobile`, `docs`)
- FastAPI skeleton with a `/health` endpoint
- `.gitignore`, and generated files removed from Git
- ERD draft for D1

**Not done:** the D1 features and documents. D1 was not complete on its due date (2026-10-25).

**Retrospective**

| Went well | Was difficult | Action |
|---|---|---|
| A clean structure for four apps in one repository | Code copied from the browser kept hidden spaces and broke Python files | Receive code as files (zip), never copy and paste |
| | `__pycache__` was committed because `.gitignore` came late | Create `.gitignore` before the first commit of any new folder |
| | Two setup weeks left little time before the D1 date | Start coding earlier in D2; riskiest work first |

---

## Sprint 4 — D1 features (2026-10-26 to 2026-11-01)

**Goal:** implement every D1 story and show it in the three clients.

**Done** (#9 to #33)

- Database models and migrations, with the no-double-booking exclusion constraint and the
  30-booking concurrency test (ADR-001)
- CI for the API: lint, tests with coverage, Bandit, pip-audit
- US-AUTH-01 registration with consents and email confirmation; US-AUTH-02 login, short access
  tokens, rotated refresh tokens, logout; US-AUTH-03 Argon2id and the password policy
- US-AUTH-04 mandatory two-factor authentication for staff; US-AUTH-06 rate limiting and lockout
- US-AVL-01 to 03 services, working hours, time off and free-slot computation, with daylight saving
  changes (ADR-004)
- Demo data and a separate test database
- Deployment: API on Render, database on Neon, website on Vercel, from a deployment copy of the
  repository (ADR-006); CORS and security headers
- Website (React) with the public pages, in French and English
- Front-desk schedule endpoint and the desktop app (WPF): staff login with MFA, day schedule
  (US-FRD-01, ADR-005)
- Mobile app (Expo): patient login and upcoming appointments in Montréal time (US-BKG-07, ADR-003)

**Retrospective**

| Went well | Was difficult | Action |
|---|---|---|
| Tests written with each feature; the same API rules serve three different clients | CI failed at first because it had no secrets for the migrations | Give CI its own test-only values, never real secrets |
| The exclusion constraint made the hardest requirement simple and provable | The concurrency test exhausted the connection pool on Windows; seed data broke tests | Dedicated engine in that test; tests on their own database |
| | The repository belongs to the supervisor, so the hosting services could not see it | Deploy from a copy of the repository (ADR-006) |
| | Expo login problems (two accounts, a token pasted with quotes, an old Expo Go) | Write down which account each service uses; update apps before a demo |
| | Writing "Closes #N" before the number was known closed the wrong issue | Create the issue first and copy its number |

---

## Sprint 5 — Completing D1 (2026-11-02 to 2026-11-08)

**Goal:** close every D1 gap and start D2.

**Done** (#35 to #109)

- README, Dependabot, pull request and issue templates; command to refresh the demo appointments
- Threat model (STRIDE) and data classification (Law 25)
- Architecture (C4) and ADR-001 to 006
- Vision and requirements; 51 user stories created as GitHub issues by a script, with labels and
  the D1, D2 and D3 milestones; implemented stories closed with their test evidence
- US-AUTH-03b password reset without user enumeration (single-use, 30-minute link; all sessions
  closed after a reset); website pages for the reset and the email confirmation link
- Deadlock retry for bookings under heavy concurrency, found by CI (ADR-001 updated)
- Data dictionary generated from the code and checked by a test
- Project management: method, project board, sprint reports, activity log, timesheet, risk register

**Retrospective**

| Went well | Was difficult | Action |
|---|---|---|
| Generating documents from the code (backlog, data dictionary, activity log) keeps them true | The documents took longer than planned and delayed D1 | Plan documents as backlog items with their own time, not at the end |
| CI caught a real problem before it reached production | A test that passed many times failed once in CI (database deadlock) | Run concurrency tests several times before trusting them |

**Next:** D2 is due at the end of sprint 6 (2026-11-15). Start with the riskiest item, online
booking with the Stripe test-mode deposit (US-BKG-01 to 04), then clinical notes with audit
(US-CLN-01, 02, 04, 05). Must stories first; the D2 scope will be discussed with the supervisor.
