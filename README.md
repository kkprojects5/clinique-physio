# Clinique Physio Mont-Royal

Secure booking and patient portal for a physiotherapy clinic (fictional), built as the capstone
project (Project B) of the Software Development Attestation at Vanier College.

One secure backend serves three clients: a website for patients and visitors, a desktop app for
the front desk, and a mobile app for patients.

> All people, clinics and data in this project are fictional. No real patient information is
> ever used.

## Live demo

| What | Address |
|---|---|
| Website | https://clinique-physio.vercel.app |
| API | https://clinique-physio-api.onrender.com |
| API documentation (OpenAPI) | https://clinique-physio-api.onrender.com/docs |

The API runs on a free plan and sleeps when unused: the first request after a pause can take
about a minute. Demo account credentials are given to the supervisor privately, never here.

## Architecture

```
  Website (React)      Desktop (C# WPF)      Mobile (Expo)
        \                    |                    /
         \                   |                   /
          +------- REST API /api/v1 (FastAPI) --+
                             |
               PostgreSQL 16 (+ btree_gist, pgvector)
```

- **No client talks to the database.** Every business rule and every permission check is
  enforced by the API; the clients are never trusted.
- **Authentication:** Argon2id password hashing, 10-minute access tokens, refresh token in an
  httpOnly cookie with rotation and reuse detection, mandatory TOTP two-factor authentication for
  staff, rate limiting and account lockout.
- **No double booking:** a PostgreSQL exclusion constraint guarantees that a therapist can never
  have two overlapping appointments, even under concurrent requests (tested with 30 simultaneous
  bookings).
- **Time zones:** times are stored in UTC and shown in Montréal time, correctly across daylight
  saving changes.
- **Bilingual:** French by default, English available, in every client.

More detail: [docs/requirements.md](docs/requirements.md) (vision and product backlog),
[docs/architecture.md](docs/architecture.md), [docs/erd.md](docs/erd.md) (data model) and
[docs/openapi.json](docs/openapi.json) (API contract).

## Repository structure

| Folder | Content | Technology |
|---|---|---|
| `api/` | REST API, business rules, database migrations, tests | Python 3.14, FastAPI, SQLAlchemy 2, Alembic, pytest |
| `web/` | Public website (services, team, availability) | React 18, Vite, TanStack Query, i18next, Vitest |
| `desktop/` | Front-desk app (login with MFA, day schedule) | C# .NET 8, WPF, MVVM (CommunityToolkit.Mvvm), xUnit |
| `mobile/` | Patient app (login, my appointments) | Expo SDK 58, React Native, TypeScript, Jest |
| `docs/` | Data model, API contract, design documents | Markdown, Mermaid |
| `.github/` | CI pipelines, Dependabot, templates | GitHub Actions |

## Running it locally

### Prerequisites

- Python 3.14, Node.js 24 LTS, .NET 8 SDK, Docker Desktop, Git
- Windows is needed for the desktop app (WPF)

### 1. Settings and database

```
copy .env.example .env
```

Open `.env` and replace every `change-me` with your own values (the file explains how to
generate each key). `.env` is never committed.

```
docker compose up -d
```

This starts PostgreSQL 16 with pgvector on port 5433.

### 2. API

```
cd api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
alembic upgrade head
python -m app.seed
python -m uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000, documentation: http://127.0.0.1:8000/docs
- `python -m app.seed` creates the demo data once (6 therapists, front desk, admin,
  5 services, 50 patients, appointments).
- `python -m app.seed --refresh-appointments` adds demo appointments for the next two weeks
  (safe to run again).

### 3. Website

```
cd web
npm ci
npm run dev
```

Open http://localhost:5173. It uses the local API by default (`web/.env.example`).

### 4. Desktop app

Open `desktop/CliniquePhysio.Desktop.sln` in Visual Studio, set `CliniquePhysio.Desktop` as the
startup project, and press F5. The API address is in
`desktop/src/CliniquePhysio.Desktop/appsettings.json`. Staff log in with a password and a
6-digit code from an authenticator app (a QR code is shown on the first login).

### 5. Mobile app

```
cd mobile
npm ci
npx expo start
```

Scan the QR code with Expo Go (same Wi-Fi), or press `a` for an Android emulator. It uses the
live API by default (`mobile/.env.example`).

## Tests

| App | Command | What it covers |
|---|---|---|
| API | `cd api` then `python -m pytest` | Business rules, authorization, double booking under concurrency, DST |
| Website | `cd web` then `npm test` | Pages, languages, time display, XSS safety |
| Desktop | `cd desktop` then `dotnet test CliniquePhysio.Desktop.sln` | API client, view models, time display |
| Mobile | `cd mobile` then `npm test` | Screens, errors, time display |

The API tests create and use their own database (`physio_test`), so they never touch the demo
data.

## Continuous integration and deployment

Every pull request runs the pipeline of the app it changes:

| Pipeline | Steps |
|---|---|
| `api-ci` | ruff (lint and format), migrations, pytest with coverage, Bandit, pip-audit |
| `web-ci` | npm ci, ESLint (with accessibility rules), Prettier, Vitest, build, npm audit |
| `desktop-ci` | restore, dotnet format, build, xUnit tests (Windows) |
| `mobile-ci` | npm ci, ESLint, TypeScript type-check, Jest |

Dependabot checks all dependencies weekly. After merging to `main`, the API (Render) and the
website (Vercel) are deployed automatically from the deployment copy of this repository.

## Working on the project

Every change follows the same routine: an issue, a branch (`feature/<issue>-short-name`), a pull
request using the template, green CI, then a squash merge. Commit messages follow
[Conventional Commits](https://www.conventionalcommits.org) (`feat:`, `fix:`, `docs:`, `test:`,
`chore:`).

## Security

- Secrets are only in environment variables (`.env` locally, the host's settings in
  production), never in the repository.
- Clinical data is never sent to the front desk, and patients only ever see their own
  appointments (tested).
- Security headers: HSTS, nosniff and frame denial on the API and the website, plus a strict
  Content-Security-Policy on the website.

Please report security problems privately to the project owner rather than in a public issue.

## Author

Claire Mancini, Vanier College, 2026.
