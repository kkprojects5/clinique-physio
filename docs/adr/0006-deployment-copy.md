# ADR-0006: Deploy from a copy of the repository in the developer's account

- Status: Accepted, temporary (D1)
- Requirements: spec section 7.2 (automatic deployment), 7.3

## Context

The course repository belongs to the supervisor's account; the developer has write access but not
admin access. Render and Vercel can only deploy repositories whose owner has authorized them, and
GitHub only lets the owner add the secrets an automated deploy pipeline would need.

## Decision

Keep `stevatak/Khadizhat-Synth` as the **only** place where work happens (issues, branches, pull
requests, CI). After each merge, copy `main` to a deployment repository in the developer's account,
`kkprojects5/clinique-physio`, with one command:

```
git push deploy main
```

Render (API) and Vercel (website) are connected to that copy and deploy automatically when it
changes. The copy is never edited directly.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Ask the owner to authorize Render and Vercel | Best long-term option; it needs the supervisor's action, and D1 could not wait. |
| Deploy from GitHub Actions with host tokens | Repository secrets can only be added by the owner on a personal repository. |
| Manual uploads | No traceability; easy to deploy something that was not reviewed. |

## Consequences

- Deployment is still automatic and only ever deploys reviewed, merged code.
- One extra manual step after each merge; forgetting it delays deployment but cannot deploy
  unreviewed code.
- The copy also gives the developer a portfolio copy of the code with its full history.
- To revisit when the owner authorizes Render and Vercel on the course repository: then connect
  them to it directly and retire the copy.
