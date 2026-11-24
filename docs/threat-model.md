# Threat model — Clinique Physio Mont-Royal

Status: **D3 (v1.0.0)**.
Method: STRIDE (Spoofing, Tampering, Repudiation, Information disclosure, Denial of service,
Elevation of privilege), applied to each main data flow.
Companion document: [data-classification.md](data-classification.md).

Every mitigation is marked:

- ✅ **Implemented**, with the automated test that proves it (in `api/tests/` unless stated).
- ⏳ **Planned**, with the deliverable where it is due (D2 or D3).

## 1. What we protect (assets)

| Asset | Why it matters |
|---|---|
| Clinical notes and exercise programs | Health information: the most sensitive category under Law 25. A leak harms patients and the clinic. |
| Patient identity and contact data | Name, date of birth, phone, email, emergency contact: personal information under Law 25. |
| Appointment schedule | Reveals who is a patient of the clinic and when. Its integrity is the clinic's business (no double booking). |
| Staff accounts (therapist, front desk, admin) | Give access to many patients at once: the highest-value target for an attacker. |
| Secrets (JWT secret, encryption key, database password) | Whoever has them can forge sessions or read encrypted data. |
| Payments (D2) | Deposits and refunds through Stripe; card data never reaches our systems. |
| Audit trail (D2) | Proof of who accessed which patient file; must not be altered. |

## 2. Actors and trust

| Actor | Trust | Notes |
|---|---|---|
| Visitor (anonymous) | None | Can read public pages and free slots, register. |
| Patient | Low | Only their own data. |
| Physiotherapist | Medium | Only their own patients (care relationship), with MFA. |
| Front desk | Medium | All schedules, no clinical notes, with MFA. |
| Clinic administrator | High | Administration and compliance, no clinical notes by default, with MFA. |
| External attacker | Hostile | Anywhere on the Internet. |
| Malicious or curious insider | Hostile | A staff member or patient trying to see more than they should. |
| Stripe, email provider, LLM provider (D2) | Partly trusted | External services; their inputs are verified (e.g. signed webhooks). |

## 3. Data flows and trust boundaries

```mermaid
flowchart LR
    subgraph Untrusted["Untrusted zone: user devices and the Internet"]
        V([Visitor / patient browser])
        M([Patient phone: mobile app])
        D([Front-desk PC: desktop app])
        A([Attacker])
    end

    subgraph Vercel["Vercel"]
        W[Website: static React files]
    end

    subgraph Render["Render: trusted application zone"]
        API[REST API /api/v1<br/>auth, rules, permissions]
    end

    subgraph Neon["Neon: data zone"]
        DB[(PostgreSQL 16)]
    end

    subgraph External["External services (D2)"]
        S[Stripe]
        E[Email provider]
        L[LLM provider]
    end

    V -- "HTTPS: pages" --> W
    V -- "HTTPS + token" --> API
    M -- "HTTPS + token" --> API
    D -- "HTTPS + token" --> API
    A -. "attacks" .-> API
    API -- "TLS, sslmode=require" --> DB
    S -- "signed webhook" --> API
    API -- "HTTPS" --> E
    API -- "HTTPS, no patient data" --> L
```

| # | Trust boundary | What crosses it | Main control |
|---|---|---|---|
| TB1 | User device → API | Every request from the three clients | TLS; token checked on every request; input validated by Pydantic schemas; rate limits |
| TB2 | API → database | SQL queries and results | TLS to Neon; parameterized queries (SQLAlchemy); credentials only in environment variables |
| TB3 | Browser → website | Static files | HTTPS; Content-Security-Policy and security headers (`web/vercel.json`) |
| TB4 | External services ↔ API (D2) | Webhooks, emails, chatbot prompts | Signature checks (Stripe); no clinical data in emails or prompts |
| TB5 | Developer → repository → hosting | Code and configuration | Pull requests with CI checks; secrets never in the repository |

## 4. STRIDE analysis

### 4.1 Authentication: login, MFA, session refresh

