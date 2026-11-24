# Runbook — Clinique Physio Mont-Royal

What to do when something has to be checked, redeployed, rotated, backed up or restored.
Setup and settings: [deployment.md](deployment.md). Confidentiality incidents (Law 25):
[privacy/README.md](privacy/README.md).

Rules that always apply:

- Secrets (database URL, keys) are typed only in the host's settings or in your own `.env`.
  Never in the repository, an issue, a screenshot or a chat.
- The deployment copy (`kkprojects5/clinique-physio`) is never edited directly.
- Stripe stays in test mode.

## 1. Is it working?

| Check | Where | Healthy |
|---|---|---|
| API up | https://clinique-physio-api.onrender.com/health | `{"status":"ok"}` (first call after a sleep: up to about 50 seconds) |
| API errors | Render → service → **Logs** | No `ERROR` or `Traceback` |
| Last deploys | Render → **Events**; Vercel → **Deployments** | Latest is **Live** / **Ready**, same commit as `main` |
| Database | Neon → project → **Monitoring** | Connections and storage below the plan limits |
| Payments | Stripe (Sandbox) → **Developers → Webhooks** → endpoint | Recent events delivered (200) |
| Unusual access | Website → Administration → **Journal d'audit** | No red lines (refused access, more than 10 patients in an hour) |

## 2. Redeploy and roll back

### 2.1 Normal deploy

```
git checkout main
git pull
git push deploy main
```

