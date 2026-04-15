#!/usr/bin/env python3
"""Multi-provider AI abstraction for LoveSpark message generation."""

import json
import os
import urllib.request

SYSTEM_PROMPT = (
    "Tu es un ami bienveillant et empathique. Tu ecris un message d'encouragement "
    "personnalise pour {name}.\n"
    "\n"
    "INTENTION DE BASE (ligne directrice immuable):\n"
    "- Reconnaitre les efforts invisibles que la personne fait au quotidien\n"
    "- Rappeler que quelqu'un voit ce qu'elle fait et tient a elle\n"
    "- Offrir du reconfort face aux moments difficiles (travail, tristesse, periodes compliquees)\n"
    "- Faire ressentir qu'elle est vue, importante, et que sa presence compte\n"
    "\n"
    "CONTRAINTES DE FORME:\n"
    "- Court: 3 a 4 phrases, environ 50 mots\n"
    "- En francais, tutoiement, ton intime et doux\n"
    "- Chaleureux et sincere, pas de cliches creux\n"
    "- Different a chaque fois (varie le style, les metaphores, l'angle)\n"
    "\n"
    "NEUTRALITE DE GENRE (IMPERATIF):\n"
    "Tu ne connais PAS le genre de la personne. N'emploie AUCUN adjectif accorde "
    "au masculin ou au feminin pour la decrire. Evite: \"fier/fiere\", \"heureux/heureuse\", "
    "\"fort/forte\", \"beau/belle\", \"courageux/courageuse\", \"content/contente\", "
    "\"seul/seule\", \"important/importante\", etc.\n"
    "A la place, utilise:\n"
    "- Des noms: \"ton courage\", \"ta force\", \"ta douceur\", \"ta presence\"\n"
    "- Des verbes: \"tu avances\", \"tu tiens bon\", \"tu rayonnes\", \"tu comptes\"\n"
    "- Des formulations neutres: \"je t'admire\", \"ce que tu fais compte\", \"tu importes\"\n"
    "Relis-toi: si un mot change d'orthographe selon le genre, reformule.\n"
    "\n"
    "{sign_block}"
    "PLACEMENT DU PRENOM:\n"
    "Mentionne le prenom {name} une fois, integre naturellement au milieu d'une phrase. "
    "Ne commence PAS par \"Cher/Chere {name}\" ni \"Bonjour {name}\" ni \"{name},\".\n"
    "\n"
    "FORMAT DE REPONSE:\n"
    "Reponds UNIQUEMENT avec le message, sans guillemets, sans explication, sans introduction."
)

SIGN_DISPLAY = {
    "belier": "Belier",
    "taureau": "Taureau",
    "gemeaux": "Gemeaux",
    "cancer": "Cancer",
    "lion": "Lion",
    "vierge": "Vierge",
    "balance": "Balance",
    "scorpion": "Scorpion",
    "sagittaire": "Sagittaire",
    "capricorne": "Capricorne",
    "verseau": "Verseau",
    "poissons": "Poissons",
}

VALID_SIGNS = set(SIGN_DISPLAY.keys())

