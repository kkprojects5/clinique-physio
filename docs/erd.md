# Entity-Relationship Diagram — Clinique Physio Mont-Royal

Source: cahier des charges, section B.6 (data model), plus the requirements in B.4.  
Status: **draft for D1** (v0.1.0).

The model is split into an overview and six modules so each diagram stays readable. In the module diagrams, tables from other modules appear with their `id` only.

## How to read the diagrams

| Symbol | Meaning |
|---|---|
| `PK` | Primary key |
| `FK` | Foreign key (points to another table) |
| `UK` | Unique |
| `\|\|--o{` | One to many (zero or more) |
| `\|\|--\|{` | One to many (at least one) |
| `\|\|--o\|` | One to zero or one |
| `\|o--o{` | Optional link: zero or one to many |

## Overview

The main tables and how they connect, without columns.

```mermaid
erDiagram
    users ||--o| patients : "is a"
    users ||--o| therapists : "is a"
    therapists }o--o{ services : "provides"
    therapists ||--o{ availability_rules : "works"
    patients ||--o{ appointments : "books"
    therapists ||--o{ appointments : "treats"
    services ||--o{ appointments : "for"
    appointments ||--o{ payments : "paid by"
    appointments ||--o{ clinical_notes : "documented in"
    patients ||--o{ programs : "follows"
    programs ||--|{ exercises : "contains"
    users ||--o{ audit_logs : "acts"
    patients ||--o{ privacy_requests : "submits"
```

## 1. Identity and access

Who can log in, with which role, and what they consented to (B-AUTH, Law 25).

```mermaid
erDiagram
    users ||--o| patients : "is a"
    users ||--o| therapists : "is a"
    users ||--o{ refresh_tokens : "has"
    users ||--o{ consents : "gives"
    users {
        uuid id PK
        text email UK
        text password_hash "Argon2id"
        text role "patient, therapist, front_desk, admin"
        text language "fr default, en"
        bytea mfa_secret_enc "encrypted, staff only"
        bool is_active
        timestamptz email_verified_at
        timestamptz last_login_at
        timestamptz created_at
    }
    patients {
        uuid id PK
        uuid user_id FK "unique"
        text first_name
        text last_name
        date date_of_birth
        text phone
        bytea emergency_contact_enc "encrypted, optional"
        timestamptz created_at
    }
    therapists {
        uuid id PK
        uuid user_id FK "unique"
        text licence_number UK "fictional"
        text specialties "array"
        text languages "array"
        text bio_fr
        text bio_en
    }
    refresh_tokens {
        uuid id PK
        uuid user_id FK
        text token_hash UK "never the raw token"
        timestamptz expires_at
        timestamptz revoked_at
        timestamptz created_at
    }
    consents {
        uuid id PK
        uuid user_id FK
        text type "privacy_policy, electronic_comms"
        text version
        timestamptz granted_at
        timestamptz revoked_at
    }

```

- A user has exactly one role. A patient or therapist row adds the role-specific details.
- `refresh_tokens` stores only a hash of each token, so a stolen database can't be used to log in.
- `consents` keeps the version and date of each consent (B-AUTH-01).

## 2. Services and availability

What the clinic offers and when each therapist works (B-AVL).

```mermaid
erDiagram
    therapists ||--o{ therapist_services : "provides"
    services ||--o{ therapist_services : "provided by"
    therapists ||--o{ availability_rules : "weekly schedule"
    therapists ||--o{ availability_exceptions : "time off"
    services {
        uuid id PK
        text name_fr
        text name_en
        text description_fr
        text description_en
        int duration_min "30, 45 or 60"
        int price_cents
        int deposit_cents
        bool is_initial_evaluation
        bool is_active
    }
    therapist_services {
        uuid therapist_id PK, FK
        uuid service_id PK, FK
    }
    availability_rules {
        uuid id PK
        uuid therapist_id FK
        smallint weekday "1 Mon to 7 Sun"
        time start_time "clinic local time"
        time end_time
    }
    availability_exceptions {
        uuid id PK
        uuid therapist_id FK
        tstzrange during
        text reason
    }
    rooms {
        uuid id PK
        text name UK
    }
    therapists {
        uuid id PK
    }
```

