# Architecture — Clinique Physio Mont-Royal

Status: **D1 (v0.1.0)**. Diagrams follow the [C4 model](https://c4model.com) (levels 1 and 2,
plus a short level 3 for the API). Design decisions are recorded as ADRs in [adr/](adr/).

Related documents: [requirements.md](requirements.md), [erd.md](erd.md) (data model),
[data-dictionary.md](data-dictionary.md), [openapi.json](openapi.json) (API contract),
[threat-model.md](threat-model.md), [data-classification.md](data-classification.md).

## 1. System context (C4 level 1)

Who uses the system, and which outside systems it depends on.

```mermaid
flowchart TB
    visitor(["Visitor<br/><i>looks at services and free times</i>"])
    patient(["Patient<br/><i>books, pays, follows exercises</i>"])
    therapist(["Physiotherapist<br/><i>availability, notes, programs</i>"])
    desk(["Front-desk agent<br/><i>schedule, check-in, phone bookings</i>"])
    admin(["Clinic administrator<br/><i>services, staff, reports, Law 25</i>"])

    system["<b>Clinique Physio Mont-Royal</b><br/>Booking and patient portal<br/>(website, mobile app, desktop app, API)"]

    stripe["Stripe<br/><i>deposit payments (D2)</i>"]
    email["Email provider<br/><i>confirmations, reminders</i>"]
    llm["LLM provider<br/><i>chatbot answers (D2)</i>"]
    authapp["Authenticator app<br/><i>staff 6-digit codes</i>"]

    visitor --> system
    patient --> system
    therapist --> system
    desk --> system
    admin --> system
    system --> stripe
    system --> email
    system --> llm
    therapist -.-> authapp
    desk -.-> authapp
    admin -.-> authapp

    classDef person fill:#1f5f5b,stroke:#164542,color:#fffdf9
    classDef sys fill:#f6f2ea,stroke:#1f5f5b,stroke-width:2px,color:#1d2a2a
    classDef ext fill:#e3e7ee,stroke:#8a96a8,color:#1d2a2a
    class visitor,patient,therapist,desk,admin person
    class system sys
    class stripe,email,llm,authapp ext
```

## 2. Containers (C4 level 2)

The separately deployed parts, their technology, and how they talk to each other.

```mermaid
flowchart TB
    patient(["Patient / visitor"])
    staff(["Physiotherapist, admin"])
    desk(["Front-desk agent"])

    subgraph sys["Clinique Physio Mont-Royal"]
        web["<b>Website</b><br/>React 18, Vite<br/><i>Vercel</i>"]
        mobile["<b>Mobile app</b><br/>Expo SDK 58, React Native, TypeScript<br/><i>Expo Go / APK</i>"]
        desktop["<b>Desktop app</b><br/>C# .NET 8, WPF, MVVM<br/><i>Windows, GitHub Releases</i>"]
        api["<b>REST API</b> /api/v1<br/>Python 3.14, FastAPI, SQLAlchemy 2<br/><i>Render</i>"]
        db[("<b>Database</b><br/>PostgreSQL 16<br/>btree_gist, pgvector<br/><i>Neon</i>")]
    end

    stripe["Stripe (D2)"]
    email["Email provider"]
    llm["LLM provider (D2)"]

    patient -- "HTTPS" --> web
    patient -- "uses" --> mobile
    staff -- "HTTPS" --> web
    desk -- "uses" --> desktop

    web -- "JSON over HTTPS<br/>Bearer token" --> api
    mobile -- "JSON over HTTPS<br/>Bearer token" --> api
    desktop -- "JSON over HTTPS<br/>Bearer token" --> api

    api -- "SQL over TLS" --> db
    api --> email
    api --> llm
    stripe -- "signed webhooks" --> api

    classDef person fill:#1f5f5b,stroke:#164542,color:#fffdf9
    classDef container fill:#fffdf9,stroke:#1f5f5b,stroke-width:2px,color:#1d2a2a
    classDef ext fill:#e3e7ee,stroke:#8a96a8,color:#1d2a2a
    class patient,staff,desk person
    class web,mobile,desktop,api,db container
    class stripe,email,llm ext
    style sys fill:#f6f2ea,stroke:#1f5f5b,stroke-width:2px,color:#164542
```

