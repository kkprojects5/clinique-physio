# Individual reflection — Khadizhat Khizrieva 

Capstone, Vanier College AEC Software Development (Secure Desktop, Mobile and Web Applications),
Project B: Clinique Physio Mont-Royal. **I worked alone**, without a team: I was responsible
for the requirements, design, code, tests, deployment and documents. Development repository:
`stevatak/Khadizhat-Synth` (pull requests below); deployed copy and release:
`kkprojects5/clinique-physio`.

## 1. My contributions

The system has four parts that share one API: a FastAPI API (PostgreSQL with pgvector on Neon,
hosted on Render), a React website (Vercel), a WPF desktop app for the front desk and an Expo
mobile app for patients. 33 of 33 Must stories and 9 of 14 Should stories are done (64%).

| Deliverable | What I built | Main pull requests |
|---|---|---|
| D1 — foundations | API skeleton and CI, database model with no double booking, registration, login with refresh token rotation, staff MFA, rate limiting, availability and slots, first versions of the website, desktop and mobile apps, threat model, architecture and ADRs, requirements and backlog | [#9](https://github.com/stevatak/Khadizhat-Synth/pull/9), [#11](https://github.com/stevatak/Khadizhat-Synth/pull/11), [#15](https://github.com/stevatak/Khadizhat-Synth/pull/15), [#17](https://github.com/stevatak/Khadizhat-Synth/pull/17), [#21](https://github.com/stevatak/Khadizhat-Synth/pull/21), [#27](https://github.com/stevatak/Khadizhat-Synth/pull/27), [#31](https://github.com/stevatak/Khadizhat-Synth/pull/31), [#33](https://github.com/stevatak/Khadizhat-Synth/pull/33), [#51](https://github.com/stevatak/Khadizhat-Synth/pull/51), [#53](https://github.com/stevatak/Khadizhat-Synth/pull/53), [#106](https://github.com/stevatak/Khadizhat-Synth/pull/106) |
| D2 — core features | Booking with the 24-hour rule, encrypted SOAP notes and audit log, exercise programs, Stripe deposits with signed webhooks and refunds, therapist workspace, front desk (phone booking, check-in, no-show), chatbot with OpenAI and safety rules, administration, mobile booking | [#113](https://github.com/stevatak/Khadizhat-Synth/pull/113), [#115](https://github.com/stevatak/Khadizhat-Synth/pull/115), [#117](https://github.com/stevatak/Khadizhat-Synth/pull/117), [#119](https://github.com/stevatak/Khadizhat-Synth/pull/119), [#125](https://github.com/stevatak/Khadizhat-Synth/pull/125), [#136](https://github.com/stevatak/Khadizhat-Synth/pull/136), [#143](https://github.com/stevatak/Khadizhat-Synth/pull/143), [#148](https://github.com/stevatak/Khadizhat-Synth/pull/148), [#156](https://github.com/stevatak/Khadizhat-Synth/pull/156) |
| D3 — final product | Law 25 requests and incident register, weekly reports, desk payments and insurance receipts, therapist photos, ZAP scans and security headers, security audit, privacy policy and consent management, chatbot RAG v2 evaluation, technical documentation and key rotation, release v1.0.0 with Windows installer and Android APK | [#159](https://github.com/stevatak/Khadizhat-Synth/pull/159), [#161](https://github.com/stevatak/Khadizhat-Synth/pull/161), [#162](https://github.com/stevatak/Khadizhat-Synth/pull/162), [#164](https://github.com/stevatak/Khadizhat-Synth/pull/164), [#167](https://github.com/stevatak/Khadizhat-Synth/pull/167), [#169](https://github.com/stevatak/Khadizhat-Synth/pull/169), [#170](https://github.com/stevatak/Khadizhat-Synth/pull/170), [#172](https://github.com/stevatak/Khadizhat-Synth/pull/172), [#177](https://github.com/stevatak/Khadizhat-Synth/pull/177), [#178](https://github.com/stevatak/Khadizhat-Synth/pull/178), [#180](https://github.com/stevatak/Khadizhat-Synth/pull/180) |

Every pull request went through CI (lint, tests, dependency audit) before merging. The full list
is in the repository's closed pull requests.

## 2. What went wrong and what I learned

- **The mobile app was the hardest part.** Android Studio and the emulator were very slow on my
  laptop, and with Docker and the other tools I ran out of disk space again and again. Once a
  full disk even broke Git in the middle of a commit. I learned to clean up regularly (Docker
  images, caches, `node_modules`), to test with Expo Go instead of a full native build, and
  finally to build the release APK on GitHub's servers instead of my computer.
- **The release build failed three times** for reasons that had nothing to do with my code:
  Stripe's library needs a private Google package for a feature I do not use, then the code
  shrinker stopped on the same missing classes, then my GitHub Actions minutes ran out. I read
  the build logs, fixed one cause at a time, and moved the release to the public deployment
  copy, where the minutes are free.
- **A secret appeared in a terminal output I shared.** I reset the database password at once.
  Since then, secrets live only in `.env` and in the hosts' settings, and the runbook explains
  how to rotate every key.
- **Git discipline.** I committed on `main` by mistake, forgot to commit after extracting files,
  and once merged a pull request whose CI was red. I now follow the same routine every time:
  branch, `git status`, commit, pull request, merge only when every check is green, then deploy.
- **Tests that failed only in the evening.** CI runs in UTC, so after 7 p.m. in Montréal "today"
  was already tomorrow. I fixed the tests to use the clinic's time zone.
- **Testing found my own mistakes.** The security scan showed missing headers. The adversarial
  chatbot questions passed only 12 of 24 before I improved the safety rules. The v2 evaluation
  showed that one of my fixes was too strict. Measuring before and after was more useful than
  guessing.
- **Images and licences.** I first used a copyrighted cartoon picture as a therapist avatar and
  replaced it. All data and images in the project are now fictional or my own.

## 3. Known limitations

- No email or SMS provider is connected: emails are prepared but not delivered, and there are
  no reminders.
- The desktop app needs the API; there is no offline mode.
- The installer and the APK are not signed for a store; they are installed by hand.
- The free hosting sleeps when idle (first page up to a minute) and keeps a limited database
  history.
- Five Should stories and four Could stories are out of scope for v1.0.0, each with its reason
  in the backlog.

## 4. What I am proudest of

Three working applications (web, desktop and mobile) that share one secure API, all live,
for four roles, with encrypted clinical data, Law 25 compliance and a chatbot that refuses
medical advice. I built them alone while learning most of these technologies for the first
time, coming from a career in translation and law.