- `therapist_services` is the many-to-many link: which therapist can provide which service.
- Bookable slots are not stored. They are computed: availability rules, minus exceptions, minus existing appointments (B-AVL-03).
- Rules use local `time`, so Monday 8:00 stays 8:00 clinic time across DST changes.
- `rooms` is a Should requirement (B-AVL-04).

## 3. Booking and payments

The transactional core: appointments, their status changes and their payments (B-BKG).

```mermaid
erDiagram
    patients ||--o{ appointments : "books"
    therapists ||--o{ appointments : "treats"
    services ||--o{ appointments : "for"
    rooms |o--o{ appointments : "hosts"
    users ||--o{ appointments : "created by"
    appointments ||--o{ appointment_status_history : "status changes"
    appointments ||--o{ payments : "paid by"
    payments |o--o{ payment_events : "confirmed by"
    appointments {
        uuid id PK
        uuid patient_id FK
        uuid therapist_id FK
        uuid room_id FK "nullable, Should"
        uuid service_id FK
        tstzrange during "no overlap per therapist"
        text status "state machine B-BKG-05"
        timestamptz hold_expires_at "10 min hold"
        uuid deposit_payment_id FK
        uuid created_by FK
        int version "offline sync conflicts"
        timestamptz created_at
        timestamptz updated_at
    }
    appointment_status_history {
        uuid id PK
        uuid appointment_id FK
        text from_status
        text to_status
        uuid actor_id FK
        timestamptz created_at
    }
    payments {
        uuid id PK
        uuid appointment_id FK
        int amount_cents
        text type "deposit, balance, refund, fee"
        text method "stripe, cash, debit"
        text status
        text stripe_id UK "nullable"
        timestamptz created_at
    }
    payment_events {
        uuid id PK
        uuid payment_id FK "nullable"
        text stripe_event_id UK "idempotency"
        text event_type
        jsonb payload
        timestamptz received_at
        timestamptz processed_at
    }
    patients {
        uuid id PK
    }
    therapists {
        uuid id PK
    }
    services {
        uuid id PK
    }
    rooms {
        uuid id PK
    }
    users {
        uuid id PK
    }
```

- **No double booking:** an exclusion constraint stops two active appointments overlapping for the same therapist (B-BKG-02, challenge B-C1).
- Every status change is a row in `appointment_status_history`, with who made it (B-BKG-05).
- `payment_events.stripe_event_id` is unique, so a webhook received twice is processed once (B-BKG-04).
- `version` lets the desktop app detect conflicts when it syncs offline actions (B-FRD-06).

## 4. Clinical file and exercises

The therapist's notes and the patient's exercise program (B-CLN, B-EXE).

```mermaid
erDiagram
    appointments ||--o{ clinical_notes : "documented in"
    therapists ||--o{ clinical_notes : "writes"
    clinical_notes |o--o{ clinical_notes : "amended by"
    patients ||--o{ programs : "follows"
    therapists ||--o{ programs : "assigns"
    programs ||--|{ program_items : "contains"
    exercises ||--o{ program_items : "used in"
    program_items ||--o{ exercise_logs : "checked off"
    clinical_notes {
        uuid id PK
        uuid appointment_id FK
        uuid therapist_id FK
        bytea content_encrypted "SOAP, encrypted"
        int version
        uuid amends_note_id FK "nullable, self"
        timestamptz signed_at
        timestamptz created_at
    }
    programs {
        uuid id PK
        uuid patient_id FK
        uuid therapist_id FK
        date start_date
        int weeks
        text notes
        timestamptz created_at
    }
    program_items {
        uuid id PK
        uuid program_id FK
        uuid exercise_id FK
        int sets
        int reps
        int times_per_week
    }
    exercises {
        uuid id PK
        text name_fr
        text name_en
        text instructions_fr
        text instructions_en
        text image_url
        int default_sets
        int default_reps
    }
    exercise_logs {
        uuid id PK
        uuid program_item_id FK
        timestamptz done_at
        smallint pain_level "0 to 10"
    }
    appointments {
        uuid id PK
    }
    patients {
        uuid id PK
    }
    therapists {
        uuid id PK
    }
```

