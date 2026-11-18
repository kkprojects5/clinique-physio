"""Safety rules checked BEFORE any search or AI call (B-BOT-02, B-BOT-03).

1. Emergency signs (chest pain, trouble breathing, suicidal thoughts...): the only answer is
   to call 911, Info-Santé 811 or the 9-8-8 crisis line. Nothing else is said.
2. Requests for a diagnosis, a treatment or medication advice: polite refusal, with the
   suggestion to book an evaluation or call Info-Santé 811. The bot never gives medical advice.
3. Attempts to change the bot's instructions (prompt injection): refused, nothing revealed.
4. Questions about a person or an account: refused; the bot has no access to patient data.

Personal details typed by the visitor (email, phone, health insurance number, card number,
postal code) are masked before the question is logged or sent to an AI provider (Law 25).

The rules are simple patterns on the text without accents, in French and English. They are
tested on the evaluation set (eval/chatbot_eval.json): 100% of emergencies and diagnosis
requests must be caught (objective O7).
"""

import re
from enum import StrEnum

from app.chatbot.text import fold


class Kind(StrEnum):
    ANSWER = "answer"
    UNKNOWN = "unknown"
    EMERGENCY = "emergency"
    MEDICAL = "medical"  # diagnosis or treatment request: refused
    INJECTION = "injection"  # attempt to change the instructions: refused
    PRIVATE = "private"  # question about a person or an account: refused


def _any(*patterns: str) -> re.Pattern[str]:
    return re.compile("|".join(f"(?:{p})" for p in patterns))


EMERGENCY = _any(
    r"(douleur|mal|serrement|pression)s? (a|dans) la poitrine",
    r"chest (pain|pressure|tightness)",
    r"pain in (my|the) chest",
    r"(peux|arrive) (pas|plus) (a )?respirer",
    r"(difficulte|mal)s? a respirer",
    r"(can'?t|cannot|can not) breathe",
    r"(trouble|difficulty) breathing",
    r"short(ness)? of breath",
    r"suicid",
    r"me tuer",
    r"en finir avec (la|ma) vie",
    r"kill myself",
    r"end my life",
    r"(me faire|se faire) du mal",
    r"hurt myself",
    r"self[- ]harm",
    r"perte de (conscience|connaissance)",
    r"perdu connaissance",
    r"evanoui",
    r"unconscious",
    r"passed out",
    r"paralys",
    r"(sens|sent) plus (mes|ses|ma|sa) (jambe|bras|visage)",
    r"(can'?t|cannot) feel (my|his|her) (legs?|arms?|face)",
    r"engourdissement soudain",
    r"sudden(ly)? numb",
    r"\bavc\b",
    r"\bstroke\b",
    r"crise cardiaque",
    r"heart attack",
    r"saign\w* (beaucoup|abondamment|sans arret)",
    r"bleeding (a lot|heavily|badly)",
    r"(controle|contrôle) (de la vessie|des intestins)",
    r"(bladder|bowel) control",
    r"c'?est une urgence",
    r"urgence (medicale|vitale)",
    r"(it'?s|this is) an emergency",
    r"medical emergency",
    r"\b911\b",
)

_CONDITIONS = (
    r"(entorse|dechirure|fracture|hernie|tendinite|bursite|sciatique|arthrose|foulure|"
    r"sprain|tear|torn|fracture|broken|hernia|herniated|tendinitis|tendonitis|bursitis|sciatica|"
    r"arthritis|strain)"
)
_MEDICATION = (
    r"(medicament|medication|ibuprof|advil|motrin|tylenol|acetaminoph|anti-?inflam|painkiller|"
    r"antidouleur|cortisone|pilule|\bpills?\b|naproxen|aleve|aspirin|relaxant)"
)

