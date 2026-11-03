# ADR-0002: Short access token and rotating refresh token in an httpOnly cookie

- Status: Accepted (D1)
- Requirements: B-AUTH-02, B-AUTH-04, challenge B-C4, NFR-03

## Context

Clients must prove who they are on every request. Tokens can be stolen: by malicious JavaScript
on the website (XSS), from a lost phone, or from an unattended front-desk computer. Health data
raises the stakes. Staff must also be logged out after 15 minutes of inactivity.

## Decision

Two tokens with different jobs:

1. **Access token**: a signed JWT valid **10 minutes**, sent as `Authorization: Bearer`. It
   carries the user id, role and whether MFA was passed (`mfa: true`). The API still reads the role
   from the database on every request.
2. **Refresh token**: a long random value in an **httpOnly, Secure cookie** limited to the path
   `/api/v1/auth`. The database stores only its SHA-256 hash. Each use replaces it with a new one
   (**rotation**); using an old one again is treated as theft and cancels all sessions of the user.
   Patients' refresh tokens last 7 days; staff refresh tokens last 15 minutes, renewed at each use,
   so inactivity logs staff out.

Where each client keeps the access token:

| Client | Storage | Why |
|---|---|---|
| Website (D2, with the patient portal) | In memory only (JavaScript variable), refreshed from the cookie | Never in `localStorage`; a page reload gets a new access token from the cookie |
| Mobile | SecureStore (iOS Keychain / Android Keystore) | Encrypted by the phone |
| Desktop | In memory only | Closing the app ends the session; nothing on disk |

## Alternatives considered

| Alternative | Why not |
|---|---|
| Token in `localStorage` | Any XSS can read and send it away; it survives closing the browser. |
| One long-lived token | A stolen token works for days; no way to log out other than changing the signing key. |
| Server sessions only (session id cookie) | Works for the website, but the desktop and mobile apps are not browsers; one mechanism for all three clients is simpler. |
| Refresh token readable by JavaScript | Defeats the purpose of the cookie. |

## Consequences

- A stolen access token is useful for at most 10 minutes; a stolen refresh token is detected at
  its second use.
- Proven by `api/tests/test_login.py` (rotation, reuse detection, logout, staff inactivity) and
  `api/tests/test_mfa.py`.
- In production the website (Vercel) and the API (Render) are on different sites, so the cookie
  must be `SameSite=None`. This is a residual risk (threat model R-4), reduced by CORS and the
  narrow cookie path; an `Origin` check is planned for D2.