- Note content is encrypted by the application before it reaches the database (B-CLN-02).
- Notes are never deleted. A correction is a new note pointing to the original with `amends_note_id` (BR-B-07).
- A program is a list of exercises; each check-off by the patient is one `exercise_logs` row, with an optional pain level.

## 5. Privacy, compliance and audit

Law 25 obligations and the audit trail (B-ADM, B-CLN-04).

```mermaid
erDiagram
    patients ||--o{ privacy_requests : "submits"
    users |o--o{ privacy_requests : "handles"
    users |o--o{ incident_register : "records"
    users |o--o{ audit_logs : "acts"
    patients |o--o{ audit_logs : "concerns"
    privacy_requests {
        uuid id PK
        uuid patient_id FK
        text type "access, deletion, correction"
        text status
        timestamptz requested_at
        timestamptz completed_at
        uuid handled_by FK
    }
    incident_register {
        uuid id PK
        timestamptz occurred_at
        timestamptz discovered_at
        text description
        text data_categories
        text risk_level
        text measures
        timestamptz notified_at
        uuid recorded_by FK
    }
    audit_logs {
        bigint id PK
        uuid actor_id FK
        text action
        text resource_type
        uuid resource_id
        uuid patient_id FK "nullable"
        inet ip
        text client_app "web, mobile, desktop"
        timestamptz created_at
    }
    users {
        uuid id PK
    }
    patients {
        uuid id PK
    }
```

- `audit_logs` is append-only: the application can insert and read rows but never change or delete them.
- `incident_register` is the confidentiality incident register Law 25 requires (B-ADM-05).

## 6. Chatbot knowledge base

Documents the chatbot answers from (spec section 8).

```mermaid
erDiagram
    kb_documents ||--|{ document_chunks : "split into"
    kb_documents {
        uuid id PK
        text title
        text language "fr, en"
        text category
        text version
        text content_hash UK "idempotent re-ingestion"
        timestamptz updated_at
    }
    document_chunks {
        uuid id PK
        uuid document_id FK
        int chunk_index
        text content
        vector embedding "pgvector"
        text content_hash
    }

```

- Each document is split into chunks, and each chunk has an embedding vector used for similarity search.
- These tables never contain patient information.
- Conversation tables (`chat_*`) are added in D2.

## Design notes

1. **UUID primary keys.** IDs can't be guessed, which reduces IDOR risk (challenge B-C3). Ownership is still checked on every request; UUIDs are only a second layer. `audit_logs` uses `bigint` because it's never exposed by ID.
2. **Money in cents** (`int`), never floating point.
3. **All timestamps are `timestamptz`**, stored in UTC and displayed in `America/Toronto` (B-BKG-07).
4. **No double booking (B-BKG-02)**, using the `btree_gist` extension:
   `EXCLUDE USING gist (therapist_id WITH =, during WITH &&) WHERE (status IN ('held','pending_payment','confirmed','checked_in'))`.
   The same constraint applies to `room_id` if rooms are implemented.
5. **Clinical notes are never deleted.** The application's database role has no `DELETE` permission on `clinical_notes`.
6. **Encrypted fields** (`*_enc`, `content_encrypted`) are `bytea`, encrypted in the application with a key kept outside the database.

## Additions to the spec's model

These are not in B.6, but the requirements need them:

| Addition | Why |
|---|---|
| `refresh_tokens` table | Store a hash of each refresh token so it can be revoked at logout or if stolen (B-AUTH-02). |
| `users.email_verified_at` | Email verification at registration (B-AUTH-01). |
| `appointments.hold_expires_at` | The 10-minute hold during payment (B-BKG-03). |
| `appointments.version` and `updated_at` | Detect conflicts when the desktop app syncs offline actions (B-FRD-06). |
| `payments.status` | Track pending, succeeded, failed and refunded payments. |