| ID | STRIDE | Threat | Mitigation | Req. | Status |
|---|---|---|---|---|---|
| T-AUTH-1 | S | Password guessing (brute force, credential stuffing) | Rate limit 5 login attempts per minute per IP; account locked 15 minutes after 5 failures; owner notified by email | B-AUTH-06, NFR-05 | ✅ `test_brute_force.py` |
| T-AUTH-2 | S | Stolen staff password used alone | Mandatory TOTP code for every staff role; staff endpoints refuse tokens without `mfa: true` | B-AUTH-04 | ✅ `test_mfa.py` |
| T-AUTH-3 | S | A 6-digit code is observed and replayed | Each TOTP time step can be used only once (`mfa_last_used_step`) | B-AUTH-04 | ✅ `test_a_code_cannot_be_used_twice` |
| T-AUTH-4 | I | Finding which emails have an account (user enumeration) | Same answer for "wrong password" and "unknown email", same timing (dummy hash); registration answers the same for new and existing emails; lockout answer identical to a wrong password | B-AUTH-03 | ✅ `test_wrong_password_and_unknown_email_get_the_same_answer`, `test_existing_email_gets_same_answer_and_no_second_account`, `test_locked_answer_looks_exactly_like_a_wrong_password` |
| T-AUTH-5 | I | Database leak reveals passwords | Argon2id hashing (memory-hard); passwords of at least 12 characters, not containing the email | NFR-02, B-AUTH-03 | ✅ `test_password_is_stored_as_argon2id_hash`, `test_weak_passwords_are_refused` |
| T-AUTH-6 | I | Database leak reveals MFA secrets | MFA secrets encrypted (Fernet: AES with HMAC) with a key kept outside the database | B-AUTH-04 | ✅ `test_first_login_enrolment_then_session_with_mfa` |
| T-AUTH-7 | S | Stolen access token reused | Access token lasts 10 minutes; signed (HS256), purpose-bound (an email or MFA ticket cannot be used as an access token) | B-AUTH-02 | ✅ `test_access_token_lasts_at_most_10_minutes`, `test_other_token_types_are_refused_as_access_token` |
| T-AUTH-8 | S | Stolen refresh token reused | Refresh token in an httpOnly cookie (not readable by JavaScript), only sent to `/api/v1/auth`; stored as a SHA-256 hash; rotated at each use; reuse of an old token cancels every session of the user | B-AUTH-02, B-C4 | ✅ `test_refresh_gives_new_tokens_and_old_refresh_token_stops_working`, `test_reusing_an_old_refresh_token_cancels_all_sessions` |
| T-AUTH-9 | S | Unattended staff workstation | Staff sessions expire after 15 minutes without activity (server-side refresh lifetime) | B-AUTH-02 | ✅ `test_staff_session_expires_after_15_minutes_of_inactivity` · ⏳ desktop auto-lock screen (D3) |
| T-AUTH-10 | E | A patient makes themself admin at registration | The role is never taken from the request; registration always creates a patient | B-AUTH-01 | ✅ `test_role_cannot_be_chosen_by_the_client` |
| T-AUTH-11 | E | A forged or modified token claims a higher role | Role read from the database on every request, not trusted from the token | B-AUTH-05 | ✅ `test_staff_endpoint_refuses_patients_even_with_mfa_claim` |
| T-AUTH-12 | S | MFA set up again by someone who only knows the password | Enrolment is refused once MFA is active | B-AUTH-04 | ✅ `test_enrolment_cannot_be_restarted_with_only_a_password` |
| T-AUTH-13 | T | Cross-site request (CSRF) on `/auth/refresh` or `/auth/logout` | Cookie limited to the auth path; CORS allows only the clinic's website, so another site cannot read the new token | NFR-03 | ✅ CORS test `test_cors_allows_the_web_app_and_refuses_other_sites` · ⏳ Origin header check on auth endpoints (D2), see residual risk R-4 |
| T-AUTH-15 | S | Account takeover through the password reset | Reset link is a 256-bit random value stored as a SHA-256 hash; single use; expires after 30 minutes; a new request cancels older links; all sessions cancelled after a reset; owner told by email; staff still need their MFA code; 5 requests per minute per IP | B-AUTH-03 | ✅ `test_password_reset.py` |
| T-AUTH-16 | I | Finding which emails have an account through "forgot password" | Same answer and status for known and unknown emails; the email is sent after the answer (background task), so response time reveals nothing | B-AUTH-03 | ✅ `test_same_answer_whether_or_not_the_account_exists` |
| T-AUTH-14 | R | A user denies having logged in | `last_login_at` recorded | B-CLN-04 | ✅ partial · ⏳ full audit log (D2) |