# Profils psychologiques par signe — injectes dans le prompt pour que l'IA
# puisse incarner subtilement l'essence du signe sans le nommer.
# Sources : astrologie psychologique (Liz Greene, astro-psycho francophone).
SIGN_PROFILES = {
    "belier": (
        "Forces discretes: Il lance ce que les autres n'osent pas commencer. "
        "Sa sincerite brute est un cadeau rare. Il se releve vite apres les chutes. "
        "Il protege ceux qu'il aime sans toujours le dire avec des mots.\n"
        "Luttes interieures: Demarre fort et s'epuise avant la ligne d'arrivee. "
        "Panique silencieusement a l'idee d'etre ordinaire. L'impatience cache la peur de stagner. "
        "Se sent souvent seul dans son elan, les autres peinent a suivre.\n"
        "Mots et images qui resonnent: etincelle, breche, premier pas, elan, souffle, "
        "printemps, depart, territoire, conquete interieure, feu qui s'allume.\n"
        "Pieges: ne pas lui dire de ralentir ou d'etre patient (sonne comme une punition). "
        "Eviter le ton doux et condescendant — il a besoin d'etre interpelle, pas couve. "
        "Pas de message trop long et contemplatif."
    ),
    "taureau": (
        "Forces discretes: Un roc pour ceux qu'il aime, une presence stable que tout le monde "
        "cherche. Sa lenteur est de la profondeur, pas de la paresse. Il construit du durable. "
        "Sensibilite fine aux plaisirs simples (lumiere, texture, gout).\n"
        "Luttes interieures: Resiste au changement par peur de detruire ce qu'il a mis du temps a batir. "
        "Peur profonde et ancienne du manque, affectif autant que materiel. Accumule les frustrations "
        "en silence jusqu'a l'eruption. Son entetement protege ses fondations.\n"
        "Mots et images qui resonnent: racines, ancrage, patience, recolte, douceur, construire, "
        "sol, texture, duree, seve, digne de confiance.\n"
        "Pieges: ne pas lui demander de tout lacher ou de changer radicalement. Eviter les envolees "
        "lyriques trop abstraites — il a besoin de concret, de tangible."
    ),
    "gemeaux": (
        "Forces discretes: Connecte les idees et les gens avec une fluidite rare. Voit plusieurs angles "
        "en meme temps. S'adapte sans perdre sa vivacite. Son humour cache une intelligence aigue. "
        "Il est le pont entre des mondes qui ne se parleraient pas sans lui.\n"
        "Luttes interieures: La dispersion est sa souffrance — commencer sans finir. Se sent parfois "
        "superficiel alors qu'il est traverse par des questions profondes. La coherence de soi lui echappe, "
        "il se sent different selon les jours. Craint d'etre incompris parce qu'il ne se comprend pas toujours.\n"
        "Mots et images qui resonnent: liens, pont, souffle, voix, carrefour, idee en mouvement, tisser, "
        "curieux, vivant, scintillant, resonance.\n"
        "Pieges: ne pas lui demander de choisir ou de se stabiliser. Eviter la lourdeur et la solennite — "
        "il a besoin de legerete qui va loin, pas de profondeur pesante."
    ),
    "cancer": (
        "Forces discretes: Nourrit les autres d'une facon si naturelle qu'il ne realise pas que c'est rare. "
        "Intuition quasi-psychique sur l'etat emotionnel des gens. Derriere la douceur, une ferocite protectrice. "
        "Cree des espaces ou les gens se sentent en securite. Memoire affective d'une richesse rare.\n"
        "Luttes interieures: Peur de l'abandon ancienne et profonde, anticipe les rejets qui n'ont pas eu lieu. "
        "Prend tout personnellement. Se retracte dans sa carapace quand il est blesse. Sa generosite peut "
        "l'epuiser s'il ne se protege pas.\n"
        "Mots et images qui resonnent: foyer, maree, douceur, soin, memoire, lune, refuge, tendresse, "
        "source, protection, enracinement affectif.\n"
        "Pieges: ne pas minimiser ni rationaliser ses emotions. Ne jamais lui dire d'etre moins sensible "
        "ou de prendre du recul — cela le coupe. Pas de ton froid ou trop cerebral."
    ),
    "lion": (
        "Forces discretes: Generosite sincere, non calculee — il eleve les autres autant qu'il brille. "
        "La chaleur qu'il rayonne change l'atmosphere meme s'il n'en est pas conscient. Courage d'exister "
        "pleinement qui inspire les autres. Loyaute absolue une fois accordee.\n"
        "Luttes interieures: Sensibilite disproportionnee a la critique — une attaque de son travail sonne "
        "comme une attaque de son etre. A integre l'idee qu'il doit meriter l'amour, s'epuise a briller. "
        "Peur reelle de disparaitre s'il ne performe plus. Vulnerable aux flatteries vides.\n"
        "Mots et images qui resonnent: lumiere, chaleur, coeur, rayonner, noblesse, creer, feu solaire, "
        "offrande, courage d'exister, don, flamme.\n"
        "Pieges: jamais de flatterie creuse, il la detecte. Ne pas reduire son besoin de reconnaissance a "
        "de la vanite. Pas de ton qui suggere qu'il devrait etre plus humble."
    ),
    "vierge": (
        "Forces discretes: Devouement silencieux, courage quotidien invisible. Percoit les nuances que les "
        "autres ratent. Transforme le chaos en ordre, un vrai talent alchimique. Porte des responsabilites "
        "que personne d'autre ne prendrait, sans se plaindre.\n"
        "Luttes interieures: Se critique dix fois plus durement qu'elle ne critique les autres. Perfectionnisme "
        "qui vient de l'anxiete d'etre decouvert inadequat. Anticipe mentalement les catastrophes pour les "
        "prevenir — ce qui l'epuise. Peur existentielle d'etre inutile.\n"
        "Mots et images qui resonnent: soin, precision, invisible mais essentiel, ordre, discernement, "
        "servir, alchimie du quotidien, racines souterraines, affuter, clarte, artisanat.\n"
        "Pieges: ne jamais dire de se detendre ou d'arreter de tout analyser (recu comme reproche). "
        "Eviter les messages trop vagues ou abstraits. Pas de flatterie gonflee."
    ),
    "balance": (
        "Forces discretes: Sens de la justice qui est une force morale reelle, pas du people-pleasing. "
        "Cree des espaces ou les gens se sentent entendus. Voit tous les cotes d'une situation. "
        "Son esthetisme est un langage spirituel, une recherche d'harmonie.\n"
        "Luttes interieures: Indecision chronique par peur de briser l'equilibre par un mauvais choix. "
        "Se perd dans le reflet des autres parce qu'elle cherche son identite dans les relations. "
        "Peur profonde de n'exister que dans le regard d'autrui. La confrontation lui coute enormement.\n"
        "Mots et images qui resonnent: equilibre, harmonie, lien, justice, beaute interieure, pont, "
        "equinoxe, justesse, ecoute, tissage, accord.\n"
        "Pieges: jamais lui dire de juste choisir ou de cesser de plaire aux autres. Eviter les messages "
        "trop tranches. Respecter la nuance."
    ),
    "scorpion": (
        "Forces discretes: Voit ce que les autres ne voient pas — motivations cachees, non-dits, verites "
        "que personne n'ose nommer. Traverse la destruction et se reconstruit, puissance alchimique reelle. "
        "Loyaute d'une profondeur rare une fois accordee. Transforme la souffrance en sagesse.\n"
        "Luttes interieures: Peur ancienne de la trahison, teste les gens. Mefiance qui est une armure "
        "contre une vulnerabilite reelle. Controle tout parce que perdre le controle lui semble dangereux. "
        "L'impermanence et la perte le hantent.\n"
        "Mots et images qui resonnent: profondeur, metamorphose, phenix, alchimie, verite nue, peau qui mue, "
        "renaissance, feu souterrain, abime, revelation, descente, transmutation.\n"
        "Pieges: pas de legerete superficielle, il detecte l'inauthenticite. Eviter les formules convenues "
        "sur le lacher-prise. Ne pas minimiser ce qu'il traverse."
    ),
    "sagittaire": (
        "Forces discretes: Transmet de l'espoir authentique, pas de la naivete. Synthetise des experiences "
        "disparates en sens universel, talent philosophique rare. Generosite d'esprit contagieuse. "
        "Va la ou les autres ont peur d'aller, physiquement comme intellectuellement.\n"
        "Luttes interieures: Optimisme permanent qui cache un doute existentiel fui dans le mouvement. "
        "Preche parfois pour se convaincre lui-meme. Peur de l'enfermement (physique, emotionnel) le pousse "
        "a fuir l'intimite. Instabilite chronique qui est une souffrance sous l'apparence d'aventure.\n"
        "Mots et images qui resonnent: horizon, fleche decochee, sens, voyage, verite, expansion, "
        "souffle large, altitude, carte, decouverte, feu de camp.\n"
        "Pieges: ne pas lui conseiller de ralentir ou de s'ancrer (vecu comme limitation). Ne pas reduire "
        "son elan a de l'imprudence. Pas de ton trop serieux ou pesant."
    ),
    "capricorne": (
        "Forces discretes: Porte des charges que d'autres ne pourraient pas soutenir, souvent sans se plaindre. "
        "Sa patience est de la foi en la duree. Construit pour durer. Maturite acquise par l'epreuve, "
        "une richesse qui a coute cher. Loyaute discrete d'une profondeur que peu valorisent.\n"
        "Luttes interieures: Vigilance saturnienne epuisante. Peur profonde de laisser une trace insignifiante, "
        "de disparaitre sans avoir rien construit d'utile. Supprime ses emotions pour maintenir la maitrise — "
        "elles s'accumulent. Sensibilite cachee sous l'austerite, souvent non reconnue.\n"
        "Mots et images qui resonnent: sommet, pierre, batir, patience, duree, hiver qui prepare le printemps, "
        "altitude, fondation, memoire longue, heritage, dignite, resilience.\n"
        "Pieges: jamais lui dire de se laisser aller ou d'etre plus spontane (incompatible avec son essence). "
        "Eviter les encouragements festifs ou euphoriques. Pas de legerete excessive."
    ),
    "verseau": (
        "Forces discretes: Voit des solutions que personne d'autre n'a imaginees. Comprehension intuitive des "
        "dynamiques collectives, don souvent invisible. Sa difference n'est pas de l'excentricite vaine — c'est "
        "une avance sur l'epoque. Sert une cause plus grande que lui avec sincerite.\n"
        "Luttes interieures: Solitude du visionnaire, reelle et douloureuse — etre compris trop tard ou pas du tout. "
        "Detachement emotionnel qui protege mais cree une distance dans l'intime. Parait froid alors qu'il "
        "ressent profondement. Peur de perdre son autonomie le coupe parfois des liens necessaires.\n"
        "Mots et images qui resonnent: courant, collectif, avenir, eclair, vision, rebelle utile, onde, "
        "fracture creatrice, futur, relier, electricite.\n"
        "Pieges: jamais lui demander de se conformer ou de rentrer dans le moule. Eviter le sentimental ou "
        "le larmoyant — il se ferme. Pas de ton nostalgique."
    ),
    "poissons": (
        "Forces discretes: Sa presence calme les conflits, forme de guerison qu'il ne voit pas lui-meme. "
        "Transforme la souffrance en art ou en empathie, puissance alchimique rare. Percoit ce qui n'est pas dit. "
        "Son imagination est un outil de comprehension du reel, pas une fuite.\n"
        "Luttes interieures: Peur centrale de la dissolution de soi — se perdre dans les autres, l'emotion, "
        "l'ideal. Frontiere poreuse avec le monde, epuisante. Dit oui quand il devrait dire non, par peur de blesser. "
        "Doute constant sur sa propre valeur, comme si sa sensibilite etait une faiblesse.\n"
        "Mots et images qui resonnent: ocean, profondeur, flux, reve eveille, passeur, invisible mais reel, "
        "dissolution creatrice, lumiere sous l'eau, chrysalide, soin, guerison.\n"
        "Pieges: ne pas lui demander d'etre plus rationnel ou de revenir les pieds sur terre (recu comme rejet). "
        "Eviter les messages trop pragmatiques. Ne pas effacer la dimension symbolique."
    ),
}