| Container | Responsibility | Technology | Hosting |
|---|---|---|---|
| Website | Public pages, booking, patient portal, therapist workspace, admin | React 18, Vite, React Router, TanStack Query, i18next | Vercel (static files, CSP headers) |
| Mobile app | Patient: appointments, exercises, reminders | Expo SDK 58, React Native, TypeScript, SecureStore | Expo Go (dev), APK (release) |
| Desktop app | Front desk: day schedule, check-in, phone bookings, offline mode (D3) | C# .NET 8, WPF, CommunityToolkit.Mvvm | Windows install from GitHub Releases |
| REST API | **All** business rules and permission checks; the only door to the data | FastAPI, Pydantic, SQLAlchemy 2, Alembic, Argon2id, PyJWT, pyotp, slowapi | Render (free plan) |
| Database | Relational data, constraints (no double booking), embeddings for the chatbot (D2) | PostgreSQL 16 with `btree_gist` and `pgvector` | Neon; Docker locally |

**Key rule:** the three clients are never trusted. They only display data and send requests; the
API checks every request (who is calling, with which role, and whether they own the data).

## 3. Inside the API (C4 level 3, simplified)

Each request goes through the same layers. Business logic never lives in the routers (NFR-11).

```mermaid
flowchart LR
    req(["HTTP request"]) --> mw["Middleware<br/>CORS, security headers,<br/>rate limits"]
    mw --> router["Routers<br/><i>app/routers</i><br/>receive and answer"]
    router --> deps["Dependencies<br/><i>app/dependencies.py</i><br/>who is logged in? role? MFA?"]
    router --> schemas["Schemas<br/><i>app/schemas</i><br/>validate input and output"]
    router --> services["Services<br/><i>app/services</i><br/>business rules"]
    services --> models["Models<br/><i>app/models</i><br/>tables (SQLAlchemy)"]
    models --> db[("PostgreSQL")]
    services --> core["Core<br/><i>app/core</i><br/>settings, hashing, tokens,<br/>encryption"]
```

| Layer | Folder | Example |
|---|---|---|
| Routers | `app/routers` | `auth.py` receives a login and returns tokens |
| Dependencies | `app/dependencies.py` | `require_staff` refuses tokens without MFA |
| Schemas | `app/schemas` | `RegisterRequest` refuses weak passwords |
| Services | `app/services` | `slots.py` computes free slots; `session_service.py` rotates refresh tokens |
| Models | `app/models` | `Appointment` with the no-overlap constraint |
| Core | `app/core` | `security.py` (Argon2id, JWT), `crypto.py` (field encryption) |

## 4. API routes

The full contract, with request and response schemas, is generated by FastAPI:
[openapi.json](openapi.json), live at https://clinique-physio-api.onrender.com/docs.

### Implemented (D1)

| Method and route | Purpose | Access |
|---|---|---|
| `POST /auth/register` | Create a patient account (consents recorded) | Public, rate-limited |
| `POST /auth/verify-email` | Confirm the email address | Public, rate-limited |
| `POST /auth/login` | Log in: tokens (patients) or MFA ticket (staff) | Public, rate-limited |
| `POST /auth/mfa/setup` | First staff login: create the authenticator secret | MFA ticket |
| `POST /auth/mfa/verify` | Check the 6-digit code, open the staff session | MFA ticket |
| `POST /auth/refresh` | New tokens from the refresh cookie (rotation) | Refresh cookie |
| `POST /auth/logout` | Revoke the refresh token | Refresh cookie |
| `POST /auth/password/forgot` | Send a password reset link (same answer for every email) | Public, rate-limited |
| `POST /auth/password/reset` | Set a new password with the link; cancels all sessions | Public, rate-limited |
| `GET /me` | The logged-in user | Any logged-in user |
| `GET /me/appointments` | Own upcoming appointments | Patient (own only) |
| `GET /staff/session` | Check a staff session (with MFA) | Staff with MFA |
| `GET /services`, `GET /therapists` | Catalog and team | Public |
| `GET /availability` | Free slots for a service | Public |
| `GET`, `PUT /therapist/availability` | Own weekly hours | Therapist with MFA |
| `POST`, `DELETE /therapist/availability/exceptions` | Own time off | Therapist with MFA (owner only) |
| `GET /desk/schedule?date=` | All therapists' appointments for a day | Front desk or admin with MFA |
| `GET /health` | Health check for the host | Public |

