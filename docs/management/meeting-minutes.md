# Meeting minutes

Meetings with the supervisor. Newest first. Copy the template for each meeting and fill it in
the same day. Decisions that change the design also become an ADR in [../adr](../adr/README.md).

## Template

```
## YYYY-MM-DD — <subject, for example "D1 review">

**Present:** Claire Mancini (developer), <supervisor>
**Form:** in person / online / email

### Points discussed
- ...

### Decisions
- ...

### Actions
| Action | Who | By |
|---|---|---|
| ... | ... | YYYY-MM-DD |
```

## Points to raise at the next meeting

- Repository settings that need admin rights: branch protection on `main` (0 approvals, the four
  CI checks required), CodeQL code scanning and secret scanning (residual risk R-5 in the threat
  model)
- D1 was completed on 2026-11-04 instead of 2026-10-25; D2 is due 2026-11-15 (end of week 6): agree on the D2 scope
- Demo account passwords: to be given privately, never in the repository
