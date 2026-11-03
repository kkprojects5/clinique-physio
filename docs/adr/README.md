# Architecture Decision Records

Each file records one important decision: the context, what was decided, the alternatives
considered, and the consequences. A decision is never edited after it is accepted: a new ADR
replaces it if it changes.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-double-booking-exclusion-constraint.md) | Prevent double booking with a PostgreSQL exclusion constraint | Accepted |
| [0002](0002-token-storage.md) | Short access token + rotating refresh token in an httpOnly cookie | Accepted |
| [0003](0003-mobile-framework.md) | Mobile app with Expo (React Native, TypeScript) | Accepted |
| [0004](0004-time-zones.md) | Store times in UTC, define schedules in clinic local time | Accepted |
| [0005](0005-desktop-core-library.md) | Desktop: WPF screens + a separate, testable Core library (MVVM) | Accepted |
| [0006](0006-deployment-copy.md) | Deploy from a copy of the repository in the developer's account | Accepted (temporary) |
