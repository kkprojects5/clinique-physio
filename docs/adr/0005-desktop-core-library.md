# ADR-0005: Desktop app as WPF screens plus a separate, testable Core library

- Status: Accepted (D1)
- Requirements: spec section 5.1 (WPF, MVVM, CommunityToolkit.Mvvm), B.8.3, NFR-11, NFR-12

## Context

The front-desk app must be a C# desktop application. WPF only runs on Windows. The logic (API
calls, login with MFA, schedule layout, error messages) must be tested automatically, including in
CI.

## Decision

Split the solution in three projects:

| Project | Target | Contains |
|---|---|---|
| `CliniquePhysio.Desktop.Core` | `net8.0` (any OS) | Models, API client, session, view models (MVVM with CommunityToolkit.Mvvm), translations |
| `CliniquePhysio.Desktop` | `net8.0-windows` (WPF) | Screens (XAML), converters, app start-up only |
| `CliniquePhysio.Desktop.Tests` | `net8.0` | xUnit tests of the Core library |

Screens bind to view models; view models never reference WPF. Navigation goes through an
`INavigator` interface, and the API through `IApiClient`, so tests use fakes.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Everything in the WPF project (code-behind) | Logic mixed with screens; hard to test; harder to explain. |
| .NET MAUI | Also targets Windows, but WPF is the recommended option in the spec and better documented for desktop data grids. |

## Consequences

- 31 xUnit tests run in seconds without opening a window (`desktop-ci` on Windows).
- The access token lives only in memory (`Session`), never on disk.
- Offline mode (B-FRD-06, D3) can be added in Core and tested the same way.
