# Law 25 package — Clinique Physio Mont-Royal (D3)

Québec's *Act respecting the protection of personal information in the private sector*, as
changed by Law 25. This page lists what the system does for each obligation and where the
evidence is. The clinic and all data are fictional (student project).

## 1. Contents of the package

| D3 item | Where | Evidence (tests) |
|---|---|---|
| Privacy policy, French and English | Website: **/confidentialite**, link in the footer of every page and in the consent box at registration. Text: [`web/src/pages/policyText.js`](../../web/src/pages/policyText.js) | `web/src/pages/consents.test.jsx` |
| Consent management | Registration: policy required, messages optional. **Mes données → Mes consentements**: see the version and date, give or withdraw the optional consent, accept a new policy version. API: `GET /me/consents`, `PUT /me/consents/electronic_comms`, `POST /me/consents/privacy_policy` | `api/tests/test_consents.py`, `api/tests/test_register.py` |
| Data export and deletion | **Mes données**: access, correction, deletion requests; the administrator exports (JSON) or deletes and answers within 30 days | `api/tests/test_privacy.py`, `web/src/pages/privacy.test.jsx`; demo [`docs/demo/d3-law25`](../demo/d3-law25/README.md) |
| Retention rules | [`docs/data-classification.md` section 4](../data-classification.md#4-retention) | `test_privacy.py` (deletion keeps the record), chatbot 30-day purge test |
| Incident register | Administration → **Incidents**: append-only register, CAI and persons notification dates | `test_privacy.py`; demo screenshots 4 and 5 |
| Data classification | [`docs/data-classification.md`](../data-classification.md): every field, its class, why it is kept, who sees it | `test_data_dictionary.py` |
| Assessment before sending data outside Québec | [Section 4 below](#4-privacy-impact-assessment-transfer-outside-québec) | — |

## 2. Obligations and how they are met

| Obligation (Law 25) | How the system meets it |
|---|---|
| Person in charge of personal information, published contact (art. 3.1) | Named in the policy, section 1 (fictional director, `confidentialite@clinique.example.com`) |
| Published policy in clear language (art. 3.2, 8) | `/confidentialite`, FR/EN, short items, linked everywhere |
| Collect only what is needed, say why (art. 4, 5, 8) | Registration asks only for what booking needs; the purpose of each field is in the policy and in the data classification |
| Consent: clear, separate for each purpose, recorded, can be withdrawn (art. 8.3, 14) | Two separate boxes; the version and date are stored; the optional consent is withdrawn in one click; the history is kept |
| Under 14: consent from a parent or tutor (art. 4.1) | The API refuses an online account for people under 14 (`MIN_AGE`); the policy and the form tell the parent to call |
| Confidentiality by default, no profiling technology (art. 8.1, 9.1) | No advertising or analytics cookies; one strictly necessary httpOnly cookie; only the language is kept in the browser |
| Right of access, correction, portability (art. 27, 28, 27 al. 3) | Requests in **Mes données**; export in JSON (structured, common format); 30-day deadline shown, late requests in red |
| Right to deletion, with legal retention (art. 28.1, 23) | Account closed and contact details erased at once; health record kept 5 years after the last visit, reason written in the answer |
| Incidents: register, notify CAI and persons if serious risk (art. 3.5 to 3.8) | Register in the admin; entries cannot be deleted (trigger); notification dates recorded |
| Security measures (art. 10) | HTTPS, hashed passwords, encrypted sensitive fields, staff two-factor login, roles, audit log; see the [security audit](../security/security-audit.md) |
| Assessment before communicating outside Québec (art. 17) | Section 4 below |

## 3. How to show it (demo)

1. Open the website footer → **Politique de confidentialité**. Switch to English: the policy changes language.
2. **Inscription**: the policy box is required and links to the policy; the messages box is optional. A date of birth less than 14 years ago is refused.
3. Log in as a patient → **Mes données → Mes consentements**: the accepted version and date. Click **Retirer mon consentement**, then **Je veux recevoir les communications**.
4. Log in as the administrator → **Journal d’audit**, action **Consentement retiré** / **Consentement donné**: the two changes, with the patient.
5. Export and deletion: steps in [`docs/demo/d3-law25`](../demo/d3-law25/README.md).

To ask patients to accept a new policy: change the text and `VERSION` in
`web/src/pages/policyText.js`, set `PRIVACY_POLICY_VERSION` on the API to the same value,
and redeploy. Every patient then sees **J'accepte la nouvelle version** in Mes données.

## 4. Privacy impact assessment: transfer outside Québec

Law 25 (art. 17) requires an assessment before personal information is communicated outside
Québec, and a written agreement when the protection is adequate.

| Provider | Where | What it receives | Protection | Residual risk |
|---|---|---|---|---|
| Neon (database) | AWS us-east-1, Virginia, USA | All stored data | Encrypted at rest and in transit (TLS); sensitive fields also encrypted by the application with a key Neon does not have; access by one secret connection string | Low |
| Render (API server) | Virginia, USA | Data while a request is processed; logs (masked emails, no health data) | TLS; secrets in Render settings only | Low |
| Vercel (website) | Global CDN | Public pages only; no personal data stored | Security headers (CSP, HSTS) | Very low |
| Stripe (deposits) | USA / Canada | Card details typed by the patient directly into Stripe; the amount and appointment id | PCI DSS certified; card numbers never reach our systems | Low |
| OpenAI (chatbot) | USA | The visitor's question after masking names, phones, emails and health numbers; public passages | Masking before sending (`app/chatbot/safety.py`); no patient record sent; API data not used for training by default | Medium: free text could still contain health details the visitor typed. Accepted: the chat says not to type health information, and logs are kept 30 days |

Conclusion: the protection is adequate for a student project with fictional data. For a real
clinic, the remaining steps are: signed data processing agreements with each provider
(Neon, Render, Stripe and OpenAI publish standard ones), and hosting the database and the server
in Canada to reduce the transfer.

## 5. Known limitations

- No email provider is connected (B-BKG-08): emails are prepared and logged in masked form, not
  delivered. The consent to electronic messages is recorded and enforced by
  `consent_service.wants_electronic_comms`, but no reminder or newsletter exists yet.
- Anonymizing a health record 5 years after the last visit is done by the administrator; there
  is no automatic job.
- Expired refresh tokens can no longer be used but are not deleted automatically.
- The mobile and desktop apps do not show the policy themselves; it is read on the website.
