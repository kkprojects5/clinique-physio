# ADR-0003: Mobile app with Expo (React Native, TypeScript)

- Status: Accepted (D1)
- Requirements: spec section 5.1 (React Native/Expo or .NET MAUI), B.8.2

## Context

The patient needs a mobile app (appointments, reminders, exercises). The spec allows React Native
with Expo or .NET MAUI. The website is already in React.

## Decision

Use **Expo SDK 58** with **React Native** and **TypeScript**.

## Alternatives considered

| Alternative | Why not |
|---|---|
| .NET MAUI | Would reuse the desktop's C#, but shares no code or skills with the React website; heavier tooling; slower to try on a phone. |
| Plain React Native (without Expo) | More native setup (Android Studio, Xcode builds) for no gain at this scale. |
| JavaScript instead of TypeScript | The spec's mobile pipeline includes a type-check; types catch mistakes in API data early. |

## Consequences

- Same language family and patterns as the website (React components, hooks, fetch).
- Instant testing on a real phone with Expo Go, and in an Android emulator.
- Secure token storage with `expo-secure-store` (Keychain / Keystore).
- Expo packages must be upgraded together with the SDK; Dependabot is told to leave them alone
  (`.github/dependabot.yml`).
- Known issue: a "high" advisory in Expo's build tooling (`zod`), not shipped in the app
  (threat model R-1).
