# Data classification — Clinique Physio Mont-Royal

Status: **D1 (v0.1.0)**. Companion document: [threat-model.md](threat-model.md).
Data model: [erd.md](erd.md).

All data in this project is fictional. This classification is written as if the data were real,
because the system is designed for a real clinic subject to Québec's Law 25.

## 1. Classes

| Class | Meaning | Examples | Basic rules |
|---|---|---|---|
| **Public** | Meant to be published | Services and prices, therapists' names and bios | No restriction on reading; only admins change it |
| **Internal** | Clinic operations, not personal | Working hours, licence numbers, configuration | Staff only; not shown to the public unless needed |
| **Personal** | Identifies a person (Law 25 "personal information") | Name, email, phone, date of birth | Collected only when needed (each field justified below); shown only to the person and to staff who need it; never in logs |
| **Health** | Health information, or reveals that a person receives care (Law 25 sensitive information) | Clinical notes, pain levels, appointments linked to a patient | Strictest: need-to-know access, encryption at rest for free text, every access audited (D2), never in emails, notifications or the chatbot |

Protections that apply to **every** class:

- In transit: HTTPS only (HSTS); TLS between the API and the database.
- At rest: the database provider encrypts its disks; the most sensitive fields are also
  encrypted by the application (Fernet: AES with HMAC), with a key kept outside the database.
- Access: every request is checked by the API (role, and ownership or care relationship).
  No client reads the database directly.

## 2. Field by field

Legend for **Status**: ✅ implemented, ⏳ planned (deliverable in brackets).

### users — every account

| Field | Class | Why it is collected | Who can see it | Protection | Status |
|---|---|---|---|---|---|
| `email` | Personal | Login identifier; confirmation and reminder emails | The person; staff who manage accounts (admin) | Unique; masked in logs | ✅ |
| `password_hash` | Internal (secret) | Check the password without storing it | Nobody: never returned by the API | Argon2id one-way hash | ✅ |
| `role` | Internal | Decides what the account may do | The person; admin | Set by the server only, never by the client | ✅ |
| `language` | Personal (low) | Communicate in the person's language (French by default) | The person | — | ✅ |
| `mfa_secret_enc` | Internal (secret) | Check staff two-factor codes | Nobody | Encrypted (Fernet), key outside the database | ✅ |
| `mfa_enabled_at`, `mfa_last_used_step` | Internal | Know if MFA is set up; block code reuse | Nobody via the API | — | ✅ |
| `failed_login_count`, `locked_until` | Internal | Lock the account after repeated failures | Nobody via the API | Lock state never revealed (same answer as a wrong password) | ✅ |
| `is_active`, `email_verified_at`, `last_login_at`, `created_at` | Internal | Account state; security investigations | Admin | — | ✅ |

### patients — patient profile

Collected at registration (B-AUTH-01). Each field is the minimum the clinic needs.

| Field | Class | Why it is collected | Who can see it | Protection | Status |
|---|---|---|---|---|---|
| `first_name`, `last_name` | Personal | Identify the patient at the desk and on insurance receipts | The patient; front desk; their therapist | Access checks | ✅ |
| `date_of_birth` | Personal | Tell apart patients with the same name; insurance receipts | The patient; front desk; their therapist | Access checks; must be a real past date | ✅ |
| `phone` | Personal | Reach the patient about appointments (delays, cancellations) | The patient; front desk; their therapist | Access checks; not sent to the chatbot | ✅ |
| `emergency_contact_enc` | Personal (sensitive) | Optional: someone to call if the patient feels unwell during treatment | Front desk and their therapist, when needed (D2) | **Encrypted** (Fernet); optional field | ✅ |
| `created_at` | Internal | Retention period calculation | Admin | — | ✅ |

**Not collected, on purpose:** address, health insurance number, sex or gender, medical
history at registration. They are not needed to book; the therapist records what is clinically
needed in the session notes (D2).

### therapists

| Field | Class | Why it is collected | Who can see it | Protection | Status |
|---|---|---|---|---|---|
| `first_name`, `last_name`, `specialties`, `languages`, `bio_fr`, `bio_en` | Public | Help patients choose a therapist (team page) | Everyone | Changed only by admin | ✅ |
| `licence_number` | Internal | Required on official insurance receipts (B-BKG-10) | Staff; printed on the patient's own receipts | Not in the public team list (tested: `test_therapists_list_shows_public_info_only`) | ✅ |

### services, therapist_services, availability_rules, rooms

| Data | Class | Why | Who can see it | Status |
|---|---|---|---|---|
| Service names, descriptions, durations, prices, deposits | Public | The patient must know what they book and pay | Everyone | ✅ |
| Which therapist provides which service | Public | "First available" search and filters | Everyone | ✅ |
| Weekly working hours (`availability_rules`) | Internal | Compute free slots | The therapist; staff. Only the resulting free slots are public | ✅ |
| Rooms | Internal | Avoid two treatments in the same room (Should) | Staff | ⏳ (D3) |

### availability_exceptions — time off

