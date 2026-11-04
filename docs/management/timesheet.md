# Timesheet

Hours spent on the project. First version generated from the Git history with 8 hours per working day
(`python scripts/activity_log.py --hours-per-day N`), then corrected by hand. Days worked
without a commit (setup, learning, meetings) are added by hand.

**Categories:** Setup, Development, Testing, DevOps (CI, deployment), Documentation,
Learning, Meeting.

## Summary

| Sprint | Dates | Days | Hours |
|---|---|---|---|
| 1 | 2026-10-05 to 2026-10-11 | 1 | 8 |
| 3 | 2026-10-19 to 2026-10-25 | 1 | 8 |
| 4 | 2026-10-26 to 2026-11-01 | 4 | 32 |
| 5 | 2026-11-02 to 2026-11-08 | 2 | 16 |
| **Total** | | **8** | **64** |

## Sprint 1

| Date | Activity | Category | Hours |
|---|---|---|---|
| Wed 2026-10-07 | Initial commit | Development | 8 |
| | **Sprint 1 total** | | **8** |

## Sprint 3

| Date | Activity | Category | Hours |
|---|---|---|---|
| Tue 2026-10-20 | initial monorepo structure; add FastAPI skeleton with /health endpoint (#2); add .gitignore and stop tracking generated files (#4); add ERD draft for D1 (#6) | DevOps, Development, Documentation | 8 |
| | **Sprint 3 total** | | **8** |

## Sprint 4

| Date | Activity | Category | Hours |
|---|---|---|---|
| Mon 2026-10-26 | add D1 database models, migration and double-booking test (#9); add api-ci workflow with lint, tests, coverage and security scans (#11); patient registration and email verification (#13); add login, refresh token rotation, logout and /me (#15); add mandatory TOTP MFA for staff (#17); add rate limiting and account lockout (#19); add services, therapist availability and slot computation (#21); add demo seed data and isolated test database (#23); prepare API deployment (Render, CORS, security headers) (#25) | Development, DevOps | 8 |
| Tue 2026-10-27 | add web app with public booking pages (#27); add front-desk day schedule and patient appointments endpoints (#29) | Development | 8 |
| Wed 2026-10-28 | add desktop front-desk app with MFA login and day schedule (#31) | Development | 8 |
| Thu 2026-10-29 | add mobile patient app with login and my appointments (#33) | Development | 8 |
| | **Sprint 4 total** | | **32** |

## Sprint 5

| Date | Activity | Category | Hours |
|---|---|---|---|
| Tue 2026-11-03 | add README, Dependabot, PR and issue templates; add demo refresh (#35); add threat model and data classification (#51); add architecture document and ADRs (#53); add vision, requirements and product backlog (#106) | Documentation | 8 |
| Wed 2026-11-04 | password reset without user enumeration (#107); add data dictionary generated from the models (#109) | Development, Documentation | 8 |
| | **Sprint 5 total** | | **16** |
