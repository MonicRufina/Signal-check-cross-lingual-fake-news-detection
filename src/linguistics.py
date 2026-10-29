"""
Linguistic Stylometry and Deception Cues Analyzer for NLP.
Extracts computational linguistics and pragmatic features from text:
1. Objectivity vs. Subjectivity Score (Attributive reporting vs. opinion markers)
2. Sensationalism & Syntactic Urgency (Hyperbolic triggers, clickbait syntax, exclamation ratio)
3. Emotional Extremity (Affective valence polarization vs. measured journalistic tone)
4. Lexical Richness & Readability (Type-Token Ratio - TTR, average sentence length)
"""

import re
import math

# Multilingual Sensationalism & Urgency Lexicon
SENSATIONAL_STEMS = {
    "en": [
        "shocking", "unbelievable", "secret", "exposed", "breaking", "miracle", "urgent",
        "danger", "scam", "conspiracy", "warning", "must see", "share before", "viral",
        "deleted", "hidden truth", "disaster", "nightmare", "mind blowing", "bombshell",
        "catastrophe", "banned", "censored", "they don't want you to know", "proof"
    ],
    "hi": [
        "सनसनीखेज", "चमत्कार", "सावधान", "खुलासा", "गुप्त", "वायरल", "जरूर देखें",
        "शेयर करें", "खतरा", "साजिश", "हैरान", "सच्चाई", "तहलका", "धमाका", "कयामत"
    ],
    "ta": [
        "அதிர்ச்சி", "ரகசியம்", "எச்சரிக்கை", "உண்மை வெளிவந்தது", "வைரல்",
        "பகிருங்கள்", "ஆபத்து", "சதி", "அதிசயம்", "பரபரப்பு"
    ],
    "es": [
        "impactante", "secreto", "urgente", "milagro", "alerta", "viral",
        "conspiración", "peligro", "oculto", "prohibido", "catástrofe"
    ],
    "fr": [
        "incroyable", "secret", "choc", "urgent", "complot", "viral",
        "attention", "danger", "catastrophe", "censure", "bombe"
    ],
    "de": [
        "schockierend", "geheim", "unglaublich", "warnung", "skandal",
        "verschwörung", "viral", "katastrophe", "enthüllung", "zensiert"
    ]
}

# Multilingual Factual / Attributive Journalism Markers
FACTUAL_ATTRIBUTION_STEMS = {
    "en": [
        "said", "stated", "announced", "confirmed", "reported", "according to",
        "published", "released", "found", "study", "data", "official", "spokesperson",
        "minister", "bureau", "agency", "investigation", "court", "parliament", "source"
    ],
    "hi": [
        "कहा", "बताया", "घोषणा", "पुष्टि", "रिपोर्ट", "अनुसार", "जारी",
        "अधिकारी", "प्रवक्ता", "मंत्रालय", "जांच", "अदालत", "वैज्ञानिक"
    ],
    "ta": [
        "தெரிவித்தார்", "கூறினார்", "வெளியிட்டது", "அறிக்கை", "உறுதிப்படுத்தியது",
        "அதிகாரிகள்", "நீதிமன்றம்", "காவல்துறை"
    ],
    "es": [
        "dijo", "declaró", "anunció", "confirmó", "informó", "según",
        "publicó", "oficial", "estudio", "fuente", "portavoz"
    ],
    "fr": [
        "déclaré", "annoncé", "confirmé", "selon", "publié", "officiel",
        "source", "rapport", "porte-parole", "ministère"
    ],
    "de": [
        "erklärte", "bestätigte", "berichtet", "laut", "veröffentlicht",
        "offiziell", "quelle", "sprecher", "studie", "untersuchung"
    ]
}

# Subjective & Emotional Intensifiers
SUBJECTIVE_STEMS = {
    "en": [
        "obviously", "clearly", "terrible", "evil", "corrupt", "wonderful", "pathetic",
        "definitely", "surely", "monstrous", "disgusting", "heroic", "mastermind",
        "horrific", "ridiculous", "shameful", "unacceptable", "pure evil"
    ],
    "hi": [
        "भ्रष्ट", "घटिया", "अद्भुत", "शर्मनाक", "घिनौना", "महान", "बकवास", "बेकार"
    ],
    "ta": [
        "மோசமான", "அற்புதம்", "வெட்கக்கேடான", "துரோகம்", "அயோக்கியர்"
    ],
    "es": [
        "obviamente", "terrible", "corrupto", "maravilloso", "patético", "vergonzoso"
    ],
    "fr": [
        "terrible", "corrompu", "honteux", "pathétique", "évident", "monstrueux"
    ],
    "de": [
        "schrecklich", "korrupt", "peinlich", "offensichtlich", "monströs", "ekelhaft"
    ]
}


