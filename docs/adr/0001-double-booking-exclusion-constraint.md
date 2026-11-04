# ADR-0001: Prevent double booking with a PostgreSQL exclusion constraint

- Status: Accepted (D1)
- Requirements: B-BKG-02, BR-B-01, challenge B-C1

## Context

Two patients must never get the same therapist at the same time, even if they click "book" at the
same millisecond (B-C1: 30 simultaneous requests must give exactly one success). Appointments have
different lengths (30, 45, 60 minutes), so two bookings can overlap without starting at the same
time.

## Decision

Enforce the rule **in the database** with an exclusion constraint on the `appointments` table:

```sql
EXCLUDE USING gist (therapist_id WITH =, during WITH &&)
  WHERE (status IN ('held', 'pending_payment', 'confirmed', 'checked_in'))
```

`during` is a `tstzrange` (start and end). The constraint refuses any new active appointment whose
time range overlaps (`&&`) another active one for the same therapist. Cancelled and finished
appointments do not count, so their slot can be booked again. The `btree_gist` extension allows the
`=` comparison on `therapist_id` inside the GiST index. The booking endpoint (D2) will turn the
database refusal into a clear "slot no longer available" answer (HTTP 409).

## Alternatives considered

| Alternative | Why not |
|---|---|
| Check in Python first ("is the slot free?"), then insert | Race condition: two requests can both see the slot free before either inserts. |
| `SELECT ... FOR UPDATE` on existing rows | Locks only rows that already exist; it cannot lock an empty slot, so two first bookings can still collide. |
| Serializable transactions | Works, but every conflict becomes a retry error to handle everywhere, and it is slower under load. |
| A table of fixed slots with a unique key | Breaks with different service lengths and with the 5-minute buffer; overlaps are not "the same key". |
| A lock in the application (mutex, Redis) | Does not protect against several API instances or direct database writes; one more system to run. |

## Consequences

- The guarantee holds whatever the client or the number of API instances: the database is the
  single point of truth.
- Proven by `api/tests/test_double_booking.py`: 30 concurrent bookings give 1 success and 29
  refusals, and the test fails if the constraint is removed.
- Requires PostgreSQL (not portable to every database) and the `btree_gist` extension, created by
  the first migration.
- The same pattern will apply to rooms (B-AVL-04).
- **Deadlocks under heavy concurrency.** When many transactions insert overlapping rows at the
  same moment, PostgreSQL sometimes cancels one of them with "deadlock detected" instead of
  reporting the overlap (a known behaviour of exclusion constraints). No double booking can
  result: the cancelled transaction saved nothing. The application therefore retries a write
  that fails with a deadlock (up to 3 times, in a fresh transaction, `app/db/retry.py`); on the
  retry it either succeeds or gets the normal overlap refusal, which becomes HTTP 409. Any other
  error is never retried. Found by CI, where the 30-booking test occasionally failed with a
  deadlock; the test now goes through the same retry (`test_retry.py`, `test_double_booking.py`).