### 4.2 Booking and availability

| ID | STRIDE | Threat | Mitigation | Req. | Status |
|---|---|---|---|---|---|
| T-BKG-1 | T | Two patients book the same slot at the same moment (race condition) | PostgreSQL exclusion constraint on (therapist, time range) for active statuses: the database refuses the second booking; competing bookings for one therapist take turns (transaction lock) so losers get a clear refusal, not a deadlock (ADR-001) | B-BKG-02, B-C1 | ✅ `test_30_concurrent_bookings_only_one_succeeds`, `test_the_database_alone_never_accepts_two_bookings`, `test_race_lost_at_the_database_gives_409` |
| T-BKG-2 | T | Wrong times around daylight saving changes (booking at the wrong hour, wrong 24 h cancellation rule) | Times stored in UTC (`timestamptz`); schedules defined in clinic local time and converted per date | B-BKG-07, B-C2 | ✅ `test_slots.py` (November and March changes) · ✅ `test_24_hours_are_real_hours_across_the_november_change` |
| T-BKG-3 | D | Requests for huge date ranges overload the API | Searches limited to 31 days, at most 60 days ahead; lists limited (e.g. 50 appointments) | NFR-07 | ✅ `test_invalid_ranges_are_refused`, `test_no_slots_more_than_60_days_ahead` |
| T-BKG-4 | E | A therapist deletes another therapist's time off (IDOR) | Ownership checked in the database query; unknown or foreign id answers 404, revealing nothing | B-C3 | ✅ `test_therapist_cannot_delete_another_therapists_time_off` |
| T-BKG-5 | S/T | Slots held forever to block the schedule | 10-minute hold, then status `expired`; a new hold replaces the patient's unpaid one (one slot at a time); 20 booking requests per minute per IP | B-BKG-03 | ✅ `test_expired_hold_does_not_block_but_active_hold_does`, `test_an_expired_hold_frees_the_slot`, `test_a_new_hold_replaces_the_patients_previous_hold` |
| T-BKG-6 | T/R | Fake payment confirmation; webhook replayed | Stripe signature and timestamp verified before anything is read (ADR-007); each event applied once (unique `stripe_event_id`); the appointment is confirmed only by the webhook, never by the browser; a payment after the hold expired is refunded automatically | B-BKG-04 | ✅ `test_a_fake_or_altered_webhook_is_refused`, `test_the_same_event_twice_is_applied_once`, `test_payment_after_the_hold_expired_is_refunded` |
| T-BKG-8 | E | A patient cancels or moves another patient's appointment (IDOR) | Every change looks the appointment up by id **and** the logged-in patient; otherwise 404, revealing nothing | B-C3 | ✅ `test_patients_cannot_cancel_someone_elses_appointment`, `test_patients_cannot_reschedule_someone_elses_appointment` |
| T-BKG-7 | R | Who changed an appointment's status is unknown | Status history table with the actor and a reason; rows only added | B-BKG-05 | ✅ `test_booking.py` (history checked on hold, cancel, reschedule, expiry) |

### 4.3 Patient data and clinical file

