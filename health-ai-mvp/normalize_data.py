import json
import re
from collections import Counter
from db import init_db, clear_db, insert_provider

KNOWN_CITIES = [
    "Aguilares",
    "Ahuachapán",
    "Antiguo Cuscatlán",
    "Apopa",
    "Chalatenango",
    "Cojutepeque",
    "Ilobasco",
    "La Libertad",
    "La Unión",
    "Mejicanos",
    "Metapán",
    "San Miguel",
    "San Salvador",
    "San Vicente",
    "Santa Ana",
    "Santa Rosa de Lima",
    "Santa Tecla",
    "Sonsonate",
    "Soyapango",
    "Usulután",
    "Zacatecoluca",
]

INSURANCE_NAMES = [
    "MAPFRE", "Seguros del Pacifico", "ACSA", "Aseguradora Popular", "ASESUISA",
    "ASSA", "Quálitas", "Seguros Futuro", "SISA", "Seguros Atlántida Vida",
    "La Central", "Seguros Azul", "SIAP", "Vital", "MiRED", "RPN",
    "Pan American Life", "AIG", "Global Assist", "ETESAL", "CEL",
    "ABANK", "La Geo", "GEA Internacional",
]

PAYMENT_METHODS = [
    "Efectivo", "Tarjeta", "BTC", "Cheque", "Transferencias bancarias",
    "Money Gram", "Western Unión", "Tasa 0",
]

SPECIALTY_SIGNAL_RULES = {
    "Cardiólogos": [
        r"cardi[oó]log", r"cardiolog[íi]a", r"ecocardiograma", r"electrocardiograma",
        r"holter", r"\bmapa\b", r"hipertensi[oó]n", r"dolor de pecho",
        r"palpitaciones", r"cateterismo", r"insuficiencia cardiaca"
    ],
    "Otorrinolaringólogos": [
        r"otorrino", r"otorrinolaring[oó]log", r"garganta", r"am[ií]gdal",
        r"o[ií]do", r"nariz", r"sinus", r"congesti[oó]n nasal",
        r"ronquera", r"sore throat", r"stuffy nose"
    ],
    "Gastroenterólogos": [
        r"gastroenter[oó]log", r"reflujo", r"gastr", r"colon", r"intestin",
        r"h[ií]gado", r"abdominal", r"endoscop", r"diarrea",
        r"estreñimiento", r"n[aá]use", r"v[oó]mit"
    ],
    "Dermatólogos": [
        r"dermat[oó]log", r"piel", r"acn[eé]", r"eczema", r"rash",
        r"picaz[oó]n", r"lesiones cut[aá]neas", r"psoriasis", r"vitiligo"
    ],
    "Neumólogos": [
        r"neum[oó]log", r"pulm[oó]n", r"respira", r"tos", r"asma",
        r"bron", r"shortness of breath", r"wheezing", r"falta de aire"
    ],
    "Nefrólogos": [
        r"nefr[oó]log", r"renal", r"hemodi[aá]lisis", r"riñ[oó]n",
        r"riñones", r"trasplante renal"
    ],
    "Pediatras": [
        r"pediatr", r"neonat", r"reci[eé]n nacido", r"prematuro",
        r"niñ[oa]s?", r"adolescentes"
    ],
    "Neurocirujanos": [
        r"neurociruj", r"cerebro", r"m[eé]dula", r"columna",
        r"craneo", r"nervios", r"cirug[ií]a de columna"
    ],
    "Psiquiatría": [
        r"psiquiatr", r"ansiedad", r"depresi[oó]n", r"salud mental",
        r"insomnio", r"p[aá]nico"
    ],
    "Ginecolólogo Obstetras": [
        r"ginec[oó]log", r"obstetra", r"embarazo", r"prenatal",
        r"sangrado vaginal", r"mast[oó]log", r"perinat[oó]log"
    ],
    "Urólogos": [
        r"urol[oó]g", r"urin", r"pr[oó]stata", r"vejiga"
    ],
    "Cirujanos": [
        r"cirujano general", r"laparoscop", r"hernia", r"apendicitis",
        r"ves[ií]cula", r"cirug[ií]a digestiva"
    ],
    "Medicina Interna": [
        r"internista", r"medicina interna", r"enfermedades cr[oó]nicas",
        r"adultos", r"diabetes"
    ],
    "Medicina General": [
        r"medicina general", r"medico general", r"consulta general",
        r"fiebre", r"dolor general", r"infecci[oó]n leve"
    ],
}

