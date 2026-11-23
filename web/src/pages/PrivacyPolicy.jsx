import { useTranslation } from 'react-i18next';
import { POLICY } from './policyText';

// The privacy policy, public (Law 25): linked from the footer of every page and from the
// consent box at registration. Same language as the rest of the site.
export default function PrivacyPolicy() {
  const { i18n } = useTranslation();
  const policy = POLICY[i18n.language] || POLICY.fr;
  return (
    <article className="policy">
      <h1>{policy.title}</h1>
      <p className="hint">{policy.updated}</p>
      <p className="notice">{policy.fictional}</p>
      {policy.sections.map((section) => (
        <section key={section.title}>
          <h2>{section.title}</h2>
          <ul>
            {section.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ))}
    </article>
  );
}