| ID | STRIDE | Threat | Mitigation | Req. | Status |
|---|---|---|---|---|---|
| T-CLN-1 | I/E | A patient reads another patient's appointments by changing an id (IDOR) | Patient endpoints never take a patient id: the query is always filtered by the logged-in patient | B-C3 | ✅ `test_patient_never_sees_another_patients_appointments` |
| T-CLN-2 | I | Front desk sees clinical information | Front-desk schedule returns only name, phone, service and status | B-CLN-05 | ✅ `test_schedule_contains_no_clinical_or_account_data` · ✅ `test_front_desk_and_admin_never_reach_clinical_notes` |
| T-CLN-3 | I | A therapist reads notes of patients they do not treat | Care relationship check: at least one confirmed, checked-in or completed appointment with that therapist; otherwise 404 (same as unknown) and the attempt is audited | B-AUTH-05, B-C3 | ✅ `test_therapist_without_care_relationship_cannot_read_a_note`, `test_cancelled_or_expired_appointments_give_no_access` |
| T-CLN-4 | I | Database leak exposes clinical notes or emergency contacts | Field-level encryption with a key outside the database | B-CLN-02 | ✅ emergency contact (`test_emergency_contact_is_encrypted`) · ✅ notes (`test_note_content_is_encrypted_in_the_database`) |
| T-CLN-5 | T/R | A note is changed or deleted after the fact | Notes locked after signature and never deleted, enforced by a database trigger (not only the API); corrections are signed amendments that keep the original | B-CLN-03, BR-B-07 | ✅ `test_database_refuses_changing_a_signed_note_or_deleting_any_note`, `test_amendment_keeps_the_original` |
| T-CLN-6 | R | Access to a file cannot be traced | Audit log of every read, write, signature and refused attempt, written in the same transaction as the action; a database trigger refuses any change or deletion of audit rows | B-CLN-04 | ✅ `test_database_refuses_changing_or_deleting_audit_entries`, `test_listing_a_patients_notes_audits_each_note` |
| T-CLN-7 | I | Personal data in logs, emails or notifications | Email addresses masked in logs (`c***@example.com`); reminders contain no clinical data | B-C7, BR-B-08 | ✅ masking in `app/services/email.py` · ⏳ log tests and reminders (D3) |

### 4.4 Client applications

| ID | STRIDE | Threat | Mitigation | Req. | Status |
|---|---|---|---|---|---|
| T-CLI-1 | I/E | Cross-site scripting (XSS) on the website steals a session | React escapes text; strict Content-Security-Policy (`script-src 'self'`); refresh token not readable by JavaScript | B-C4, NFR-03 | ✅ `web/src/pages/pages.test.jsx` (API text shown as text, not run) · CSP in `web/vercel.json` |
| T-CLI-2 | I | Clickjacking (site shown inside another site) | `X-Frame-Options: DENY`, `frame-ancestors 'none'` | NFR-03 | ✅ `test_security_headers_on_every_response` |
| T-CLI-3 | I | Token stolen from a lost phone | Token in the phone's secure storage (Keychain / Keystore), 10-minute lifetime | B.8.2 | ✅ `mobile/src/tokenStore.ts` |
| T-CLI-4 | I | Token stolen from the front-desk PC | Desktop token kept in memory only, never written to disk | B.8.3 | ✅ `desktop/.../Session.cs` · ⏳ encrypted offline cache (D3, B-FRD-06) |
| T-CLI-5 | I | Traffic intercepted on public Wi-Fi | HTTPS only; HSTS on the API and website | NFR-03 | ✅ `test_security_headers_on_every_response` (HSTS in production) |
| T-CLI-6 | E | Another website calls the API with the user's browser | CORS limited to the clinic's website | NFR-03 | ✅ `test_cors_allows_the_web_app_and_refuses_other_sites` |

### 4.5 Infrastructure, code and supply chain

