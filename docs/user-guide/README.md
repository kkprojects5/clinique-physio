# User guide — Clinique Physio Mont-Royal

One guide per role, with the tasks each person does every day. The clinic and all people in
the screenshots are fictional. Payments are in Stripe test mode (card `4242 4242 4242 4242`).

| Role | Uses | Guide |
|---|---|---|
| Patient | Website https://clinique-physio.vercel.app and the Android app | [patient.md](patient.md) |
| Front desk | Windows desktop app (installer on the [v1.0.0 release](https://github.com/kkprojects5/clinique-physio/releases/tag/v1.0.0)) | [front-desk.md](front-desk.md) |
| Physiotherapist | Website, **Espace thérapeute** | [therapist.md](therapist.md) |
| Administrator | Website, **Administration** | [admin.md](admin.md) |

**Demo video (3 to 5 minutes):** https://github.com/kkprojects5/clinique-physio/releases/download/v1.0.0/clinique-physio-demo.mp4 — one short scenario per role.

## Good to know for everyone

- The website and the apps are in **French and English** (button at the top of the website).
- All times are **Montréal time**, whatever the computer's settings.
- The free hosting sleeps when nobody uses it: the first page can take up to a minute.
- **Staff** log in with their email, password and a **6-digit code** from an authenticator app
  (Microsoft or Google Authenticator). The first login shows a QR code to scan; it is set up
  in the desktop app.
- Never write health information in free-text fields that are not clinical notes (privacy
  requests, time-off reasons, the chatbot).
- Demo accounts are given privately by the clinic (never written in documents).