def analyze_linguistic_features(text: str, lang: str = "en") -> dict:
    """
    Computes key NLP stylometric metrics on input claim/article:
    - Objectivity vs Subjectivity
    - Sensationalism & Clickbait Index
    - Emotional Extremity / Affective Charge
    - Lexical Richness (Type-Token Ratio) & Readability Level
    """
    if not text or not text.strip():
        return _default_metrics()

    clean_text = text.strip()
    words = re.findall(r'\b\w+\b', clean_text, re.UNICODE)
    total_words = len(words)
    if total_words == 0:
        return _default_metrics()

    lower_text = clean_text.lower()
    lower_words = [w.lower() for w in words]
    unique_words = set(lower_words)

    # 1. Lexical Richness (Type-Token Ratio - TTR)
    ttr = len(unique_words) / total_words
    ttr_score = round(min(1.0, max(0.0, ttr)) * 100, 1)

    if ttr >= 0.75:
        lexical_label = "Rich Editorial Vocabulary"
    elif ttr >= 0.50:
        lexical_label = "Balanced Journalistic Diction"
    else:
        lexical_label = "Repetitive / Low Lexical Diversity"

    # 2. Sentences & Readability
    sentences = re.split(r'[.!?।\n]+', clean_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 0]
    total_sentences = max(len(sentences), 1)
    avg_sentence_length = round(total_words / total_sentences, 1)

    if avg_sentence_length > 25:
        reading_level = "Complex / Formal Investigative Report"
    elif avg_sentence_length >= 12:
        reading_level = "Standard News Editorial"
    else:
        reading_level = "Brief / Conversational Headline"

    # 3. Sensationalism & Clickbait Syntax
    sensational_words_list = SENSATIONAL_STEMS.get(lang, SENSATIONAL_STEMS["en"])
    # Combine with English stems as secondary check
    if lang != "en":
        sensational_words_list = list(set(sensational_words_list + SENSATIONAL_STEMS["en"]))

    sensational_hits = sum(1 for stem in sensational_words_list if stem in lower_text)

    # Excessive punctuation checks (??, !!, !?)
    excl_count = len(re.findall(r'!+', clean_text))
    question_count = len(re.findall(r'\?+', clean_text))
    mult_punct_count = len(re.findall(r'[!?]{2,}', clean_text))

    # All-caps words (excluding common single-letter acronyms)
    all_caps_words = [w for w in words if len(w) > 2 and w.isupper() and w.isalpha()]
    caps_ratio = len(all_caps_words) / total_words

    # Compute Sensationalism Index [0 - 100]
    sensational_raw = (
        (sensational_hits * 18.0) +
        (excl_count * 10.0) +
        (mult_punct_count * 20.0) +
        (caps_ratio * 40.0)
    )
    # Normalize with text length dampener
    sensational_score = int(min(98, max(4, round(sensational_raw))))

    if sensational_score >= 50:
        sensational_label = "High Clickbait & Urgency Framing"
        sensational_status = "warning"
    elif sensational_score >= 25:
        sensational_label = "Moderate Affective Hook"
        sensational_status = "caution"
    else:
        sensational_label = "Low (Standard Journalistic Syntax)"
        sensational_status = "safe"

    # 4. Objectivity vs. Subjectivity
    attribution_list = FACTUAL_ATTRIBUTION_STEMS.get(lang, FACTUAL_ATTRIBUTION_STEMS["en"])
    if lang != "en":
        attribution_list = list(set(attribution_list + FACTUAL_ATTRIBUTION_STEMS["en"]))

    subjective_list = SUBJECTIVE_STEMS.get(lang, SUBJECTIVE_STEMS["en"])
    if lang != "en":
        subjective_list = list(set(subjective_list + SUBJECTIVE_STEMS["en"]))

    attrib_hits = sum(1 for stem in attribution_list if stem in lower_text)
    subjective_hits = sum(1 for stem in subjective_list if stem in lower_text)

    # Numbers and quantitative statistics indicate factual reporting
    number_hits = len(re.findall(r'\b\d+([.,]\d+)?\b', clean_text))

    objective_points = (attrib_hits * 16.0) + (number_hits * 8.0) + 30.0
    subjective_points = (subjective_hits * 22.0) + (sensational_hits * 14.0)

    total_points = objective_points + subjective_points
    if total_points > 0:
        obj_ratio = objective_points / total_points
    else:
        obj_ratio = 0.70

    objectivity_score = int(min(96, max(12, round(obj_ratio * 100))))
    subjectivity_score = 100 - objectivity_score

    if objectivity_score >= 65:
        objectivity_label = f"{objectivity_score}% Objective (Factual Attribution)"
        objectivity_status = "safe"
    elif objectivity_score >= 40:
        objectivity_label = f"{objectivity_score}% Balanced (Mixed Tone)"
        objectivity_status = "caution"
    else:
        objectivity_label = f"{subjectivity_score}% Subjective (High Opinion Density)"
        objectivity_status = "warning"

    # 5. Emotional Extremity / Affective Polarization
    # Calculated from subjective density + exclamation intensity
    emotional_raw = (subjective_hits * 20.0) + (sensational_hits * 15.0) + (excl_count * 12.0)
    emotional_score = int(min(95, max(8, round(emotional_raw))))

    if emotional_score >= 55:
        emotional_label = "High Polarization (Outrage / Fear Trigger)"
        emotional_status = "warning"
    elif emotional_score >= 28:
        emotional_label = "Moderate Affective Charge"
        emotional_status = "caution"
    else:
        emotional_label = "Neutral & Measured Journalistic Tone"
        emotional_status = "safe"

    # Key Diagnostic Linguistic Markers (Evidence bullets)
    key_markers = []
    if attrib_hits > 0:
        key_markers.append(f"Attribution verbs detected ({attrib_hits} sourcing markers)")
    if number_hits > 0:
        key_markers.append(f"Empirical statistics / numbers cited ({number_hits} data points)")
    if sensational_hits > 0:
        key_markers.append(f"Sensationalism lexical cues triggered ({sensational_hits} alarm stems)")
    if mult_punct_count > 0 or excl_count > 1:
        key_markers.append("Non-standard emphatic punctuation (!/?) detected")
    if len(all_caps_words) > 1:
        key_markers.append(f"All-caps shouting emphasis tokens ({len(all_caps_words)} words)")
    if len(key_markers) == 0:
        key_markers.append("Standard neutral sentence structure with uniform syntax")

    return {
        "objectivity": {
            "score": objectivity_score,
            "label": objectivity_label,
            "status": objectivity_status
        },
        "sensationalism": {
            "score": sensational_score,
            "label": sensational_label,
            "status": sensational_status
        },
        "emotional_extremity": {
            "score": emotional_score,
            "label": emotional_label,
            "status": emotional_status
        },
        "lexical_richness": {
            "ttr": round(ttr, 3),
            "score": ttr_score,
            "label": lexical_label,
            "reading_level": reading_level,
            "word_count": total_words,
            "sentence_count": total_sentences,
            "avg_sentence_len": avg_sentence_length
        },
        "key_markers": key_markers[:3]
    }


def _default_metrics() -> dict:
    return {
        "objectivity": {
            "score": 75,
            "label": "75% Objective (Standard Baseline)",
            "status": "safe"
        },
        "sensationalism": {
            "score": 10,
            "label": "Low (Standard Journalistic Syntax)",
            "status": "safe"
        },
        "emotional_extremity": {
            "score": 15,
            "label": "Neutral & Measured Journalistic Tone",
            "status": "safe"
        },
        "lexical_richness": {
            "ttr": 0.80,
            "score": 80.0,
            "label": "Balanced Journalistic Diction",
            "reading_level": "Standard News Editorial",
            "word_count": 0,
            "sentence_count": 0,
            "avg_sentence_len": 0
        },
        "key_markers": ["Awaiting text input"]
    }
