# Vision and requirements — Clinique Physio Mont-Royal

Status: **D1 (v0.1.0)**. Related documents: [architecture.md](architecture.md),
[erd.md](erd.md), [threat-model.md](threat-model.md),
[data-classification.md](data-classification.md).

The backlog below is generated from [backlog.json](backlog.json). Each user story is a GitHub
issue (label `user-story`, milestone D1, D2 or D3). To change a story, edit the issue on GitHub;
to add stories, add them to `backlog.json` and run `python scripts/create_backlog.py`.

## 1. Context

Clinique Physio Mont-Royal is a (fictional) physiotherapy clinic in Montréal with six
physiotherapists, a front desk and an administrator. Today, appointments are taken by phone and
written in a shared calendar, exercise programs are given on paper, and payments are recorded by
hand. The clinic serves patients in French and English and handles health information, so it
must respect Québec's **Law 25** on the protection of personal information.

## 2. Problems to solve

| # | Problem | Who suffers |
|---|---|---|
| P1 | Patients can only book by phone during opening hours | Patients, front desk |
| P2 | Double bookings and mistakes in the shared calendar | Patients, therapists |
| P3 | No-shows cost the clinic paid time; no deposit is taken | Clinic |
| P4 | Clinical notes are not protected well enough for health data; access is not traced | Patients, clinic (legal risk) |
| P5 | Paper exercise programs are lost and adherence is unknown | Patients, therapists |
| P6 | The same practical questions (parking, cancellations, insurance) take front-desk time | Front desk |
| P7 | The desk stops working when the internet is down | Front desk, patients |

## 3. Vision

> For the patients and staff of Clinique Physio Mont-Royal, the booking and patient portal is a
> secure system that lets patients book and pay online at any time, lets therapists document
> care and follow exercise programs, and lets the front desk run the day, even offline. Unlike a
> generic booking tool, it guarantees no double booking, protects health data by design, and
> respects Law 25.

## 4. Objectives and success indicators

| Objective | Success indicator (how it is measured) | Deliverable |
|---|---|---|
| O1. Secure access for every user | Access token at most 10 min; staff cannot reach any staff endpoint without MFA; account locked after 5 failures (automated tests) | D1 ✅ |
| O2. Never two appointments at the same time | 30 simultaneous bookings of one slot: exactly 1 succeeds (concurrency test) | D1 ✅ (database), D2 (API) |
| O3. Correct times for everyone | Appointment at 10:00 the Monday after a daylight saving change shows 10:00 in every client (tests in API, web, mobile) | D1 ✅ |
| O4. Online booking 24/7 with deposit | A patient books and pays a deposit in Stripe test mode in under 2 minutes | D2 |
| O5. Health data on a need-to-know basis | Tests prove a therapist cannot read another therapist's patients' notes; front desk and admin are refused; 100% of note reads are in the audit log | D2 |
| O6. Better exercise adherence | Patients check off sessions on mobile; therapist sees completed vs planned | D2 |
| O7. Fewer routine questions at the desk | Chatbot: 100% refusal of diagnosis requests, answers cite the clinic's documents, evaluated on 20 (D2) then 40 (D3) questions | D2–D3 |
| O8. The desk keeps working offline | Day schedule readable and check-ins queued without the API; conflicts detected on sync | D3 |
| O9. Law 25 compliance | Consents recorded with version and date; privacy requests and incident register available to the admin | D1 (consents) ✅, D3 |
| O10. Quality and maintainability | CI green on every pull request for the four apps; no high-severity dependency alerts | D1 ✅ |

## 5. Scope

### In scope

