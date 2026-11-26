# Technical challenges — Project B (spec B.10)

Each challenge follows the same method: show the problem, fix it, prove the fix with an
automated test that runs in CI on every pull request, and explain it here.

| # | Challenge | Fix in one line | Proof (automated tests) |
|---|---|---|---|
| B-C1 | Double booking under concurrency | PostgreSQL exclusion constraint + per-therapist lock + clean 409 | `api/tests/test_double_booking.py` |
| B-C2 | Time zones and daylight saving time | Store UTC, compute and show in `America/Montreal`, 24 real hours | `test_slots.py`, `test_booking.py`, `web/src/utils/format.test.js` |
| B-C3 | IDOR and broken access control | Role + care relationship checked on every request; others' data answers 404 | `test_clinical.py`, `test_billing.py`, `test_booking.py` |
| B-C4 | Token storage and XSS | Access token in memory, refresh token in an httpOnly cookie, strict CSP, no raw HTML | `test_login.py`, `test_deploy_config.py`, `web/src/pages/pages.test.jsx`, `web/src/security.test.js` |
| B-C5 | Offline synchronization conflict | Offline actions queued in memory, sent to `POST /desk/sync`; the server's state wins | `api/tests/test_offline_sync.py`, `desktop/tests/…/OfflineSyncTests.cs` |
| B-C6 | Chatbot medical advice and prompt injection | Safety rules before the search, AI limited to the clinic's passages, output check | `api/tests/test_chatbot.py`, `api/eval/chatbot_eval.json` (64 questions) |
| B-C7 | Sensitive data in logs and emails | Masked emails, no bodies or notes logged, query strings removed from request logs | `api/tests/test_logs.py`, `test_notifications.py`, `test_chatbot.py` |

---

## B-C1 — Double booking under concurrency

**Problem.** Two patients click the same free time at the same moment. Each request checks
"is the slot free?", both see "yes", and both insert an appointment. A check in Python cannot
prevent this: the two checks run before either insert is committed.

**Fix.**

1. **The database refuses overlaps.** Table `appointments` has the exclusion constraint
   `ex_appointments_no_overlap`: for one therapist (`therapist_id WITH =`), two active
   appointments (`held`, `pending_payment`, `confirmed`, `checked_in`) can never have
   overlapping time ranges (`during WITH &&`, a `tstzrange`, GiST index). Even a bug in the API
   could not create a double booking (migration `0001_d1_core_tables.py`).
2. **The API answers cleanly.** `booking_service` catches the `ExclusionViolation` raised by
   PostgreSQL and turns it into `SlotUnavailable`, which the route returns as
   **409 Conflict** "this time is no longer available". Nothing of the refused request is kept.
3. **No deadlocks for users.** Bookings for one therapist take turns with a transaction lock
   (`app/db/locks.py`), and a rare deadlock is retried (`app/db/retry.py`), so the 29 losers
   get a clear "slot taken", not a server error.

**Proof.** `test_30_concurrent_bookings_only_one_succeeds`: 30 threads, each with its own
database connection, wait at a barrier and book the same slot at the same instant: exactly
**1 booked, 29 slot taken**. `test_the_database_alone_never_accepts_two_bookings` removes the
lock and the retry: still only 1 booking (the constraint alone holds).
`test_a_slot_already_held_gives_409` checks the 409 through the API, and
`test_cancelled_appointment_frees_the_slot` checks that a cancellation frees the time.

## B-C2 — Time zones and daylight saving time

**Problem.** Montréal changes time twice a year (first Sunday of November: 25-hour night;
second Sunday of March: 23-hour night). Mixing local and UTC times gives slots one hour off
after a change, a "24-hour" cancellation rule that is really 23 or 25 hours, and dates that
jump to tomorrow in the evening (UTC is 4 or 5 hours ahead).

**Fix.**

- Every moment is stored as `timestamptz` (UTC). Working hours are stored as local times
  (09:00) and converted for each date with `zoneinfo("America/Montreal")` (`app/services/slots.py`),
  so 10:00 stays 10:00 local on both sides of a change.
- The 24-hour rule compares real instants (UTC), so it is always 24 real hours.
- "Today" is the clinic's date (`today_local()`), never the server's UTC date.
- The API sends each time with its offset (`2026-11-02T10:00:00-05:00`); the website and the
  desktop show it as given, never in the computer's own time zone.

**Proof.** `test_slots.py`: `test_monday_10am_stays_10am_local_after_november_change`,
`…_after_march_change`, `test_night_of_november_change_has_25_hours_of_real_time`,
`test_night_of_march_change_has_one_hour_less`, `test_range_across_dst_change_keeps_local_times`.
`test_booking.py`: `test_24_hours_are_real_hours_across_the_november_change` (refund or not,
on each side of the change). Website `format.test.js`: 10:00 shown before and after the
November change, the clinic's date for late-evening slots, today's date when UTC is already
tomorrow. Lesson learned during D3: two tests failed only after 7 p.m. because they used the
server's date; they now use `today_local()`.