Render and Vercel deploy by themselves in 2 to 5 minutes. Then do the checks of
[deployment.md section 4](deployment.md#4-after-every-deployment).

### 2.2 Redeploy the same version (API stuck, settings changed)

- **API:** Render → service → **Manual Deploy → Deploy latest commit**. A change of
  environment variable also redeploys by itself.
- **Website:** Vercel → **Deployments** → latest → **⋯ → Redeploy**. Needed after changing
  `VITE_API_URL`, because it is read at build time.

### 2.3 Roll back a bad version

1. **Website:** Vercel → **Deployments** → the last good one → **⋯ → Instant Rollback**.
2. **API:** Render → **Events** → the last good deploy → **Rollback**.
3. Fix the problem with a normal pull request, then deploy again (2.1). Render keeps the
   rolled-back version until the next push to the deployment copy.

A rollback does not undo database migrations. Migrations only add things (tables, columns,
triggers), so an older API still works with a newer database. If a migration itself is wrong,
fix it with a new migration (roll forward); `alembic downgrade -1` exists for every migration
but must first be tried on a copy of the database (section 5.3).

## 3. Rotating keys

Rotate a key at once if it may have been seen (pasted in a chat, committed, shown on screen),
and otherwise once a year. After each rotation, write the date in the table at the end of this
section.

### 3.1 `JWT_SECRET` (signs access tokens)

1. Render → **Environment** → `JWT_SECRET` → **Generate** (or paste a value from
   `python -c "import secrets; print(secrets.token_urlsafe(48))"`) → **Save**. The API restarts.
2. Effect: access tokens signed with the old secret stop working; the apps get a new one with
   the refresh cookie (refresh tokens are random values, not signed). Staff in the middle of
   the two-step login start the login again.

### 3.2 `FIELD_ENCRYPTION_KEY` (encrypts clinical notes, emergency contacts, MFA secrets)

Never replace this key directly: data encrypted with the old key would become unreadable.
The API accepts several keys, the new one first.

1. Make a backup (section 5.2) and keep the **old key** with it.
2. Generate a new key:
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
3. Render → **Environment** → `FIELD_ENCRYPTION_KEY` = `NEW_KEY,OLD_KEY` → **Save**. New data is
   now encrypted with the new key; old data is still readable.
4. Re-encrypt everything with the new key, from your computer, with `DATABASE_URL` and
   `FIELD_ENCRYPTION_KEY=NEW_KEY,OLD_KEY` in your `.env` for this command only:
   ```
   cd api
   python -m app.rotate_key
   ```
   It works in one transaction (all or nothing), checks every value decrypts to the same text,
   and writes `key_rotation` in the audit log. Signed clinical notes stay locked for any other
   change (migration 0015).
5. Render → `FIELD_ENCRYPTION_KEY` = `NEW_KEY` → **Save**. Put your local `.env` back.
6. Check: log in as a therapist and open a signed note; log in as staff (MFA code).

### 3.3 Database password (Neon)

1. Neon → **Roles** → `neondb_owner` → **Reset password**. Copy the new connection string.
2. Render → `DATABASE_URL` → paste → **Save** (the API restarts with the new password).
3. Update your own `.env` if it points to Neon. The old password stops working at once.

### 3.4 Stripe keys (test mode)

1. Stripe (Sandbox) → **Developers → API keys** → secret key → **Rotate key** (choose "now").
2. Render → `STRIPE_SECRET_KEY` (and `STRIPE_PUBLISHABLE_KEY` if it changed) → **Save**.
3. Webhook secret: **Developers → Webhooks** → endpoint → **Roll secret** →
   `STRIPE_WEBHOOK_SECRET` in Render. Check with a test payment (card 4242 4242 4242 4242).

### 3.5 OpenAI key

1. platform.openai.com → **API keys** → **Create new secret key**.
2. Render → `OPENAI_API_KEY` → **Save**. Ask the chatbot a question.
3. Delete the old key in OpenAI. While no key works, the chatbot keeps answering with keyword
   search (v1), so nothing breaks for visitors.

### 3.6 A staff account may be compromised

Administration → **Personnel** → the person → deactivate the account: their sessions end at
once. Then
check their recent actions in the **Journal d'audit** (filter by email), and record an incident
if patient information may have been seen (section 6).

| Key | Last rotated | Why |
|---|---|---|
| Neon password | | |
| `JWT_SECRET` | | |
| `FIELD_ENCRYPTION_KEY` | | |
| Stripe | | |
| OpenAI | | |

## 4. Releasing a version (desktop installer, Android app)

Written with release v1.0.0 (D3): version tag, desktop installer attached to the GitHub
release, Android APK or Expo link.

## 5. Backup and restore

### 5.1 What protects the data

| Copy | Made by | Restores |
|---|---|---|
| Neon history (point-in-time restore) | Neon, continuously | The whole database as it was at a moment within the plan's restore window (Neon → **Backup & Restore**; the window depends on the plan) |
| Logical backup (`pg_dump`) | You, before risky changes and once a week during the demo period | Everything, anywhere, at any later time |
| The code | GitHub (two copies) | The app; demo data with `python -m app.seed` |

Encrypted fields stay encrypted in every backup. **A backup can only be read with the
`FIELD_ENCRYPTION_KEY` that was in use when it was made**: keep that key with the backup, in a
password manager, never in the same folder.

### 5.2 Make a logical backup

On your computer, with Docker running, in a folder outside the repository (for example
`C:\backups`). The image `postgres:17` brings `pg_dump`; nothing to install.

```
mkdir C:\backups
cd C:\backups
set /p PGURL=Paste the Neon connection string and press Enter: 
docker run --rm -v "%cd%":/backup postgres:17 pg_dump "%PGURL%" --format=custom --no-owner --file /backup/clinique.dump
set PGURL=
ren clinique.dump clinique-YYYY-MM-DD.dump
dir
```

Replace `YYYY-MM-DD` with today's date. The connection string is typed at the prompt, so it is
not saved in a file, and `set PGURL=` forgets it. Never commit or share a backup: it contains
personal information.

### 5.3 Test the backup (restore into your local database)

Restore drill, without touching production, into the local Docker database
(`docker compose up -d` at the repository root, port 5433):

```
cd C:\backups
docker run --rm -v "%cd%":/backup postgres:17 pg_restore --clean --if-exists --no-owner --dbname "postgresql://physio:YOUR_LOCAL_PASSWORD@host.docker.internal:5433/physio" /backup/THE_FILE.dump
```

Then, with the backup's `FIELD_ENCRYPTION_KEY` in your local `.env`, start the API and the
website and open a signed clinical note: if it reads, the backup is good. Write the date of
the drill here: **last restore drill:** ____.

### 5.4 Restore production

Only after an accident (data deleted, bad migration):

1. **Point in time (recent accident):** Neon → **Backup & Restore** → choose the time just
   before the accident → restore to a **new branch** first, check it (connect your local API to
   it), then restore the main branch. Render keeps working with the same `DATABASE_URL`.
2. **From a logical backup (older accident):** create an empty Neon branch, restore into it
   with `pg_restore` as in 5.3 (using its connection string), check it, then put its connection
   string in Render → `DATABASE_URL`.
3. Put the backup's encryption key in Render if it is not the current one.
4. Record what happened in the incident register if personal information was lost or exposed
   (section 6).

## 6. Confidentiality incident (Law 25)

1. Stop the leak first (deactivate the account, rotate the key, roll back the version).
2. Administration → **Incidents** → new entry: what happened, the data and people concerned,
   and whether there is a **risk of serious injury**.
3. If there is: notify the Commission d'accès à l'information and the people concerned, and
   write the dates in the entry. Entries can be completed but never deleted.

## 7. Common problems

| Symptom | Likely cause | Fix |
|---|---|---|
| The website shows "cannot load" right after a while without visits | The free API is waking up | Wait up to a minute and retry |
| Browser console: CORS error | Site address missing from `ALLOWED_ORIGINS` | Add it in Render (comma-separated, no trailing `/`) |
| An image or font is blocked | Content-Security-Policy in `web/vercel.json` | Add the host to `img-src` / `font-src`, keeping `'self'` |
| The API does not start after a deploy | A migration failed (Render logs show `alembic`) | Roll back (2.3), fix the migration in a pull request |
| The chatbot answers but never in sentences | OpenAI key missing, wrong or out of credit | Render logs (`OpenAIError`); new key (3.5) |
| A paid deposit stays "on hold" | Webhook refused (400: wrong `STRIPE_WEBHOOK_SECRET`) | Stripe → Webhooks → endpoint → failed event; fix the secret, **Resend** |
| Tests fail only in the evening | Dates compared in UTC (CI) and Montréal time | Use `today_local()` in tests |
| `No space left on device` locally | Docker images and caches | `docker system prune`, delete `node_modules` and `.venv` and reinstall |
