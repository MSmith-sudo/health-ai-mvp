from typing import List
import re

SPECIALTY_PRIORITY_RULES = [
    (
        "Otorrinolaringólogos",
        [
            "throat", "sore throat", "pain in throat", "tonsils", "ear pain", "sinus", "congestion",
            "stuffy nose", "blocked nose", "runny nose", "nose is stuffy", "nasal pressure",
            "garganta", "amígdal", "amigdal", "oído", "oido", "nariz", "otorrino",
            "hoarse", "voice", "swallowing", "post nasal drip"
        ]
    ),
    (
        "Cardiólogos",
        [
            "heart", "heart pain", "chest pain", "pain in chest", "pain in my chest",
            "pressure in chest", "tightness in chest", "palpitations", "blood pressure",
            "corazón", "corazon", "cardio", "dolor de pecho", "presión", "presion",
            "opresión en el pecho", "palpitaciones"
        ]
    ),
    (
        "Gastroenterólogos",
        [
            "stomach", "stomach pain", "abdominal", "vomiting", "nausea", "diarrhea", "reflux", "constipation",
            "gastro", "abdomen", "náusea", "nausea", "vómito", "vomit", "diarrea", "reflujo"
        ]
    ),
    (
        "Dermatólogos",
        [
            "rash", "itching", "skin", "redness", "acne", "eczema", "hives",
            "piel", "picazón", "picazon"
        ]
    ),
    (
        "Neumólogos",
        [
            "cough", "wheezing", "shortness of breath", "breathing", "chest congestion",
            "can't breathe", "cannot breathe", "trouble breathing",
            "tos", "respirar", "pulmón", "pulmon", "falta de aire"
        ]
    ),
    (
        "Nefrólogos",
        [
            "kidney", "renal", "hemodialysis", "hemodiálisis", "riñón", "riñones", "nefro"
        ]
    ),
    (
        "Pediatras",
        [
            "child", "baby", "kid", "newborn", "pediatric",
            "niño", "niña", "bebe", "bebé", "recién nacido", "recien nacido", "pediatra"
        ]
    ),
    (
        "Neurocirujanos",
        [
            "brain", "spine", "neuro", "seizure", "médula", "medula", "cerebro", "columna"
        ]
    ),
    (
        "Psiquiatría",
        [
            "anxiety", "depression", "panic", "mental health", "insomnia",
            "ansiedad", "depresión", "depresion", "pánico", "panico"
        ]
    ),
    (
        "Ginecolólogo Obstetras",
        [
            "pregnancy", "pelvic pain", "menstrual", "prenatal", "vaginal bleeding",
            "embarazo", "pélvico", "pelvico", "menstrual", "sangrado vaginal"
        ]
    ),
    (
        "Medicina Interna",
        [
            "internista", "chronic illness", "adult chronic", "complex symptoms",
            "blood sugar", "diabetes", "adult medicine"
        ]
    ),
    (
        "Medicina General",
        [
            "fever", "fatigue", "body aches", "general pain", "headache",
            "fiebre", "dolor general", "cansancio", "dolor de cabeza", "mild infection"
        ]
    ),
]

RED_FLAG_PATTERNS = [
    r"\bchest pain\b",
    r"\bpain in (my )?chest\b",
    r"\bpressure in (my )?chest\b",
    r"\btightness in (my )?chest\b",
    r"\bdolor de pecho\b",
    r"\bopresi[oó]n en el pecho\b",
    r"\bsevere bleeding\b",
    r"\bstroke\b",
    r"\bone-sided weakness\b",
    r"\btrouble breathing\b",
    r"\bshortness of breath\b",
    r"\bcannot breathe\b",
    r"\bcan'?t breathe\b",
    r"\bunconscious\b",
    r"\bseizure\b",
    r"\bsuicidal\b",
]


def normalize_text(text: str) -> str:
    lowered = text.lower().strip()

    replacements = {
        "pain in my chest": "chest pain",
        "pain in chest": "chest pain",
        "pressure in my chest": "chest pain",
        "tightness in my chest": "chest pain",
        "my nose is stuffy": "stuffy nose",
        "nose is stuffy": "stuffy nose",
        "blocked nose": "stuffy nose",
        "my throat hurts": "sore throat",
        "pain in my throat": "sore throat",
        "my ear hurts": "ear pain",
        "my stomach hurts": "stomach pain",
        "my stomach is acting up": "stomach pain",
    }

    for old, new in replacements.items():
        lowered = lowered.replace(old, new)

    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


def infer_specialties_from_text(text: str) -> List[str]:
    lowered = normalize_text(text)
    scored = []

    for specialty, keywords in SPECIALTY_PRIORITY_RULES:
        matches = sum(1 for keyword in keywords if keyword in lowered)
        if matches > 0:
            scored.append((specialty, matches))

    if not scored:
        return ["Medicina General"]

    scored.sort(key=lambda item: item[1], reverse=True)

    seen = set()
    ordered = []
    for specialty, _ in scored[:2]:
        if specialty not in seen:
            ordered.append(specialty)
            seen.add(specialty)

    return ordered


def has_red_flags(text: str) -> bool:
    lowered = normalize_text(text)
    return any(re.search(pattern, lowered) for pattern in RED_FLAG_PATTERNS)