PROVIDER_CONFIGS = {
    "anthropic": {
        "url": "https://api.anthropic.com/v1/messages",
        "default_model": "claude-3-haiku-20240307",
        "format": "anthropic",
    },
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "default_model": "gpt-4o-mini",
        "format": "openai",
    },
    "kimi": {
        "url": "https://api.moonshot.cn/v1/chat/completions",
        "default_model": "moonshot-v1-8k",
        "format": "openai",
    },
}


def get_ai_message(name: str, sign: str | None = None) -> str | None:
    """Generate an inspirational message via AI. Returns None if the AI is
    unavailable or fails — the caller is responsible for surfacing an error."""
    provider = os.environ.get("AI_PROVIDER", "").lower().strip()
    api_key = os.environ.get("AI_API_KEY", "").strip()
    model = os.environ.get("AI_MODEL", "").strip()

    if not provider or not api_key:
        return None

    config = PROVIDER_CONFIGS.get(provider)
    if not config:
        return None

    if not model:
        model = config["default_model"]

    sign_block = ""
    if sign and sign in SIGN_DISPLAY:
        profile = SIGN_PROFILES.get(sign, "")
        sign_block = (
            f"PROFIL DE LA PERSONNE (signe {SIGN_DISPLAY[sign]}) — ne nomme JAMAIS le signe:\n"
            f"{profile}\n"
            "Incarne subtilement l'essence de ce profil dans le ton, les images et le choix des mots. "
            "N'enumere pas ces traits et ne les recopie pas; laisse-les transparaitre. "
            "Pioche dans le champ lexical propose si cela sonne juste. "
            "Respecte scrupuleusement la regle de neutralite de genre ci-dessus.\n\n"
        )

    prompt = SYSTEM_PROMPT.replace("{name}", name).replace("{sign_block}", sign_block)
    user_hint = f"Ecris maintenant le message pour {name}."
    if sign and sign in SIGN_DISPLAY:
        user_hint += f" Laisse transparaitre l'esprit du signe {SIGN_DISPLAY[sign]} sans le nommer."

    try:
        if config["format"] == "anthropic":
            result = _call_anthropic(config["url"], api_key, model, prompt, user_hint)
        else:
            result = _call_openai_compatible(config["url"], api_key, model, prompt, user_hint)
        text = (result or "").strip()
        return text or None
    except Exception:
        return None


def _call_anthropic(url: str, api_key: str, model: str, system_prompt: str, user_hint: str) -> str:
    """Call the Anthropic Messages API."""
    payload = json.dumps({
        "model": model,
        "max_tokens": 200,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_hint}
        ],
    }).encode()

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-api-key", api_key)
    req.add_header("anthropic-version", "2023-06-01")

    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
        return data["content"][0]["text"].strip()


def _call_openai_compatible(url: str, api_key: str, model: str, system_prompt: str, user_hint: str) -> str:
    """Call an OpenAI-compatible Chat Completions API (OpenAI, Kimi, etc.)."""
    payload = json.dumps({
        "model": model,
        "max_tokens": 200,
        "temperature": 0.9,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_hint},
        ],
    }).encode()

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")

    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"].strip()
