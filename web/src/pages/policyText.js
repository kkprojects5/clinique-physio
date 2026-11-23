// The privacy policy (Law 25, art. 3.2 and 8), in French and English.
// Kept here as data, not in the translation files, because it is long and changes as a whole:
// a new text means a new VERSION, and the API then asks patients to accept it again
// (settings.privacy_policy_version on the API must be changed at the same time).
//
// Fictional clinic: every name, address and email below is invented for a student project.

export const VERSION = '2026-10';

export const POLICY = {
  fr: {
    title: 'Politique de confidentialité',
    updated: 'Version 2026-10, en vigueur depuis le 1er octobre 2026.',
    fictional:
      'Projet étudiant : la clinique, ses employés et les données sont fictifs. Le texte décrit ce que fait réellement le système.',
    sections: [
      {
        title: '1. Qui est responsable',
        items: [
          'Clinique Physio Mont-Royal, 4200, rue Saint-Denis, Montréal (Québec).',
          'Personne responsable de la protection des renseignements personnels : la directrice de la clinique, confidentialite@clinique.example.com, 514-555-0100.',
          'Vous pouvez lui écrire pour toute question, demande ou plainte au sujet de vos renseignements.',
        ],
      },
      {
        title: '2. Ce que nous recueillons et pourquoi',
        items: [
          'Compte : courriel, mot de passe (gardé seulement sous forme hachée, jamais lisible), langue. Pour vous connecter.',
          'Profil : nom, date de naissance, téléphone, personne à joindre en cas d’urgence (facultatif). Pour vous identifier et vous joindre au sujet de vos rendez-vous.',
          'Rendez-vous : physiothérapeute, service, date, statut. Pour gérer l’horaire.',
          'Dossier de santé : notes cliniques et programme d’exercices écrits par votre physiothérapeute. Pour vous soigner. Seuls votre physiothérapeute et vous y avez accès.',
          'Paiements : montants, type et mode de paiement. Pour les dépôts, les remboursements et vos reçus d’assurance. Les numéros de carte ne passent jamais par nos systèmes.',
          'Journal d’accès : qui a consulté votre dossier, quand et d’où. Pour détecter les abus.',
          'Nous demandons seulement ce qui est nécessaire. Nous ne vendons aucun renseignement et ne faisons aucune publicité ciblée ni aucun profilage.',
        ],
      },
      {
        title: '3. Votre consentement',
        items: [
          'À l’inscription, vous acceptez cette politique (obligatoire pour avoir un compte). La version acceptée et la date sont enregistrées.',
          'Les communications électroniques non essentielles (rappels, nouvelles de la clinique) sont facultatives. Vous pouvez donner ou retirer ce consentement en tout temps dans « Mes données ».',
          'Les messages nécessaires au service que vous avez demandé (confirmation de rendez-vous, réinitialisation du mot de passe, réponse à une demande) ne dépendent pas de ce choix.',
          'Si cette politique change, nous vous demandons de lire et d’accepter la nouvelle version.',
          'Les comptes en ligne sont réservés aux personnes de 14 ans et plus. Pour un enfant de moins de 14 ans, le parent ou le tuteur communique avec la clinique.',
        ],
      },
      {
        title: '4. Qui voit vos renseignements',
        items: [
          'Votre physiothérapeute : votre dossier de santé et vos rendez-vous avec lui ou elle.',
          'L’accueil : vos coordonnées, vos rendez-vous et vos paiements, jamais vos notes cliniques.',
          'L’administration : les comptes, les demandes liées à la vie privée et le journal d’accès, jamais vos notes cliniques.',
          'Nos fournisseurs, seulement pour le service qu’ils rendent (section 5). Personne d’autre, sauf si la loi l’exige.',
        ],
      },
      {
        title: '5. Fournisseurs et hébergement hors Québec',
        items: [
          'Render (serveur de l’application) et Neon (base de données) : hébergement aux États-Unis (Virginie).',
          'Vercel : le site Web public.',
          'Stripe : le paiement en ligne des dépôts. Stripe reçoit votre carte directement; nous recevons seulement le résultat du paiement.',
          'OpenAI : l’assistant virtuel. Seule la question, sans votre nom, téléphone, courriel ni numéro d’assurance maladie (masqués avant l’envoi), est transmise. Aucune donnée de votre dossier n’est envoyée.',
          'Avant cette communication hors Québec, la clinique a évalué les risques (évaluation des facteurs relatifs à la vie privée) : chiffrement en transit et au repos, accès limité, contrats des fournisseurs.',
        ],
      },
      {
        title: '6. Combien de temps nous gardons vos renseignements',
        items: [
          'Dossier de santé : 5 ans après la dernière visite, puis anonymisé.',
          'Paiements : tant que le dossier lié existe, pour les reçus et la comptabilité.',
          'Conversations avec l’assistant virtuel : 30 jours (déjà masquées).',
          'Sessions de connexion : expirent après 7 jours au plus (15 minutes d’inactivité pour le personnel); une session expirée ne sert plus à rien.',
          'Consentements, demandes et journal d’accès : gardés comme preuve que la clinique a respecté la loi.',
        ],
      },
      {
        title: '7. Sécurité',
        items: [
          'Connexions chiffrées (HTTPS), mots de passe hachés, renseignements sensibles chiffrés dans la base de données.',
          'Double authentification pour le personnel; chaque employé voit seulement ce dont il a besoin.',
          'En cas d’incident de confidentialité présentant un risque de préjudice sérieux, nous avisons la Commission d’accès à l’information et les personnes touchées. Tous les incidents sont inscrits dans un registre.',
        ],
      },
      {
        title: '8. Vos droits',
        items: [
          'Voir vos renseignements, en obtenir une copie dans un format numérique courant (JSON) et les faire transmettre à une autre organisation.',
          'Faire corriger un renseignement inexact ou incomplet.',
          'Retirer un consentement facultatif, ou demander la suppression de votre compte. Le dossier de santé est alors gardé 5 ans après la dernière visite, comme l’exige l’ordre professionnel, puis anonymisé.',
          'Faites votre demande dans « Mes données » (après connexion) ou par courriel à la personne responsable. Nous répondons dans un délai de 30 jours.',
          'Si vous n’êtes pas satisfait de notre réponse, vous pouvez porter plainte à la Commission d’accès à l’information du Québec (cai.gouv.qc.ca).',
        ],
      },
      {
        title: '9. Témoins (cookies) et stockage dans le navigateur',
        items: [
          'Un seul témoin, nécessaire à la connexion : il garde votre session ouverte. Il ne peut pas être lu par le site ni servir au suivi.',
          'Le navigateur retient votre langue (français ou anglais).',
          'Aucun témoin publicitaire ou de mesure d’audience. Aucune technologie de localisation ou de profilage.',
        ],
      },
    ],
  },
  en: {
    title: 'Privacy policy',
    updated: 'Version 2026-10, in effect since October 1, 2026.',
    fictional:
      'Student project: the clinic, its staff and the data are fictional. The text describes what the system really does.',
    sections: [
      {
        title: '1. Who is responsible',
        items: [
          'Clinique Physio Mont-Royal, 4200 Saint-Denis Street, Montréal, Québec.',
          'Person in charge of the protection of personal information: the clinic director, confidentialite@clinique.example.com, 514-555-0100.',
          'You can write to her with any question, request or complaint about your information.',
        ],
      },
      {
        title: '2. What we collect and why',
        items: [
          'Account: email, password (kept only in hashed form, never readable), language. To log you in.',
          'Profile: name, date of birth, phone, emergency contact (optional). To identify you and reach you about your appointments.',
          'Appointments: physiotherapist, service, date, status. To manage the schedule.',
          'Health record: clinical notes and exercise program written by your physiotherapist. To treat you. Only your physiotherapist and you can see it.',
          'Payments: amounts, type and payment method. For deposits, refunds and your insurance receipts. Card numbers never go through our systems.',
          'Access log: who opened your file, when and from where. To detect abuse.',
          'We ask only for what is needed. We sell no information and do no targeted advertising or profiling.',
        ],
      },
      {
        title: '3. Your consent',
        items: [
          'When you register, you accept this policy (required to have an account). The version accepted and the date are recorded.',
          'Non-essential electronic messages (reminders, clinic news) are optional. You can give or withdraw this consent at any time in "My data".',
          'Messages needed for a service you asked for (booking confirmation, password reset, answer to a request) do not depend on this choice.',
          'If this policy changes, we ask you to read and accept the new version.',
          'Online accounts are for people aged 14 or more. For a child under 14, the parent or tutor contacts the clinic.',
        ],
      },
      {
        title: '4. Who sees your information',
        items: [
          'Your physiotherapist: your health record and your appointments with them.',
          'Front desk: your contact details, appointments and payments, never your clinical notes.',
          'Administration: accounts, privacy requests and the access log, never your clinical notes.',
          'Our providers, only for the service they give (section 5). Nobody else, unless the law requires it.',
        ],
      },
      {
        title: '5. Providers and hosting outside Québec',
        items: [
          'Render (application server) and Neon (database): hosted in the United States (Virginia).',
          'Vercel: the public website.',
          'Stripe: online payment of deposits. Stripe receives your card directly; we receive only the payment result.',
          'OpenAI: the virtual assistant. Only the question is sent, with your name, phone, email and health insurance number masked first. No data from your record is sent.',
          'Before this communication outside Québec, the clinic assessed the risks (privacy impact assessment): encryption in transit and at rest, limited access, provider contracts.',
        ],
      },
      {
        title: '6. How long we keep your information',
        items: [
          'Health record: 5 years after the last visit, then anonymized.',
          'Payments: as long as the related record exists, for receipts and accounting.',
          'Conversations with the virtual assistant: 30 days (already masked).',
          'Login sessions: expire after 7 days at most (15 minutes without activity for staff); an expired session can no longer be used.',
          'Consents, requests and the access log: kept as proof that the clinic followed the law.',
        ],
      },
      {
        title: '7. Security',
        items: [
          'Encrypted connections (HTTPS), hashed passwords, sensitive information encrypted in the database.',
          'Two-factor authentication for staff; each employee sees only what they need.',
          'If a confidentiality incident presents a risk of serious injury, we notify the Commission d’accès à l’information and the people affected. Every incident is recorded in a register.',
        ],
      },
      {
        title: '8. Your rights',
        items: [
          'See your information, get a copy in a common digital format (JSON) and have it sent to another organization.',
          'Have inaccurate or incomplete information corrected.',
          'Withdraw an optional consent, or ask for your account to be deleted. The health record is then kept 5 years after the last visit, as the professional order requires, then anonymized.',
          'Make your request in "My data" (after logging in) or by email to the person in charge. We answer within 30 days.',
          'If you are not satisfied with our answer, you can complain to the Commission d’accès à l’information du Québec (cai.gouv.qc.ca).',
        ],
      },
      {
        title: '9. Cookies and browser storage',
        items: [
          'One cookie only, needed to log in: it keeps your session open. The site cannot read it and it is not used for tracking.',
          'Your browser remembers your language (French or English).',
          'No advertising or analytics cookies. No location or profiling technology.',
        ],
      },
    ],
  },
};
