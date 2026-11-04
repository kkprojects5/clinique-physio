# Activity log

Generated from the Git history of `main` by `scripts/activity_log.py`;
do not edit by hand.
Each sprint is one week, Monday to Sunday. Each line is a change merged into `main`
(usually one pull request). Hours are recorded in [timesheet.md](timesheet.md).

| Sprint | Dates | Days with commits | Changes merged |
|---|---|---|---|
| [Sprint 1](#sprint-1) | 2026-10-05 to 2026-10-11 | 1 | 1 |
| [Sprint 3](#sprint-3) | 2026-10-19 to 2026-10-25 | 1 | 4 |
| [Sprint 4](#sprint-4) | 2026-10-26 to 2026-11-01 | 4 | 13 |
| [Sprint 5](#sprint-5) | 2026-11-02 to 2026-11-08 | 2 | 6 |

## Sprint 1

Week of 2026-10-05.

| Day | Change |
|---|---|
| Wed 2026-10-07 | Initial commit |

## Sprint 3

Week of 2026-10-19.

| Day | Change |
|---|---|
| Tue 2026-10-20 | chore: initial monorepo structure |
| Tue 2026-10-20 | feat: add FastAPI skeleton with /health endpoint (#2) |
| Tue 2026-10-20 | fix: add .gitignore and stop tracking generated files (#4) |
| Tue 2026-10-20 | docs: add ERD draft for D1 (#6) |

## Sprint 4

Week of 2026-10-26.

| Day | Change |
|---|---|
| Mon 2026-10-26 | feat: add D1 database models, migration and double-booking test (#9) |
| Mon 2026-10-26 | ci: add api-ci workflow with lint, tests, coverage and security scans (#11) |
| Mon 2026-10-26 | feat: patient registration and email verification (#13) |
| Mon 2026-10-26 | feat: add login, refresh token rotation, logout and /me (#15) |
| Mon 2026-10-26 | feat: add mandatory TOTP MFA for staff (#17) |
| Mon 2026-10-26 | feat: add rate limiting and account lockout (#19) |
| Mon 2026-10-26 | feat: add services, therapist availability and slot computation (#21) |
| Mon 2026-10-26 | feat: add demo seed data and isolated test database (#23) |
| Mon 2026-10-26 | chore: prepare API deployment (Render, CORS, security headers) (#25) |
| Tue 2026-10-27 | feat: add web app with public booking pages (#27) |
| Tue 2026-10-27 | feat: add front-desk day schedule and patient appointments endpoints (#29) |
| Wed 2026-10-28 | feat: add desktop front-desk app with MFA login and day schedule (#31) |
| Thu 2026-10-29 | feat: add mobile patient app with login and my appointments (#33) |

## Sprint 5

Week of 2026-11-02.

| Day | Change |
|---|---|
| Tue 2026-11-03 | docs: add README, Dependabot, PR and issue templates; add demo refresh (#35) |
| Tue 2026-11-03 | docs: add threat model and data classification (#51) |
| Tue 2026-11-03 | docs: add architecture document and ADRs (#53) |
| Tue 2026-11-03 | docs: add vision, requirements and product backlog (closes #54) (#106) |
| Wed 2026-11-04 | feat(auth): password reset without user enumeration (closes #58) (#107) |
| Wed 2026-11-04 | docs: add data dictionary generated from the models (closes #108) (#109) |
