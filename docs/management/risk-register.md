# Risk register

Reviewed at the end of each sprint. Security risks of the system itself are in the
[threat model](../threat-model.md); this register covers risks to the **project**.

**Scale:** probability and impact from 1 (low) to 3 (high). Score = probability × impact:
1–2 low, 3–4 medium, 6–9 high.

| ID | Risk | Category | P | I | Score | Mitigation | Early warning sign | Status |
|---|---|---|---|---|---|---|---|---|
| PR-01 | One developer for the whole project: not enough time to finish D2 and D3 | Schedule | 3 | 3 | **9** | MoSCoW: Must stories first, Could stories dropped first; riskiest work early in each deliverable; generate documents from code to save time | A sprint ends with Must stories not done | **Occurred**: D1 due 2026-10-25, completed 2026-11-04 |
| PR-02 | Stripe payment and webhooks take longer than expected | Technical | 2 | 3 | **6** | Start D2 with it; Stripe test mode and Stripe CLI for local webhooks; idempotent webhook handling tested | Payment not working halfway to the D2 date | Open |
| PR-03 | Chatbot gives wrong, unsafe or manipulated answers | Technical, safety | 2 | 3 | **6** | Answers only from clinic documents; refusal of diagnosis and emergency handling tested; evaluation set of 20 then 40 questions; not connected to patient data | Evaluation scores below target | Open |
| PR-04 | No admin rights on the repository: no branch protection, code scanning or secret scanning | Process, security | 3 | 2 | **6** | Every change through a pull request with green CI by routine; pip-audit, npm audit, Bandit and Dependabot in CI; ask the supervisor for the settings | A commit pushed directly to `main` | Open; request to the supervisor |
| PR-05 | Free hosting limits: the API sleeps, database limits, possible outage during a demo | Infrastructure | 2 | 2 | 4 | Open the API a few minutes before a demo; full local setup as a fallback (Docker); demo data refreshed by one command | Slow first request; Neon usage warning | Open |
| PR-06 | Mobile tooling changes (Expo SDK, Expo Go version, account access) | Technical | 2 | 2 | 4 | SDK pinned; Dependabot ignores major Expo updates; Expo Go updated before demos; APK as a fallback | Expo Go refuses the project | Open; occurred once in sprint 3 |
| PR-07 | Secret or real personal data committed to the repository | Security, legal | 1 | 3 | 3 | `.env` ignored by Git; secrets only in host settings; fictional data only (`example.com`, 514-555 numbers); review of each pull request | A key appears in a diff | Open |
| PR-08 | No email provider: emails are not delivered in production | Technical | 3 | 1 | 3 | Flows proven by tests and demonstrated locally; provider planned with reminders (D3) | — | Accepted (threat model R-9) |
| PR-09 | Concurrency or time zone bugs found late | Quality | 1 | 3 | 3 | Database constraint, deadlock retry, concurrency and daylight saving tests in CI | A flaky test in CI | Mitigated; occurred once (deadlock), fixed in sprint 4 |
| PR-10 | Vulnerable or unsupported dependencies (.NET 8 end of support in November 2026) | Maintenance | 2 | 1 | 2 | Dependabot weekly; audits in CI; .NET 8 required by the spec | Audit failure in CI | Open (threat model R-8) |
| PR-11 | Scope of D3 too large (offline mode, administration, Law 25 tools) | Scope | 2 | 2 | 4 | Should and Could stories ranked; offline mode limited to the read-only schedule and queued check-ins | D3 backlog larger than the time left after D2 | Open |

## Changes

| Date | Change |
|---|---|
| 2026-11-04 | Register created; PR-01 occurred (D1 completed 2026-11-04 instead of 2026-10-25); PR-09 occurred and was fixed |