| ID | STRIDE | Threat | Mitigation | Req. | Status |
|---|---|---|---|---|---|
| T-INF-1 | I | Secrets committed to the repository | `.env` ignored by Git; `.env.example` holds only placeholders; production secrets in the host's settings | NFR-02 | ✅ `.gitignore` · ⏳ GitHub secret scanning (needs repository admin) |
| T-INF-2 | T | SQL injection | All queries through SQLAlchemy with bound parameters; no SQL built from strings | OWASP A03 | ✅ Bandit in `api-ci` |
| T-INF-3 | T | Vulnerable dependency | pip-audit and npm audit in CI; Dependabot weekly | OWASP A06 | ✅ `api-ci`, `web-ci`, `.github/dependabot.yml` · ⏳ CodeQL (needs repository admin or a public repository) |
| T-INF-4 | T | Unreviewed code reaches production | Pull requests with green CI before merge | spec 7.1 | ✅ practice · ⏳ branch protection enforced (needs repository admin) |
| T-INF-5 | D | API flooded with requests | Rate limits on authentication endpoints; host platform limits | NFR-05 | ✅ partial (see R-3) |
| T-INF-6 | I | Detailed errors reveal internals | Generic error messages to clients; validation errors without stack traces | OWASP A05 | ✅ |

### 4.6 Chatbot (ADR-0008)

| ID | STRIDE | Threat | Mitigation | Req. | Status |
|---|---|---|---|---|---|
| T-BOT-1 | E | Prompt injection: the visitor tries to change the bot's rules or make it reveal them | Injection patterns refused before any AI call; rules in the system message; question and passages sent as marked data, tags cannot be closed; AI answer accepted only if it cites a given passage and passes the safety rules again | B-BOT-03 | ✅ `test_prompt_injection_is_refused_and_nothing_is_revealed`, `test_question_cannot_close_the_data_tags`, `test_unsafe_or_ungrounded_ai_answers_fall_back_to_the_passage` |
| T-BOT-2 | I | The bot reveals patient data | No access to any patient table; questions about a person or a file refused | B-BOT-03, BR-8 | ✅ `test_questions_about_people_or_files_are_refused` |
| T-BOT-3 | I | Personal or health details typed by the visitor are kept or sent to the AI provider | Emails, phones, health insurance, card numbers and postal codes masked before logging and before OpenAI; log deleted after 30 days | Law 25 | ✅ `test_personal_details_are_masked`, `test_provider_gets_only_the_masked_question_and_public_passages`, `test_conversations_older_than_30_days_are_deleted` |
| T-BOT-4 | T | Harmful answer: diagnosis, treatment advice, or a missed emergency | Fixed rules before search: emergencies get only 911 / 811 / 9-8-8, medical requests refused; never generated | B-BOT-02 | ✅ evaluation set in CI (100% required) and 27 extra phrasings in tests |
| T-BOT-5 | T | Wrong or invented answer (hallucination) | Answers only from clinic passages; below a minimum score the bot says it does not know | B-BOT-01 | ✅ `test_question_outside_the_documents_gets_i_dont_know_not_a_guess` |
| T-BOT-6 | D | Flooding the chat to run up the AI bill | 10 questions per minute per IP; questions limited to 500 characters; answers capped at 400 tokens | NFR-05 | ✅ `test_chat_is_rate_limited_per_ip` |
| T-BOT-7 | I | OpenAI key leaked | Key only in `.env` and Render settings; never sent to the browser; errors log only their type | NFR-02 | ✅ `test_provider_errors_never_reveal_the_key_or_the_question` |

### 4.7 Administration (B-ADM-01, B-ADM-03)

| ID | STRIDE | Threat | Mitigation | Req. | Status |
|---|---|---|---|---|---|
| T-ADM-1 | E | A non-admin (or an admin without MFA) changes services or accounts | Every `/admin` endpoint requires the admin role read from the database and an MFA session | B-AUTH-04 | ✅ `test_only_administrators_use_the_admin_pages`, `test_admin_needs_the_two_factor_session` |
| T-ADM-2 | E | Privilege escalation: creating a new administrator through the API | Only therapist and front-desk accounts can be created (schema and service); admins cannot deactivate themselves or another admin | — | ✅ `test_invalid_staff_accounts_are_refused`, `test_service_layer_also_refuses_new_administrators`, `test_admin_cannot_deactivate_itself_or_another_admin` |
| T-ADM-3 | I | The administrator knows a staff member's password | New accounts get a random unusable password and a one-time link (72 h, only its hash stored); MFA still set up at the first login | B-AUTH-03, 04 | ✅ `test_new_therapist_gets_an_invitation_never_a_password`, `test_invited_staff_chooses_a_password_then_still_needs_mfa` |
| T-ADM-4 | S | A departed employee keeps using an open session | Deactivation revokes refresh tokens at once; access tokens are refused because the account is checked on each request | B-AUTH-02 | ✅ `test_deactivating_closes_sessions_and_hides_the_therapist` |
| T-ADM-5 | R | Abuse of access to patient files goes unnoticed | Audit viewer with filters; refused accesses and more than 10 different patients read in an hour are highlighted; reading the log is itself logged; entries cannot be changed (trigger) | B-ADM-03, B-CLN-04 | ✅ `test_many_patient_files_in_one_hour_are_highlighted`, `test_reading_the_audit_log_is_itself_logged` |