### Planned (from spec B.7)

| Method and route | Purpose | Access | Deliverable |
|---|---|---|---|
| `POST /appointments/hold`, `POST /appointments/{id}/pay` | Hold a slot 10 minutes, pay the deposit | Patient | D2 |
| `POST /webhooks/stripe` | Payment confirmation (signed, idempotent) | Stripe | D2 |
| `POST /appointments/{id}/reschedule`, `POST /appointments/{id}/cancel` | Change or cancel (24 h rule) | Patient (owner) | D2 |
| `GET /therapist/schedule`, `GET /therapist/patients/{id}` | Own schedule; patient file | Therapist (care relationship) | D2 |
| `POST /therapist/appointments/{id}/notes`, `GET /therapist/notes/{id}` | Clinical notes (encrypted, audited) | Therapist (author / care relationship) | D2 |
| `POST /therapist/patients/{id}/programs`, `GET /me/program`, `POST /me/program/logs` | Exercise programs and check-off | Therapist; patient (own) | D2 |
| `POST /desk/appointments`, `POST /desk/appointments/{id}/check-in` | Phone booking, check-in | Front desk | D2 |
| `POST /chat/messages`, `POST /chat/feedback` | Chatbot | Public, rate-limited | D2 |
| `GET /me/receipts/{id}.pdf` | Insurance receipt | Patient (own) | D3 |
| `POST /desk/sync` | Offline actions from the desktop | Front desk | D3 |
| `/admin/*` (services, staff, audit, privacy requests, incidents, reports) | Administration and Law 25 | Admin | D3 |

## 5. Deployment and delivery

```mermaid
flowchart LR
    dev(["Developer"]) -- "branch + pull request" --> gh["GitHub<br/>stevatak/Khadizhat-Synth"]
    gh -- "CI on every PR:<br/>api-ci, web-ci,<br/>desktop-ci, mobile-ci" --> gh
    gh -- "after merge:<br/>git push deploy main" --> mirror["Deployment copy<br/>kkprojects5/clinique-physio"]
    mirror -- "auto deploy" --> render["Render<br/>API"]
    mirror -- "auto deploy" --> vercel["Vercel<br/>website"]
    render -- "alembic upgrade head<br/>at start" --> neon[("Neon<br/>PostgreSQL")]
```

- The API applies database migrations automatically when it starts.
- Secrets (database URL, signing key, encryption key) are set in the Render dashboard, never in
  the repository. See [ADR-006](adr/0006-deployment-copy.md) for why a deployment copy is used.
- The desktop app is published as a release on GitHub (D3); the mobile app as an APK or Expo link.

## 6. Cross-cutting concerns

| Concern | How it is handled |
|---|---|
| Security | See [threat-model.md](threat-model.md). Authentication: [ADR-002](adr/0002-token-storage.md). |
| Concurrency | Database exclusion constraint: [ADR-001](adr/0001-double-booking-exclusion-constraint.md). |
| Time zones | UTC storage, Montréal display: [ADR-004](adr/0004-time-zones.md). |
| Languages | French by default, English available; texts in translation files in each client (NFR-10). |
| Accessibility | Labels, keyboard navigation, contrast, skip link on the website (ESLint `jsx-a11y`); 48 px touch targets on mobile (NFR-09). |
| Testing | Automated tests in every app, run by CI on every pull request; API tests on their own database. |
