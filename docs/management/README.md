# Project management — Clinique Physio Mont-Royal

Status: **D1 (v0.1.0)**. Solo project: one developer (Claire Mancini) and one supervisor.

| Document | Content | How it is kept up to date |
|---|---|---|
| [Product backlog](../requirements.md#8-product-backlog) | 51 user stories with acceptance criteria and MoSCoW priority | GitHub Issues (label `user-story`), from `docs/backlog.json` |
| Project board | Every issue in Todo, In Progress or Done | GitHub Projects; `python scripts/create_project_board.py` |
| [sprint-reports.md](sprint-reports.md) | Goal, result and retrospective of each sprint | Written at the end of each sprint |
| [activity-log.md](activity-log.md) | Days worked and changes merged, per sprint | Generated: `python scripts/activity_log.py` |
| [timesheet.md](timesheet.md) | Hours per day and per activity | Filled in by hand each day |
| [meeting-minutes.md](meeting-minutes.md) | Meetings with the supervisor: decisions and actions | Written after each meeting |
| [../demo/d2-payments](../demo/d2-payments/README.md) | Screenshots of the live Stripe payment flow, for presentations | Added after each demo |
| [risk-register.md](risk-register.md) | Project risks, scores, mitigations | Reviewed at each sprint review |

## Method

A light Scrum adapted to one developer:

| Practice | How it is done here |
|---|---|
| Sprints | One week, Monday to Sunday, from 2026-10-05. Deliverables: D1 end of sprint 3 (2026-10-25), D2 end of sprint 6 (2026-11-15), D3 end of sprint 8 (2026-11-29) |
| Backlog | User stories in GitHub Issues, one milestone per deliverable (D1, D2, D3), labels for priority and module |
| Planning | At the start of a sprint, the stories for the sprint are moved to In Progress on the board |
| Daily work | Each change: an issue, a branch, a pull request with green CI, a squash merge |
| Review | At the end of a sprint: demo of what works, update of the board, the sprint report and the risks |
| Retrospective | What went well, what was difficult, one or two actions for the next sprint (in the sprint report) |
| Prioritization | MoSCoW: Must first; Could stories are dropped first if time is short |

### Definition of Ready (before a story is started)

- Written as "As a …, I want …, so that …", with testable acceptance criteria
- Priority, module and deliverable set (labels and milestone)
- Linked to the spec requirement (B-AUTH-01, B-BKG-02, …)

### Definition of Done (before a story is closed)

- Every acceptance criterion is met
- Automated tests prove it, including the security cases (wrong user, wrong role, bad input)
- CI is green: lint, format, tests, security checks
- Texts in French and English; accessibility rules respected
- Documentation updated when needed (API contract, data dictionary, threat model, ADR)
- Merged into `main` with a pull request that closes the issue, and deployed

### Branches and commits

`feature/<issue>-short-name`, `fix/…` or `docs/…`; commit messages follow Conventional Commits
(`feat:`, `fix:`, `docs:`, `test:`, `chore:`). The pull request template lists the checks above.