### 4.8 Law 25: privacy requests and incidents (B-ADM-04, B-ADM-05)

| ID | STRIDE | Threat | Mitigation | Req. | Status |
|---|---|---|---|---|---|
| T-L25-1 | I | A patient sees another patient's requests | `/me/privacy-requests` lists only the logged-in patient's own requests | B-AUTH-05 | ✅ `test_patients_see_only_their_own_requests` |
| T-L25-2 | I | Clinical notes reach the administrator through an access export | The export contains account, profile, consents, appointments and payments only; the clinical record is given by the treating physiotherapist (BR-6) | B-ADM-04, BR-6 | ✅ `test_export_for_an_access_request_has_no_clinical_notes` |
| T-L25-3 | R | A deletion destroys health records the clinic must keep, or keeps more than needed | Erasure closes the account and erases contact details at once; the health record is kept until the end of retention with the reason written; a patient without record is fully anonymized | B-ADM-04 | ✅ `test_deletion_keeps_the_health_record_with_the_reason`, `test_deletion_without_health_record_anonymizes_everything` |
| T-L25-4 | T | Incident register entries are removed to hide an incident | No delete endpoint, and a database trigger refuses any deletion; every change is in the audit log | B-ADM-05 | ✅ `test_incident_entries_can_never_be_deleted` |
| T-L25-5 | R | A serious incident is never reported | Entries with a risk of serious injury show the missing notifications until their dates are recorded | B-ADM-05 | ✅ `test_record_an_incident_and_see_missing_notifications` |

### 4.9 Desk payments, receipts, reports and photos (B-FRD-05, B-BKG-10, B-ADM-02, B-AVL-05)

| ID | STRIDE | Threat | Mitigation | Req. | Status |
|---|---|---|---|---|---|
| T-PAY-1 | T | The desk app (or a changed copy of it) records a wrong amount | The app sends only the method; the server computes the balance (price minus what was paid) and refuses a second payment | B-FRD-05 | ✅ `test_an_amount_sent_by_the_client_is_ignored`, `test_the_balance_is_paid_once` |
| T-PAY-2 | R | A desk agent denies recording a payment | Each desk payment keeps who recorded it, and an audit log entry is written | B-FRD-05 | ✅ `test_desk_records_the_balance_computed_by_the_server` |
| T-PAY-3 | I | A patient downloads another patient's receipt | `/appointments/{id}/receipt` checks ownership and answers 404 for another patient's appointment; every download is logged | B-BKG-10, B-AUTH-05 | ✅ `test_no_receipt_for_another_patients_appointment` |
| T-PAY-4 | I | A receipt reveals health information or stays in a shared cache | The receipt has practical details only (service, date, amounts, licence number), no notes; sent with `Cache-Control: no-store`; the desktop app saves it in the user's own temporary folder | B-BKG-10, NFR-02 | ✅ `test_patient_downloads_a_pdf_receipt` |
| T-PAY-5 | I | Reports expose patients | Reports hold counts and totals only, for administrators with MFA | B-ADM-02 | ✅ `test_admin_reads_the_report_without_patient_names`, `test_other_roles_cannot_read_reports` |
| T-PHO-1 | T/E | An uploaded "photo" carries a script, a second file or a decompression bomb | Only JPEG, PNG or WebP; size and pixel limits; the image is decoded and re-encoded as a new JPEG, never stored as uploaded; served as `image/jpeg` with `nosniff` | B-AVL-05 | ✅ `test_files_that_are_not_valid_images_are_refused`, `test_wrong_content_type_is_refused` |
| T-PHO-2 | I | A photo reveals where it was taken (GPS) or the camera | Metadata (EXIF) is dropped by the re-encoding | B-AVL-05 | ✅ `test_location_and_camera_details_are_removed` |
| T-PHO-3 | E | Someone other than the administrator changes a photo | Upload and removal need an administrator with MFA; every change is in the audit log | B-AVL-05 | ✅ `test_only_the_administrator_changes_photos` |
| T-PAY-6 | S | A receipt is taken for a real clinic's official document | Every receipt says it comes from a fictional clinic made for a student project | B-BKG-10 | ✅ `test_receipt_text_has_the_insurer_details` |