| Field | Class | Why | Who can see it | Protection | Status |
|---|---|---|---|---|---|
| `during` | Internal | Remove slots when the therapist is away | The therapist; staff | Ownership check on delete (tested) | ✅ |
| `reason` | Personal (therapist) | Optional note ("training", "vacation") | The therapist only | Optional, free text kept short; never shown to patients | ✅ |

### appointments and appointment_status_history

An appointment links a person to a physiotherapy clinic at a given time: it reveals that this
person receives care, so it is treated as **Health**.

| Field | Class | Why | Who can see it | Protection | Status |
|---|---|---|---|---|---|
| `patient_id` + `during` + `service_id` + `therapist_id` | Health | The booking itself | The patient (own only); front desk; the therapist | Patient endpoints filtered by the logged-in patient (tested: `test_patient_never_sees_another_patients_appointments`); public slot search shows only free times, never who booked | ✅ |
| `status`, `hold_expires_at` | Internal | Appointment lifecycle | Same as above | — | ✅ |
| `created_by`, `version`, `created_at`, `updated_at` | Internal | Traceability; offline sync conflicts | Staff | — | ✅ |
| Status history (who changed what) | Internal | Accountability (B-BKG-05) | Admin | Rows only added; reasons never clinical | ✅ |

### clinical_notes — the most sensitive data

| Field | Class | Why | Who can see it | Protection | Status |
|---|---|---|---|---|---|
| `content_encrypted` (SOAP note) | Health | Professional record of each treatment, required by the profession | **Only the patient's therapist** (care relationship); not front desk, not admin by default | **Encrypted** by the application; immutable after signature; amendments instead of edits; no DELETE permission; every read and write audited | ⏳ (D2) |
| `signed_at`, `version`, `amends_note_id` | Health | Integrity of the record | Same as above | — | ⏳ (D2) |

### exercise programs and logs

| Data | Class | Why | Who can see it | Status |
|---|---|---|---|---|
| Exercise library (`exercises`) | Public | General exercise descriptions | Everyone | ⏳ (D2) |
| A patient's program (`programs`, `program_items`) | Health | Treatment plan | The patient; their therapist | ⏳ (D2) |
| Completed sessions and **pain level** (`exercise_logs`) | Health | Track adherence and progress | The patient; their therapist | ⏳ (D2) |

### payments and payment_events

| Data | Class | Why | Who can see it | Protection | Status |
|---|---|---|---|---|---|
| Amounts, type, method, status | Personal | Deposits, refunds, receipts | The patient (own); front desk; admin | Card data is never sent to or stored by our systems (Stripe handles it) | ⏳ (D2) |
| Stripe ids and webhook events | Internal | Confirm payments exactly once | Admin | Signed webhooks; unique event id | ⏳ (D2) |

### consents, privacy_requests, incident_register (Law 25)

| Data | Class | Why | Who can see it | Status |
|---|---|---|---|---|
| Consent type, version, date given, date withdrawn | Personal | Prove what the person agreed to and when (Law 25) | The person; admin | ✅ |
| Access, correction and deletion requests | Personal | Law 25 rights of the person | The person; admin (person in charge of privacy) | ⏳ (D3) |
| Confidentiality incident register | Internal (may contain Personal) | Law 25 obligation to record incidents | Admin only | ⏳ (D3) |

### refresh_tokens and audit_logs

| Data | Class | Why | Who can see it | Protection | Status |
|---|---|---|---|---|---|
| Password reset tokens | Internal (secret) | Let a user choose a new password from an email link | Nobody | Only a SHA-256 hash is stored; single use; 30 minutes | ✅ |
| Refresh tokens | Internal (secret) | Keep sessions without storing passwords | Nobody | Only a SHA-256 hash is stored; rotated and revocable | ✅ |
| Audit log (who accessed which patient file, when, from where) | Personal | Accountability; detect abuse (B-ADM-03) | Admin only | Append-only (no UPDATE or DELETE for the application) | ⏳ (D2) |

### Chatbot knowledge base and conversations (D2)

| Data | Class | Rule |
|---|---|---|
| Knowledge base documents | Public | Policies and general information only. **Never** patient data (spec section 8). |
| Conversation logs | Personal | Names, phones, emails and health numbers masked before storage; kept 30 days (B.9.2). |

## 3. Data that never leaves the system

| Destination | What may be sent | What is never sent |
|---|---|---|
| Logs | Request ids, error types, masked emails | Passwords, tokens, phone numbers, note contents |
| Emails and push notifications | Date, time, clinic address, links | Any clinical information (BR-B-08) |
| LLM provider (chatbot, D2) | The visitor's question and approved policy passages | Patient records, appointments, notes |
| Front desk | Name, phone, service, status | Clinical notes, pain levels, programs |

## 4. Retention (to be finalized in D3)

| Data | Planned retention |
|---|---|
| Clinical notes | Kept 5 years after the last visit (professional order rule, fictional for this project), then anonymized; never physically deleted before |
| Chatbot conversation logs | 30 days |
| Refresh tokens | Deleted after expiry |
| Accounts without any appointment | Deleted on request (Law 25 right to deletion) |