- REST API (FastAPI, PostgreSQL) holding every business rule and permission check
- Website (React): public pages, booking, patient portal, therapist workspace, administration
- Desktop app (C# WPF) for the front desk, with offline mode in D3
- Mobile app (Expo) for patients: appointments, exercise program, reminders
- Payments of deposits in Stripe **test mode** only
- Chatbot answering practical questions from the clinic's documents only
- French by default, English available; accessibility (WCAG 2.1 AA target on the website)

### Out of scope

- Real patients, real payments or real health data (everything is fictional)
- Billing to insurers or to the public health system (patients receive a receipt only)
- Medical diagnosis or treatment advice by the chatbot (it refuses)
- Several clinics, online video consultations, and SMS messages
- Publication to the app stores (the mobile app is delivered as an Expo link or APK)

## 6. Actors

| Actor | Main needs | Clients used | Authentication |
|---|---|---|---|
| Visitor | See services, prices, team, free times; ask the chatbot | Website | None |
| Patient | Book, pay, reschedule, follow the exercise program, receipts | Website, mobile | Password (MFA optional later) |
| Physiotherapist | Hours and time off, schedule, patient files, notes, programs | Website | Password + mandatory MFA |
| Front-desk agent | Day schedule, phone bookings, check-in, payments at the desk | Desktop | Password + mandatory MFA |
| Clinic administrator | Services, staff, reports, audit, Law 25 requests and incidents | Website | Password + mandatory MFA |
| Stripe, email provider, LLM provider | External systems (see [architecture.md](architecture.md)) | — | API keys, signed webhooks |

## 7. Main business rules

| ID | Rule |
|---|---|
| BR-1 | A therapist can never have two overlapping active appointments (database constraint). |
| BR-2 | Slots are on a 15-minute grid with a 5-minute buffer, never in the past, at most 60 days ahead. |
| BR-3 | A slot is held 10 minutes during payment, then released if not paid. |
| BR-4 | Cancellation more than 24 h before: deposit refunded; less than 24 h or no-show: deposit kept. |
| BR-5 | Times are stored in UTC and shown in Montréal time (America/Toronto). |
| BR-6 | A therapist reads a patient's clinical data only with a care relationship; front desk and admin never read notes. |
| BR-7 | Signed notes are never changed; corrections are amendments. Every access to a note is audited. |
| BR-8 | Emails, notifications and the chatbot never contain clinical information. |

## 8. Product backlog

Priorities use **MoSCoW** (Must, Should, Could). Statuses: **Done** (all acceptance criteria
met and tested), **In progress** (some criteria met), **To do**. Each issue holds the full story
("As a …, I want …, so that …") and its acceptance criteria.

Summary: 51 stories — Must 33, Should 14, Could 4. Planned by deliverable: D1 11, D2 23, D3 17.

<!-- BACKLOG-TABLE:START -->
| Issue | ID | User story | Priority | Deliverable | Status |
|---|---|---|---|---|---|
| — | US-AUTH-01 | Patient registration with consent | Must | D1 | Done |
| — | US-AUTH-02 | Login and secure sessions | Must | D1 | Done |
| — | US-AUTH-03 | Strong password storage and password policy | Must | D1 | Done |
| — | US-AUTH-03b | Password reset without user enumeration | Must | D1 | Done |
| — | US-AUTH-04 | Mandatory two-factor authentication for staff | Must | D1 | Done |
| — | US-AUTH-05 | Role and care-relationship access control | Must | D2 | Done |
| — | US-AUTH-06 | Protection against password guessing | Must | D1 | Done |
| — | US-AUTH-07 | Break-the-glass emergency access | Could | D3 | To do |
| — | US-AVL-01 | Service catalog | Must | D1 | Done |
| — | US-AVL-02 | Therapist working hours and time off | Must | D1 | Done |
| — | US-AVL-03 | Bookable slot computation | Must | D1 | Done |
| — | US-AVL-04 | Rooms as a resource | Should | D3 | To do |
| — | US-AVL-05 | Therapist profile page | Should | D2 | In progress |
| — | US-BKG-01 | Online booking with deposit | Must | D2 | In progress |
| — | US-BKG-02 | No double booking under concurrency | Must | D2 | Done |
| — | US-BKG-03 | Temporary hold during payment | Must | D2 | Done |
| — | US-BKG-04 | Deposit payment confirmed by Stripe | Must | D2 | Done |
| — | US-BKG-05 | Appointment lifecycle | Must | D2 | In progress |
| — | US-BKG-06 | Reschedule and cancel with the 24-hour rule | Must | D2 | Done |
| — | US-BKG-07 | Times shown in Montréal time | Must | D1 | Done |
| — | US-BKG-08 | Appointment reminders | Should | D3 | To do |
| — | US-BKG-09 | Waiting list | Could | D3 | To do |
| — | US-BKG-10 | Insurance receipt | Should | D3 | To do |
| — | US-CLN-01 | My patients and their history | Must | D2 | Done |
| — | US-CLN-02 | Encrypted SOAP session notes | Must | D2 | Done |
| — | US-CLN-03 | Signed notes and amendments | Should | D3 | Done |
| — | US-CLN-04 | Audit of clinical access | Must | D2 | Done |
| — | US-CLN-05 | No clinical notes for front desk and admin | Must | D2 | Done |
| — | US-CLN-06 | Document upload | Could | D3 | To do |
| — | US-EXE-01 | Exercise library | Must | D2 | Done |
| — | US-EXE-02 | Assign a program | Must | D2 | Done |
| — | US-EXE-03 | Follow my program | Must | D2 | In progress |
| — | US-EXE-04 | Adherence chart | Should | D3 | Done |
| — | US-EXE-05 | Daily exercise reminder | Could | D3 | To do |
| — | US-FRD-01 | Day schedule of all therapists | Must | D1 | Done |
| — | US-FRD-02 | Book for a patient on the phone | Must | D2 | To do |
| — | US-FRD-03 | Check-in and no-show | Must | D2 | To do |
| — | US-FRD-04 | Walk-in patients | Should | D3 | To do |
| — | US-FRD-05 | Record payments at the desk | Should | D3 | To do |
| — | US-FRD-06 | Offline mode with conflict detection | Should | D3 | To do |
| — | US-ADM-01 | Manage services, staff and rooms | Must | D2 | To do |
| — | US-ADM-02 | Reports | Should | D3 | To do |
| — | US-ADM-03 | Audit log viewer | Must | D3 | To do |
| — | US-ADM-04 | Privacy requests | Should | D3 | To do |
| — | US-ADM-05 | Confidentiality incident register | Should | D3 | To do |
| — | US-ADM-06 | Knowledge base management | Should | D3 | To do |
| — | US-BOT-01 | Ask practical questions | Must | D2 | To do |
| — | US-BOT-02 | Refuse diagnosis and handle emergencies | Must | D2 | To do |
| — | US-BOT-03 | Resist prompt injection and protect privacy | Must | D2 | To do |
| — | US-BOT-04 | Measured answer quality | Must | D2 | To do |
| — | US-BOT-05 | Answer feedback | Should | D2 | To do |
<!-- BACKLOG-TABLE:END -->

### D1 status

All 11 D1 stories are done, each proved by automated tests run in CI (completed 2026-11-04).

### D2 progress

- Done: US-BKG-02 (no double booking, with a clear 409 answer), US-BKG-03 (10-minute hold),
  US-BKG-04 (Stripe deposit, signed webhook), US-BKG-06 (24-hour rule with Stripe refunds),
  US-AUTH-05 (care relationship), US-CLN-01 to 05 (patient files, encrypted SOAP notes, signature
  and amendments, audit log, no notes for front desk and admin), US-EXE-01, 02 and 04 (exercise
  library, programs, adherence).
- In progress: US-BKG-01 (website booking and Stripe payment done; mobile and email to do),
  US-EXE-03 (check-off: API done, screens to do), US-BKG-05 (status history; check-in
  and no-show to come), US-AVL-05 (team page; photos to come).
- Next: the screens: therapist workspace (notes, programs), patient exercises on mobile,
  front-desk check-in.