MEDICAL = _any(
    r"diagnos",
    r"qu'?est[- ]ce que j'?ai\b",
    r"qu'?est[- ]ce que (c'?est|ca peut etre)\b.{0,40}(mal|douleur|bosse|enflure)",
    r"what'?s wrong with (me|my)",
    r"what is wrong with (me|my)",
    r"what do i have\b",
    r"(est-ce|c'?est) grave",
    r"is (it|this|that) serious",
    r"(ai-je|j'?ai peut-etre|est-ce (que c'?est )?une?|c'?est une?|serait-ce une?) "
    rf".{{0,20}}{_CONDITIONS}",
    rf"(do i have|is (it|this|that)|could (it|this) be|have i got|did i) .{{0,20}}{_CONDITIONS}",
    rf"(prendre|take|taking|dose|dosage|combien de|how (much|many)) .{{0,30}}{_MEDICATION}",
    rf"{_MEDICATION}.{{0,40}}(prendre|take|ok|safe|dose|aide|help|bon)",
    r"(glace|chaleur|froid|ice|heat|cold)\b.{0,30}\b(ou|or)\b.{0,20}"
    r"(glace|chaleur|froid|ice|heat|cold)",
    r"(dois|devrais|puis|should|can|could)[- ]?(je|i) (mettre|appliquer|put|apply|use) "
    r".{0,10}(glace|chaleur|ice|heat)",
    r"(quel|quels|quelle|quelles|which|what) (exercice|etirement|exercise|stretch)\w*.{0,40}"
    r"(pour|for|contre|devrais|dois|should)",
    r"(comment|how (do|can|should) i|how to) "
    r"(soigner|traiter|guerir|soulager|treat|heal|cure|relieve|fix|get rid)",
    r"(soigner|traiter|guerir|soulager) (mon|ma|mes)\b",
    r"\b(treat|heal|cure|relieve|fix) my\b",
    r"(j'?ai mal|douleur|mal (au|a la|aux|a l')|enfle|pain|hurts?|ache|swollen|sore)"
    r".{0,60}(que (dois-je|devrais-je|faire)|quoi faire|what (should|can|do) i do)",
    r"(dois-je|devrais-je|should i) (aller )?(voir|consulter|see|go to) (un |une |a |the )?"
    r"(medecin|docteur|doctor|hopital|hospital|urgence|er)\b",
    r"(arreter|stop|continuer|continue) (mes|my) "
    r"(exercice|exercise|traitement|treatment|medicament|medication)",
)

INJECTION = _any(
    r"ignore[sz]? .{0,30}(instructions|consignes|regles|rules|directives)",
    r"oublie[sz]? .{0,30}(instructions|consignes|regles|rules|directives)",
    r"disregard .{0,30}(instructions|rules)",
    r"(system|systeme) ?prompt",
    r"prompt (systeme|system|initial)",
    r"(reveal|show|print|repeat|display|montre|affiche|revele|repete|donne)\w* .{0,30}"
    r"(instructions|prompt|consignes|regles|configuration)",
    r"you are now",
    r"tu es maintenant",
    r"vous etes maintenant",
    r"\bact as\b",
    r"agis comme",
    r"comporte-toi comme",
    r"pretend (to be|you)",
    r"fais semblant",
    r"jailbreak",
    r"developer mode",
    r"mode developpeur",
    r"\bdan mode\b",
    r"</?(system|documents?|question|instructions?)>",
    r"new instructions",
    r"nouvelles? (instructions|consignes|regles)",
    r"from now on",
    r"a partir de maintenant",
)

# A full name after "de/of/for" next to a personal-data word: "le téléphone de Marie Gagnon".
_PERSON_DATA = (
    r"(telephone|phone|numero|number|adresse|address|courriel|email|dossier|file|record|"
    r"rendez-vous|appointments?|notes?|diagnostic|diagnosis|date de naissance|birth)"
)
_NAME = r"[A-ZÉÈ][a-zéèêëïîôç]+(?:-[A-ZÉÈ][a-zéèêëïîôç]+)? [A-ZÉÈ][a-zéèêëïîôç]+"
PRIVATE_ORIGINAL = re.compile(
    rf"(?i:{_PERSON_DATA})\s+(?i:de|d'|du|of|for)\s*(?i:m\.|mme|mr\.?|mrs\.?|ms\.?|monsieur|madame)?\s*{_NAME}"
    rf"|{_NAME}\s+(?i:est-(?:il|elle)|is)\s+(?i:un|une|a)\s+(?i:patient|patiente|client)"
    rf"|(?i:is|est-ce que)\s+{_NAME}\s+(?i:est\s+)?(?i:a|an|un|une)\s+(?i:patient|patiente|client)"
)
PRIVATE = _any(
    r"(liste|list) (des|of|of the) (patients|clients)",
    r"(qui sont|who are) (les|the|your) (patients|clients)",
    r"(mes|my) (resultats|results|notes cliniques|clinical notes|diagnostic|diagnosis|"
    r"dossier medical|medical record)",
)