## B-C3 — IDOR and broken access control

**Problem.** Ids are in the URLs (`/appointments/{id}/receipt`, `/patients/{id}/notes`).
Changing the id must never show someone else's data, whatever the role.

**Fix.**

- Every route declares the roles it accepts (`FrontDeskUser`, `CurrentPatient`, therapist,
  admin with MFA) in `app/dependencies.py`.
- A therapist reads a patient file only with a **care relationship**: an appointment with
  that patient that is not cancelled or expired (`app/services/clinical_service.py`).
- The front desk and the administrator **never** reach clinical notes, even with MFA.
- A patient's request is always filtered by their own patient id. Another patient's
  appointment or receipt answers **404**, exactly like a missing one, so ids cannot be probed.
- Every read of a patient file is written in the append-only audit log.

**Proof.** `test_clinical.py`: `test_therapist_without_care_relationship_cannot_read_a_note`
(therapist A, B's patient), `test_front_desk_and_admin_never_reach_clinical_notes`,
`test_cancelled_or_expired_appointments_give_no_access`. `test_billing.py`:
`test_no_receipt_for_another_patients_appointment` (404) and
`test_patients_and_therapists_cannot_record_payments`. `test_booking.py`:
`test_patients_cannot_cancel_someone_elses_appointment` and `…_reschedule_someone_elses_appointment`. The ZAP active scan found no access-control issue
([security audit](security/security-audit.md)).

## B-C4 — Token storage and XSS

**Problem.** If JavaScript injected into the page (XSS) can read the login token, the attacker
becomes the user. `localStorage` is readable by any script on the page.

**Choice and justification.**

| Option | XSS can steal it? | CSRF risk | Used for |
|---|---|---|---|
| `localStorage` | Yes, any script reads it | No | Nothing (only the language) |
| Memory (a JavaScript variable) | Only while the page is open, never stored | No | The **access token** (10 minutes) |
| httpOnly cookie | No, JavaScript cannot read it | Yes, so it is limited | The **refresh token** (7 days, rotated at each use) |

The refresh cookie is `HttpOnly`, `Secure`, `SameSite`, limited to the refresh path, and
rotated on each use (a reused one revokes the whole family). The access token lives only in
memory (`web/src/auth/AuthContext.jsx`); a page reload gets a new one through the cookie.

**Defences against XSS.**

1. React writes data as text; the code never uses `dangerouslySetInnerHTML` or `innerHTML`.
2. Content-Security-Policy on every page (`web/vercel.json`): `script-src 'self'` plus Stripe
   only, no `'unsafe-inline'`, no `'unsafe-eval'`, `object-src 'none'`,
   `frame-ancestors 'none'`, `base-uri 'self'`. Even an injected `<script>` would not run.
3. The API returns JSON only, with `X-Content-Type-Options: nosniff`.

**Proof.** `pages.test.jsx` — "displays API text as text, never as HTML": a service named
`<img src=x onerror=alert(1)>` is shown as those characters and no image element is created.
`security.test.js` fails if `dangerouslySetInnerHTML`, `innerHTML` or a token in browser
storage ever appears in the website's code. `test_deploy_config.py` —
`test_website_csp_only_runs_scripts_from_known_places` checks the CSP rules above, and
`test_security_headers_on_every_response` the API's headers. `test_login.py`:
`test_login_returns_access_token_and_httponly_refresh_cookie`,
`test_refresh_gives_new_tokens_and_old_refresh_token_stops_working` and
`test_reusing_an_old_refresh_token_cancels_all_sessions`.

## B-C5 — Offline synchronization conflict (desktop)

**Problem.** The front desk loses the connection. Marie Gagnon is at the desk, so the agent
clicks **Check-in**. Meanwhile, Marie had cancelled online from her phone. When the connection
returns, which is true?

**Fix.**

1. **Offline, the desk keeps working.** When the API cannot be reached, a check-in or no-show
   is kept in a queue (`OfflineQueue`) with the status the agent saw (`confirmed`) and the time
   of the click. The card shows "Waiting to be sent (offline)" and its buttons disappear (no
   double click); a banner shows how many actions wait and a **Send now** button. The day
   already on screen stays visible.
2. **No patient data on the computer.** The queue lives in memory only: nothing is written to
   disk. Closing the app or logging out with actions waiting asks for confirmation first.
   Only ids, the action, the seen status and the time are sent; the patient's name stays on
   screen.
3. **Synchronization.** Before the next reload, or with **Send now**, the app sends the queue
   to `POST /api/v1/desk/sync` (front desk with MFA). The server handles the actions in the
   order they were done.
4. **The documented rule: the server's state wins.** An offline action is applied only if
   the appointment is still in the status the agent saw. If it changed meanwhile (cancelled
   online, cancelled by the clinic, already handled by a colleague), the action is **not**
   applied; the result is a **conflict** with the current status. The time rules still apply
   at the moment of the click (check-in only on the day, no-show 15 minutes after the start);
   an action older than 12 hours is refused.
5. **Reported and audited.** The desk sees: "Conflict for Marie Gagnon: the appointment is now
   'Cancelled (patient)' (changed while you were offline). Your action was not recorded;
   check with the patient." Every conflict is written in the audit log (`sync_conflict`), and
   the day is reloaded to show the server's real state.

Why this rule: a cancellation made by the patient is a decision the clinic must respect (it
may have triggered a refund and freed the slot for someone else); the agent who is with the
patient can rebook in seconds, while silently undoing a cancellation could double-book the
time.

**Proof.** `api/tests/test_offline_sync.py`:
`test_patient_cancels_online_while_the_desk_checks_in_offline` (the scenario end to end through
the API: conflict, status stays cancelled, audit entry), `…_applied_when_nothing_changed`,
`test_sending_the_same_actions_twice_does_nothing_more`,
`test_time_rules_still_apply_at_the_moment_of_the_click`,
`test_actions_are_applied_in_the_order_they_were_done`, `test_an_action_older_than_12_hours_is_refused`,
`test_only_the_desk_can_send_offline_actions`. Desktop `OfflineSyncTests.cs`: the action is
queued and shown as waiting, the conflict message after the patient cancelled, the queue sent
before the next reload, still offline keeps the queue, logout asks first, and the request
never contains the patient's name.

**Limits.** Only check-ins and no-shows work offline; booking, moving, cancelling and payments
need the connection (they depend on live availability and Stripe). A day that was not loaded
before the outage cannot be shown, because nothing is cached on disk, by choice.

## B-C6 — Chatbot drift into medical advice and prompt injection

**Problem.** A chatbot built on a language model can be pushed into giving a diagnosis or a
dose, or into ignoring its rules ("ignore your instructions…"), and could miss an emergency.

**Fix.** Safety rules run **before** any search or AI call (`app/chatbot/safety.py`), in French
and English: emergencies get 911 / 811 / 9-8-8 only; diagnosis, treatment, exercise or dose
requests are refused; prompt injections and questions about another person are refused. The
AI only rewrites the clinic's own passages, treats the question as data, must cite a passage,
and its answer is checked again before it is shown; otherwise the passage is shown as written.

**Proof.** 64-question evaluation set (`api/eval/chatbot_eval.json`): 40 base questions and
**24 adversarial** ones (8 injections, 4 data-fishing, 4 disguised medical questions, 3
unusual emergencies, off-topic and personal-details questions). Results: **100%** of
emergencies (6/6), diagnosis and treatment requests (10/10), injections (10/10) and questions
about a person (5/5) handled safely; v2 64/64 overall. CI runs the set on every pull request
and fails if any emergency or medical request is not handled safely
(`test_evaluation_set_meets_the_targets`). Details, before/after and limits:
[rag-v2-evaluation.md](rag-v2-evaluation.md).

## B-C7 — Sensitive data in logs, emails and notifications

**Problem.** Logs are read by more people than patient files (hosting dashboards, support),
are kept longer, and are rarely encrypted. A careless `print(request)` puts emails, phone
numbers or notes in them.

**Fix.**

- The application logs events, not data: "email queued to=m***@example.com subject=…", never
  the body (`app/services/email.py`).
- Clinical notes are encrypted in the database and never logged; errors return generic
  messages.
- The chatbot masks emails, phone numbers, health insurance numbers, card numbers and postal
  codes before logging or sending the question to OpenAI.
- **Found during this check:** uvicorn's request lines (Render's log) contained the front
  desk's patient searches (`GET /desk/patients?q=514-555-0142`). A logging filter now replaces
  every query string with `?…` (`app/core/logging.py`).
- Emails contain practical details only (date, time, address, what to bring), never the
  service's clinical reason or notes. There are no reminders yet (no email provider); the
  same rule will apply to them.

**Proof.** `test_logs.py` — `test_no_personal_or_clinical_data_in_any_log`: a journey
(registration with email, phone and emergency contact; a SOAP note written and read; a chatbot
question containing an email and a phone) with **every logger at DEBUG level** captured; none
of those values appears, while "email queued" does. `test_request_lines_hide_the_query_string`
and `test_the_filter_is_installed_on_uvicorns_request_log` for the request log.
`test_notifications.py` — `test_confirmation_has_practical_details_only` and
`test_queued_emails_appear_in_the_server_log_without_the_address`. `test_chatbot.py` — the
masking tests.

---

## How to run every proof

```
cd api && pytest -q                         # all API tests (needs the local database)
cd web && npm test -- --run                 # website tests
cd desktop && dotnet test                   # desktop tests
cd api && python scripts/eval_chatbot.py    # chatbot evaluation (B-C6)
```

All of them also run in GitHub Actions on every pull request.
