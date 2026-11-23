# Security audit report (D3)

Clinique Physio Mont-Royal · version 1.0.0 · audit date: 22–23 November 2026 · author: KK

This report checks the system against the **OWASP Top 10 (2021)**, with evidence for each
category, and records the **OWASP ZAP** scans before and after the fixes, the **dependency
audit** and the **residual and accepted risks**. It complements the threat model
([../threat-model.md](../threat-model.md)) and the data classification
([../data-classification.md](../data-classification.md)).

All data in the system is fictional. Payments use Stripe in test mode.

## 1. Scope and method

| Part | What was checked | How |
|---|---|---|
| API (FastAPI, PostgreSQL) | All 76 endpoints | Code review, 465 automated tests, Bandit, ZAP API scan (passive on the live API, **active attacks** on a throwaway copy) |
| Website (React on Vercel) | Pages, headers, CSP | 97 automated tests, ZAP baseline scan of the live site, `npm audit` |
| Desktop app (C# WPF) | Login, desk actions, receipts | 71 automated tests, code review (no secret stored on disk; tokens kept in memory) |
| Mobile app (Expo) | Login, booking, payment sheet | 36 automated tests, `npm audit` |
| Supply chain | Python, npm and NuGet packages; GitHub Actions | `pip-audit`, `npm audit`, Dependabot |

The ZAP scans run in GitHub Actions ([../../.github/workflows/security-scan.yml](../../.github/workflows/security-scan.yml)),
started by hand with the label `before` or `after`. The active scan never touches the live
system: the workflow starts its own API with a throwaway database and fictional data, then
attacks it (SQL injection, cross-site scripting, path traversal, command injection, etc.).

## 2. OWASP Top 10 (2021) checklist

✅ = in place and tested · ⚠️ = in place with a documented limit (see section 5)

### A01 Broken Access Control ✅

| Control | Evidence |
|---|---|
| Every route checks the role on the server (`require_patient`, `require_staff`, `require_admin`); the apps are never trusted | `test_only_administrators_use_the_admin_pages`, `test_staff_endpoint_refuses_patients_even_with_mfa_claim`, `test_other_roles_cannot_read_reports` |
| Patients reach only their own data; another patient's record answers 404 (no enumeration) | `test_cannot_pay_someone_elses_appointment`, `test_no_receipt_for_another_patients_appointment`, `test_patients_see_only_their_own_requests` |
| Clinical notes only for therapists with a care relationship (BR-6); front desk and admin never | `test_therapist_without_care_relationship_gets_404_and_is_audited`, `test_front_desk_and_admin_never_reach_clinical_notes` |
| The client cannot choose its role or the amount it pays | `test_role_cannot_be_chosen_by_the_client`, `test_an_amount_sent_by_the_client_is_ignored` |
| Staff need the two-factor session for every staff route | `test_staff_endpoint_refuses_staff_token_without_mfa_claim`, `test_admin_needs_the_two_factor_session` |
| ZAP: no access-control finding; every protected endpoint answered 401 without a token | ZAP reports, alert 100000 (401 on all protected routes) |

### A02 Cryptographic Failures ✅

| Control | Evidence |
|---|---|
| HTTPS everywhere; HSTS on the API and the website | `test_security_headers_on_every_response`; `web/vercel.json` |
| Passwords hashed with **Argon2id**; reset tokens stored as hashes only | `test_password_is_stored_as_argon2id_hash`, `test_only_a_hash_of_the_token_is_stored` |
| Clinical notes and emergency contacts **encrypted** in the database (Fernet, key outside the code) | `test_note_content_is_encrypted_in_the_database`, `test_emergency_contact_is_encrypted` |
| Card data never reaches our systems (Stripe Elements / payment sheet; ADR-0007) | `test_paying_a_hold_creates_a_deposit_intent`; ADR-0007 |
| Secrets only in `.env` and the hosts' settings, never in git | `.gitignore`; CI uses throwaway values; key rotation in the runbook |

### A03 Injection ✅

| Control | Evidence |
|---|---|
| All database access through SQLAlchemy with bound parameters; no SQL built from text | Code review; Bandit (no B608) |
| Every request body validated by Pydantic (types, lengths, formats); invalid input answers 422 | `test_invalid_service_values_are_refused`, `test_invalid_questions_are_rejected`, `test_invalid_incidents_are_refused` |
| React escapes all text; strict CSP (`script-src 'self'` + Stripe) | `web/src/pages/pages.test.jsx`; `web/vercel.json` |
| Chatbot: prompt injection refused; the question cannot close the data tags | `test_prompt_injection_is_refused_and_nothing_is_revealed`, `test_question_cannot_close_the_data_tags` |
| Uploaded photos are decoded and re-encoded, never stored as sent | `test_files_that_are_not_valid_images_are_refused`, `test_location_and_camera_details_are_removed` |
| **ZAP active scan: 0 High, 0 Medium** (SQL injection, XSS, path traversal, command injection tried on 256 requests; no server error 500) | [zap/before/api-active.md](zap/before/api-active.md) |

### A04 Insecure Design ✅

| Control | Evidence |
|---|---|
| Threat model (STRIDE) updated with every feature; abuse cases written as tests | [../threat-model.md](../threat-model.md) |
| Double booking impossible even under load: database exclusion constraint (ADR-0001) | `test_30_concurrent_bookings_only_one_succeeds`, `test_the_database_alone_never_accepts_two_bookings` |
| Payment confirmed only by Stripe's signed webhook, applied once | `test_a_fake_or_altered_webhook_is_refused`, `test_the_same_event_twice_is_applied_once` |
| Clinical notes cannot be changed after signature; audit log and incident register cannot be deleted (database triggers) | `test_database_refuses_changing_a_signed_note_or_deleting_any_note`, `test_database_refuses_changing_or_deleting_audit_entries`, `test_incident_entries_can_never_be_deleted` |
| Chatbot safety rules run before any AI; the AI never sees personal data | `test_emergencies_get_only_911_811_988`, `test_provider_gets_only_the_masked_question_and_public_passages` |

### A05 Security Misconfiguration ✅ (after fixes)

| Control | Evidence |
|---|---|
| Security headers on every API answer: `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Cache-Control: no-store`, HSTS, **`Cross-Origin-Resource-Policy: same-origin`** (added after ZAP) | `test_security_headers_on_every_response` |
| Website: CSP, HSTS, `X-Frame-Options`, `Permissions-Policy`, **`Cross-Origin-Opener-Policy`** and a restricted **`Access-Control-Allow-Origin`** (added after ZAP) | `web/vercel.json`; ZAP after scan |
| CORS on the API limited to our own website | `test_cors_allows_the_web_app_and_refuses_other_sites` |
| Errors never show stack traces or internals; generic messages for login and recovery | `test_wrong_password_and_unknown_email_get_the_same_answer`, `test_same_answer_whether_or_not_the_account_exists` |
| ZAP findings fixed or justified: see section 3 | ZAP before/after |

### A06 Vulnerable and Outdated Components ⚠️

See section 4. CI blocks known vulnerabilities in the API (`pip-audit`) and the website
(`npm audit`); Dependabot opens update pull requests every week. Remaining moderate
advisories are in mobile **build tools** only (R-1) and .NET 8 support ends in November 2026 (R-8).

### A07 Identification and Authentication Failures ✅

| Control | Evidence |
|---|---|
| Strong passwords required; weak ones refused | `test_weak_passwords_are_refused` |
| **Two-factor authentication (TOTP) mandatory for all staff**; a code works once | `test_staff_password_alone_gives_no_tokens`, `test_a_code_cannot_be_used_twice` |
| Account lockout after repeated failures (password and MFA), same answer as a wrong password | `test_account_locks_after_too_many_wrong_passwords`, `test_locked_answer_looks_exactly_like_a_wrong_password`, `test_wrong_mfa_codes_also_lock_staff_accounts` |
| Rate limiting per IP on login, registration, recovery, chat and booking | `test_login_is_rate_limited_per_ip`, `test_forgot_password_is_rate_limited_per_ip`, `test_chat_is_rate_limited_per_ip`; ZAP saw 429 answers |
| Access tokens last 10 minutes; refresh tokens rotate and a reused one cancels every session; staff sessions end after 15 minutes of inactivity | `test_access_token_lasts_at_most_10_minutes`, `test_reusing_an_old_refresh_token_cancels_all_sessions`, `test_staff_session_expires_after_15_minutes_of_inactivity` |
| Refresh token in an httpOnly, Secure cookie, never readable by JavaScript (ADR-0002) | `test_login_returns_access_token_and_httponly_refresh_cookie` |
| Password reset links work once, expire after 30 minutes and close every session | `test_link_works_only_once`, `test_link_expires_after_30_minutes`, `test_reset_cancels_every_session` |

### A08 Software and Data Integrity Failures ✅

| Control | Evidence |
|---|---|
| Stripe webhooks verified with the signing secret before anything changes | `test_a_fake_or_altered_webhook_is_refused` |
| Lock files committed (`package-lock.json`, NuGet); CI installs exactly them (`npm ci`) | Workflows in `.github/workflows` |
| Every change goes through a pull request with 4 CI pipelines; the live site is deployed from `main` only | ADR-0006 (deployment copy) |
| GitHub Actions have read-only permissions by default | `permissions: contents: read` in each workflow |

### A09 Security Logging and Monitoring Failures ✅

| Control | Evidence |
|---|---|
| Append-only audit log of every access to patient data, refused accesses included, with app and IP | `test_patient_file_with_history_and_audit`, `test_therapist_without_care_relationship_gets_404_and_is_audited` |
| The administrator sees unusual access in red (more than 10 patients in one hour) | `web/src/pages/admin.test.jsx`, US-ADM-03 |
| Law 25 incident register, kept 5 years, never deleted | `test_record_an_incident_and_see_missing_notifications` |
| Server logs never contain passwords, tokens, email bodies or full email addresses | `test_queued_emails_appear_in_the_server_log_without_the_address`, `test_only_the_masked_question_is_logged_with_its_sources` |

### A10 Server-Side Request Forgery ✅

| Control | Evidence |
|---|---|
| The API never fetches a URL given by a user. Its only outgoing calls are to fixed hosts (Stripe, OpenAI) through their official libraries | Code review (`stripe_gateway.py`, `chatbot/openai_client.py`) |
| Photos are uploaded as files, never as links to fetch | `PUT /admin/therapists/{id}/photo` takes the image body only |

> **OWASP Top 10 2025.** The newer list adds *Software Supply Chain Failures* (covered by
> A06 and A08 above) and *Mishandling of Exceptional Conditions* (covered by A05: no stack
> traces, provider errors fall back safely, e.g. `test_stripe_error_gives_502_and_changes_nothing`,
> `test_provider_error_falls_back_to_the_passage`, `test_a_failed_refund_cancels_nothing`).

## 3. ZAP scans: before and after

Reports: [zap/before/](zap/before/) and [zap/after/](zap/after/).

### 3.1 Summary

| Scan | Target | Mode | Before (H/M/L/I) | After (H/M/L/I) |
|---|---|---|---|---|
| live-web | https://clinique-physio.vercel.app | Passive | 0 / **1** / 3 / 11 | **0 / 0 / 2** / 11 |
| live-api | https://clinique-physio-api.onrender.com | Passive (safe mode) | 0 / 0 / 1 / 8 | **0 / 0 / 0** / 8 |
| api-active | Throwaway copy of the API | **Active attacks** | 0 / 0 / 1 / 7 | **0 / 0 / 0** / 7 |

H = High, M = Medium, L = Low, I = Informational.

After the fixes, the only Low findings left are on the website: Cross-Origin-Embedder-Policy
(accepted, R-11) and HSTS on some files (false positive). Both are explained below.

### 3.2 Findings and what was done

| ZAP alert (id) | Risk | Where | Decision | Done |
|---|---|---|---|---|
| Cross-Domain Misconfiguration (10098): `Access-Control-Allow-Origin: *` | Medium | Website (Vercel default) | **Fixed**: the header now names the website only | `web/vercel.json` |
| Cross-Origin-Opener-Policy missing (90004) | Low | Website | **Fixed**: `same-origin` | `web/vercel.json` |
| Cross-Origin-Resource-Policy missing (90004) | Low | API | **Fixed**: `same-origin` on every answer; therapist photos `cross-origin` because the website shows them | `api/app/main.py`, `test_security_headers_on_every_response` |
| Cross-Origin-Embedder-Policy missing (90004) | Low | Website | **Accepted** (R-11): `require-corp` blocks Stripe's payment frames, which do not send the needed header; the site uses no feature that needs cross-origin isolation | Section 5 |
| Strict-Transport-Security not set (10035) on some files | Low | Website | **False positive**: the site sends HSTS (`web/vercel.json`), and the whole `vercel.app` domain is on the browsers' HSTS preload list, so browsers never use plain HTTP for it | — |
| Client error response codes (100000) | Info | API | **Expected**: 401 without a token, 422 for invalid input, 429 when rate-limited, 404 for unknown ids. No 500 during the active attack | — |
| Non-storable content, cache-control (10049, 10015) | Info | API, website | **Intended**: API answers use `no-store` so personal data is never cached | — |
| Sec-Fetch-* header missing (90005) | Info | Both | **Not applicable**: these are headers sent by browsers in requests; ZAP's scanner does not send them | — |
| Authentication request identified (10111) | Info | API | Information only (login form found) | — |
| Information in browser localStorage (120000) | Info | Website | Only the chosen language (`fr`/`en`); tokens are never stored in the browser (ADR-0002) | — |
| Base64 disclosure, suspicious comments (10094, 10027) | Info | Website | **False positives**: Unicode tables and the word "query" in the minified React library | — |

## 4. Dependency audit

Run on 22 November 2026.

| Part | Tool | Result | Action |
|---|---|---|---|
| API (Python) | `pip-audit -r requirements.txt` (also in CI) | **No known vulnerabilities** | — |
| Website, shipped code | `npm audit --omit=dev` (CI blocks high) | **0 vulnerabilities** | — |
| Website, build and test tools | `npm audit` (CI blocks critical) | **0 vulnerabilities** | R-10 closed: the `picomatch` fix has shipped |
| Mobile app | `npm audit --omit=dev` | Before: 2 high (`zod`, `@expo/cli`), 8 moderate · **After `npm audit fix`: 0 high, 3 moderate** (R-1 reduced) | Lock file updated; tests, lint and type check pass. The 3 moderate ones (`minimatch` and `glob` inside Expo's build tools) need Expo SDK 59 (R-1) |
| Desktop app (.NET) | `dotnet list package --vulnerable --include-transitive` | Run by the developer before each release (section 7); NuGet packages are also watched by Dependabot | .NET 8 end of support (R-8) |
| Automatic updates | Dependabot (pip, npm, NuGet, GitHub Actions) | Weekly pull requests | Reviewed with the CI checks |

## 5. Residual and accepted risks

The full list, with plans, is in the threat model, section 5. Summary at release 1.0.0:

| ID | Risk | Level | Decision |
|---|---|---|---|
| R-1 | 3 moderate advisories in Expo build tools (`minimatch`, `glob`) | Low | Accepted: build-time tools on the developer's machine, not in the app; fixed by the next Expo SDK |
| R-2 | Demo hosting in the United States, not Québec | Low (fictional data) | Accepted for the demo; a real clinic needs a Law 25 transfer assessment |
| R-3 | Rate-limit counters in memory (reset on restart) | Low | Accepted with one instance; account lockout is stored in the database |
| R-4 | Refresh cookie `SameSite=None` (website and API on different sites) | Low | Accepted: httpOnly, Secure, limited path, CORS restricted |
| R-5 | Branch protection, CodeQL, secret scanning not enabled | Medium | Needs the repository owner; requested |
| R-6 | Free host sleeps when idle | Low (availability) | Accepted for the demo |
| R-7 | One signing key for all tokens | Low | Rotation procedure in the runbook |
| R-8 | .NET 8 support ends November 2026 | Low | Required by the course spec; upgrade path documented |
| R-9 | No email provider connected: emails are logged, not delivered | Low | Accepted for the demo |
| R-11 | No Cross-Origin-Embedder-Policy on the website | Low | Accepted: it would break Stripe's payment frames; no cross-origin isolation features used |
| R-12 | Active ZAP scan without login (authenticated routes only checked for refusal) | Low | Accepted: authorization of logged-in routes is covered by the automated tests (A01, A07) |

R-10 (`picomatch` in the website build tools) is **closed**: the fixed version is installed and
`npm audit` reports nothing.

## 6. Conclusion

No High finding in any scan, before or after. The one Medium finding (a permissive CORS
header on the website's static files) and two Low findings (missing Cross-Origin-Opener-Policy
and Cross-Origin-Resource-Policy) were fixed and **verified by the after scan**: the live API
and the attacked copy now have no finding above Informational, and the website only keeps one
accepted risk and one false positive. The remaining items are informational, false positives, or accepted risks with a
reason and a plan. Security controls for each OWASP Top 10 category are in place and backed by
automated tests that run on every pull request.

## 7. How to repeat this audit

1. GitHub → **Actions → security-scan → Run workflow**, label `before` or `after`
   (or `gh workflow run security-scan.yml -f label=after`).
2. Download the reports: `gh run download --dir zap-after`.
3. Dependencies: `pip-audit -r api/requirements.txt`; `npm audit` in `web` and `mobile`;
   `dotnet list desktop/CliniquePhysio.Desktop.sln package --vulnerable`.