REDACTIONS = [
    (re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+"), "[courriel/email]"),
    (re.compile(r"\b[A-Za-z]{4}\s?\d{4}\s?\d{4}\b"), "[RAMQ]"),  # health insurance number
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[carte/card]"),
    (re.compile(r"(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}(?!\d)"), "[tél/phone]"),
    (re.compile(r"\b[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d\b"), "[code postal/postal code]"),
]


def redact(text: str) -> str:
    """Mask personal details before the question is stored or sent anywhere."""
    for pattern, label in REDACTIONS:
        text = pattern.sub(label, text)
    return text


def classify(question: str) -> Kind | None:
    """The refusal kind for this question, or None if it is a practical question.

    Emergencies come first: "I have chest pain, what should I take?" is an emergency.
    """
    text = fold(question)
    if EMERGENCY.search(text):
        return Kind.EMERGENCY
    if INJECTION.search(text):
        return Kind.INJECTION
    if MEDICAL.search(text):
        return Kind.MEDICAL
    if PRIVATE.search(text) or PRIVATE_ORIGINAL.search(question):
        return Kind.PRIVATE
    return None


def unsafe_output(text: str) -> bool:
    """Check an AI-written answer: it must not look like medical advice or leak instructions."""
    folded = fold(text)
    return bool(
        MEDICAL.search(folded)
        or re.search(r"(system prompt|prompt systeme|mes instructions|my instructions)", folded)
        or re.search(rf"(prenez|take|try|essayez) .{{0,30}}{_MEDICATION}", folded)
    )


MESSAGES = {
    Kind.EMERGENCY: {
        "fr": (
            "Si c'est une urgence, appelez le 911 maintenant. Pour parler à une infirmière, "
            "appelez Info-Santé au 811. En cas de détresse ou d'idées suicidaires, appelez ou "
            "textez le 9-8-8, 24 heures sur 24."
        ),
        "en": (
            "If this is an emergency, call 911 now. To talk to a nurse, call Info-Santé at 811. "
            "If you are in distress or thinking about suicide, call or text 9-8-8, 24 hours a day."
        ),
    },
    Kind.MEDICAL: {
        "fr": (
            "Je ne peux pas donner d'avis médical, de diagnostic ni de conseil sur un traitement "
            "ou un médicament. Un ou une physiothérapeute pourra vous évaluer : vous pouvez "
            "réserver une évaluation initiale en ligne. Pour un conseil de santé rapide, appelez "
            "Info-Santé au 811. En cas d'urgence, appelez le 911."
        ),
        "en": (
            "I can't give medical advice, a diagnosis or advice on a treatment or medication. "
            "A physiotherapist can assess you: you can book an initial evaluation online. For "
            "quick health advice, call Info-Santé at 811. In an emergency, call 911."
        ),
    },
    Kind.INJECTION: {
        "fr": (
            "Je ne peux pas changer mes consignes. Je réponds seulement aux questions pratiques "
            "sur la clinique : heures, adresse, tarifs, réservation, annulation, assurances."
        ),
        "en": (
            "I can't change my instructions. I only answer practical questions about the clinic: "
            "hours, address, prices, booking, cancellation, insurance."
        ),
    },
    Kind.PRIVATE: {
        "fr": (
            "Je n'ai accès à aucun dossier ni à aucun compte, et je ne donne pas de renseignements "
            "sur une personne. Pour vos rendez-vous, connectez-vous au site ; pour le reste, "
            "appelez l'accueil au 514-555-0100."
        ),
        "en": (
            "I have no access to any file or account, and I don't give information about a "
            "person. For your appointments, log in to the website; for anything else, call the "
            "front desk at 514-555-0100."
        ),
    },
    Kind.UNKNOWN: {
        "fr": (
            "Je n'ai pas trouvé la réponse dans les documents de la clinique. Je peux répondre "
            "aux questions sur les heures, l'adresse, le stationnement, les tarifs, la "
            "réservation, l'annulation et les assurances. Pour le reste, appelez l'accueil au "
            "514-555-0100."
        ),
        "en": (
            "I didn't find the answer in the clinic's documents. I can answer questions about "
            "hours, address, parking, prices, booking, cancellation and insurance. For anything "
            "else, call the front desk at 514-555-0100."
        ),
    },
}