SUBSPECIALTY_RULES = {
    "Cardiología Intervencionista": [r"intervencionista", r"cateterismo"],
    "Neonatología": [r"neonat"],
    "Columna": [r"columna"],
    "Cuidados Intensivos": [r"cuidados intensivos"],
    "Hemodiálisis": [r"hemodi[aá]lisis"],
    "Laparoscopía": [r"laparoscop"],
    "Rehabilitación": [r"rehabilitaci[oó]n", r"fisioterapia"],
}

def is_valid_doctor(raw: dict) -> bool:
    name = raw.get("name", "").strip().lower()
    url = raw.get("profile_url", "").lower()
    text = raw.get("raw_text", "").lower()

    if name.startswith("dr.") or name.startswith("dra."):
        return True
    if "/doctor/" in url or "/medico/" in url:
        return True

    blocked_words = [
        "asociación", "clinica", "clínica", "cardiolab", "centro",
        "hospital", "laboratorio", "óptica", "farmacia"
    ]
    if any(word in name for word in blocked_words):
        return False

    if " dr. " in f" {text} " or " dra. " in f" {text} ":
        return True

    return False


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def extract_phones(text: str) -> str:
    matches = re.findall(r"\+503\s?\d{4}-\d{4}", text)
    return ", ".join(dedupe_keep_order(matches))


from collections import Counter
import re

def extract_city(text: str, profile_url: str = "") -> str:
    lowered = text.lower()
    url_lower = profile_url.lower()

    # 1) URL-based city hints first
    for city in KNOWN_CITIES:
        city_slug = (
            city.lower()
            .replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
            .replace("ñ", "n")
            .replace(" ", "-")
        )
        if city_slug in url_lower:
            return city

    # 2) Score cities by nearby address/location context
    city_scores = Counter()

    address_context_patterns = [
        r"(dirección|direccion|ubicación|ubicacion|sucursal|cl[ií]nica|hospital|colonia|avenida|av\.?|calle|blvd\.?|boulevard|localizado en|ubicado en|zona)[^.\n]{0,120}",
        r"(sanatorio|consultorio|torre m[eé]dica|torre medica|centro m[eé]dico|centro medico)[^.\n]{0,120}",
    ]

    # Find context windows that are likely about address/location
    context_windows = []
    for pattern in address_context_patterns:
        for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
            start = max(0, match.start() - 40)
            end = min(len(lowered), match.end() + 120)
            context_windows.append(lowered[start:end])

    # If no context windows found, use whole text as weak fallback
    if not context_windows:
        context_windows = [lowered]

    for city in KNOWN_CITIES:
        city_lower = city.lower()
        for window in context_windows:
            hits = len(re.findall(rf"\b{re.escape(city_lower)}\b", window, flags=re.IGNORECASE))
            if hits:
                city_scores[city] += hits * 3

        # weaker whole-page count
        whole_hits = len(re.findall(rf"\b{re.escape(city_lower)}\b", lowered, flags=re.IGNORECASE))
        if whole_hits:
            city_scores[city] += whole_hits

    if city_scores:
        return city_scores.most_common(1)[0][0]

    return ""


def count_pattern_hits(text: str, patterns: list[str]) -> int:
    total = 0
    for pattern in patterns:
        total += len(re.findall(pattern, text, flags=re.IGNORECASE))
    return total


def extract_specialty_and_subspecialty(text: str, profile_url: str = "") -> tuple[str, str]:
    lowered = text.lower()
    url_lower = profile_url.lower()
    scores = Counter()

    url_boosts = {
        "cardiologos": "Cardiólogos",
        "otorrinolaringologos": "Otorrinolaringólogos",
        "gastroenterologos": "Gastroenterólogos",
        "dermatologos": "Dermatólogos",
        "neumologos": "Neumólogos",
        "nefrologos": "Nefrólogos",
        "pediatras": "Pediatras",
        "neurocirujanos": "Neurocirujanos",
        "psiquiatria": "Psiquiatría",
        "ginecologos": "Ginecolólogo Obstetras",
        "urologos": "Urólogos",
        "medicina-interna": "Medicina Interna",
        "medicina-general": "Medicina General",
    }

    for slug, specialty in url_boosts.items():
        if slug in url_lower:
            scores[specialty] += 8

    for specialty, patterns in SPECIALTY_SIGNAL_RULES.items():
        hits = count_pattern_hits(lowered, patterns)
        if hits > 0:
            scores[specialty] += hits

    main_specialty = scores.most_common(1)[0][0] if scores else "Medicina General"

    subspecialty_scores = Counter()
    for subspecialty, patterns in SUBSPECIALTY_RULES.items():
        hits = count_pattern_hits(lowered, patterns)
        if hits > 0:
            subspecialty_scores[subspecialty] += hits

    best_subspecialty = subspecialty_scores.most_common(1)[0][0] if subspecialty_scores else ""
    return main_specialty, best_subspecialty