## 5. Residual and accepted risks

The D3 security audit ([security/security-audit.md](security/security-audit.md)) checks every OWASP Top 10 category and records the ZAP scans before and after the fixes.

| ID | Risk | Why accepted (for now) | Plan |
|---|---|---|---|
| R-1 | 3 moderate advisories (`minimatch`, `glob`) in Expo's build tools; the former high ones (`zod`, `@expo/cli`) were fixed with `npm audit fix` in D3 | Build-time tools on the developer's machine, not shipped in the app; the rest needs a newer Expo SDK | Update Expo when the next SDK is allowed |
| R-2 | Demo hosting (Render, Neon) is in the United States, not Québec | All data is fictional; a real deployment would need a Law 25 assessment for transfers outside Québec | Documented; out of scope for the student project |
| R-3 | Rate-limit counters are kept in the API's memory: they reset on restart and are not shared between instances | One instance on the free plan; lockout (stored in the database) still protects each account | Shared store (e.g. Redis) if the API ever runs on several instances |
| R-4 | Refresh cookie is `SameSite=None` in production because the website and the API are on different sites | Cookie is httpOnly, Secure, limited to `/api/v1/auth`; CORS stops other sites from reading tokens; worst case of a forged request is an unwanted logout or token rotation | Check the `Origin` header on auth endpoints (D2), or serve the API under the website's domain |
| R-5 | Branch protection, CodeQL and secret scanning are not enabled | They need repository admin rights or a public repository | Requested from the repository owner |
| R-6 | The free API host sleeps after inactivity (first request can take about a minute) | Availability, not confidentiality; acceptable for a demo | Paid plan for a real deployment |
| R-7 | Single signing key (HS256) shared by all tokens | Simple and safe while only the API issues and verifies tokens | Key rotation procedure in the D3 runbook |
| R-8 | .NET 8 reaches end of support in November 2026; ESLint 9 is deprecated | No known vulnerability; the spec requires .NET 8; ESLint 10 not yet supported by the React plugins | Upgrade when allowed and supported |
| R-9 | No email provider is connected yet: in production, account confirmation, password reset, staff invitation and booking emails are only logged (with a masked address), not delivered | Demo accounts are already confirmed; the flows are proven by automated tests and shown locally, where the email is printed in the API console | Connect a transactional email provider (planned with reminders, B-BKG-08) |
| R-10 | ~~`picomatch` advisory in the website build tools~~ **Closed in D3**: the fixed version is installed and `npm audit` reports nothing | — | — |
| R-11 | No Cross-Origin-Embedder-Policy on the website (ZAP Low) | `require-corp` would block Stripe's payment frames; the site uses no feature that needs cross-origin isolation | Revisit if Stripe supports it |
| R-12 | The ZAP active scan runs without login, so logged-in routes are only checked for refusal | Authorization of logged-in routes is covered by the automated tests (security audit, A01 and A07) | Add an authenticated ZAP context if the project continues |

## 6. Review

This model is reviewed at each deliverable: new flows (booking with payment, clinical notes,
chatbot, offline desktop mode) are added at D2 and D3, and every ⏳ line must become ✅ or be
moved to the residual risks with a reason.