def extract_languages(text: str) -> str:
    lowered = text.lower()
    langs = []

    if "español" in lowered:
        langs.append("Español")
    if "inglés" in lowered or "ingles" in lowered:
        langs.append("Inglés")
    if "francés" in lowered or "frances" in lowered:
        langs.append("Francés")
    if "portugués" in lowered or "portugues" in lowered:
        langs.append("Portugués")

    if not langs:
        langs.append("Español")

    return ", ".join(dedupe_keep_order(langs))


def extract_insurance(text: str) -> str:
    lowered = text.lower()
    found = []

    for insurer in INSURANCE_NAMES:
        if insurer.lower() in lowered:
            found.append(insurer)

    if found:
        return ", ".join(dedupe_keep_order(found))
    if "aseguradoras aceptadas" in lowered or "seguro médico" in lowered:
        return "Consultar perfil"
    return ""


def extract_payment_methods(text: str) -> str:
    lowered = text.lower()
    found = []

    for method in PAYMENT_METHODS:
        if method.lower() in lowered:
            found.append(method)

    return ", ".join(dedupe_keep_order(found))


def extract_image_url(raw: dict) -> str:
    return (raw.get("image_url", "") or raw.get("photo_url", "") or "").strip()


def infer_tags(text: str) -> list[str]:
    lowered = text.lower()
    tags = []

    mapping = {
        "heart": [
            "cardio", "corazón", "corazon", "dolor de pecho", "presión", "presion",
            "holter", "ecocardiograma", "palpitaciones", "hipertensión", "hipertension"
        ],
        "throat": [
            "garganta", "sore throat", "amigdal", "tonsils", "sinus", "congestion",
            "otorrino", "oído", "oido", "ronquera", "ear pain", "stuffy nose", "nariz"
        ],
        "kidney": [
            "renal", "hemodiálisis", "hemodialisis", "riñón", "riñones", "nefro"
        ],
        "rehab": [
            "fisioterapia", "rehabilitación", "rehabilitacion"
        ],
        "surgery": [
            "cirugía", "cirugia", "laparoscop", "apendicitis", "hernia", "vesícula", "vesicula"
        ],
        "children": [
            "pediatr", "neonat", "recién nacido", "recien nacido", "prematuro", "niño", "niña"
        ],
        "breathing": [
            "respira", "pulm", "neum", "tos", "shortness of breath", "wheezing"
        ],
        "stomach pain": [
            "gastro", "abdominal", "náuse", "nause", "vomit", "diarrea", "reflujo", "estreñimiento"
        ],
        "pain": [
            "dolor", "pain", "ardor", "molestia"
        ],
        "mental health": [
            "ansiedad", "depres", "insomnio", "panic", "mental health"
        ],
        "pregnancy": [
            "embarazo", "prenatal", "ginecol", "obstetra", "sangrado vaginal"
        ]
    }

    for tag, keywords in mapping.items():
        if any(keyword in lowered for keyword in keywords):
            tags.append(tag)

    return dedupe_keep_order(tags)


def normalize_provider(raw: dict) -> dict:
    text = (raw.get("raw_text", "") or "").strip()
    profile_url = raw.get("profile_url", "").strip()

    city = extract_city(text, profile_url)
    specialty, subspecialty = extract_specialty_and_subspecialty(text, profile_url)

    return {
        "name": raw.get("name", "").strip(),
        "category": "Doctor",
        "specialty": specialty,
        "subspecialty": subspecialty,
        "city": city,
        "location_text": city,
        "home_service": "SI" if "domicilio" in text.lower() or "domiciliar" in text.lower() else "NO",
        "profile_url": profile_url,
        "image_url": extract_image_url(raw),
        "phone": extract_phones(text),
        "whatsapp": "SI" if "whatsapp" in text.lower() else "",
        "languages": extract_languages(text),
        "insurance": extract_insurance(text),
        "payment_methods": extract_payment_methods(text),
        "raw_text": text[:1200],
        "tags": infer_tags(text),
    }


def main():
    with open("raw_providers.json", "r", encoding="utf-8") as f:
        raw = json.load(f)

    clean = [
        normalize_provider(item)
        for item in raw
        if item.get("name") and is_valid_doctor(item)
    ]

    init_db()
    clear_db()

    for provider in clean:
        print(provider)
        insert_provider(provider)

    with open("clean_providers.json", "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)

    print(f"Normalized and inserted {len(clean)} providers.")


if __name__ == "__main__":
    main()