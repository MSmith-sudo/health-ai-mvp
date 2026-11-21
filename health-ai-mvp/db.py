import sqlite3
from typing import List, Dict, Any

DB_PATH = "medicos.db"

SPECIALTY_MISMATCH_PENALTIES = {
    "Otorrinolaringólogos": ["Cardiólogos", "Nefrólogos", "Dermatólogos"],
    "Cardiólogos": ["Otorrinolaringólogos", "Dermatólogos", "Gastroenterólogos"],
    "Gastroenterólogos": ["Cardiólogos", "Otorrinolaringólogos"],
    "Dermatólogos": ["Cardiólogos", "Otorrinolaringólogos"],
    "Neumólogos": ["Dermatólogos", "Gastroenterólogos"],
    "Nefrólogos": ["Otorrinolaringólogos", "Dermatólogos"],
}


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS providers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT,
        specialty TEXT,
        subspecialty TEXT,
        city TEXT,
        location_text TEXT,
        home_service TEXT,
        profile_url TEXT,
        image_url TEXT,
        phone TEXT,
        whatsapp TEXT,
        languages TEXT,
        insurance TEXT,
        payment_methods TEXT,
        source_site TEXT DEFAULT 'medicosdeelsalvador.com',
        raw_text TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS provider_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider_id INTEGER NOT NULL,
        tag TEXT NOT NULL,
        FOREIGN KEY(provider_id) REFERENCES providers(id)
    )
    """)

    conn.commit()
    conn.close()


def clear_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM provider_tags")
    cur.execute("DELETE FROM providers")
    conn.commit()
    conn.close()


def insert_provider(provider: Dict[str, Any]) -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO providers (
            name, category, specialty, subspecialty, city, location_text,
            home_service, profile_url, image_url, phone, whatsapp, languages,
            insurance, payment_methods, raw_text
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        provider.get("name", ""),
        provider.get("category", ""),
        provider.get("specialty", ""),
        provider.get("subspecialty", ""),
        provider.get("city", ""),
        provider.get("location_text", ""),
        provider.get("home_service", ""),
        provider.get("profile_url", ""),
        provider.get("image_url", ""),
        provider.get("phone", ""),
        provider.get("whatsapp", ""),
        provider.get("languages", ""),
        provider.get("insurance", ""),
        provider.get("payment_methods", ""),
        provider.get("raw_text", "")
    ))

    provider_id = cur.lastrowid

    for tag in provider.get("tags", []):
        cur.execute(
            "INSERT INTO provider_tags (provider_id, tag) VALUES (?, ?)",
            (provider_id, tag)
        )

    conn.commit()
    conn.close()


def normalize_language(language: str) -> str:
    if not language:
        return ""
    lang = language.lower().strip()
    if lang == "spanish":
        return "español"
    if lang == "english":
        return "inglés"
    return lang


def normalize_specialty_name(value: str) -> str:
    return (value or "").lower().strip()


def score_specialty_match(
    requested_specialties: List[str],
    provider_specialty: str,
    provider_subspecialty: str
) -> int:
    score = 0
    provider_specialty_norm = normalize_specialty_name(provider_specialty)
    provider_subspecialty_norm = normalize_specialty_name(provider_subspecialty)

    for requested in requested_specialties:
        req = normalize_specialty_name(requested)
        if not req:
            continue

        if req == provider_specialty_norm:
            score += 20
        elif req == provider_subspecialty_norm:
            score += 14
        elif req and provider_specialty_norm and (req in provider_specialty_norm or provider_specialty_norm in req):
            score += 10
        elif req and provider_subspecialty_norm and (req in provider_subspecialty_norm or provider_subspecialty_norm in req):
            score += 7

    return score


def score_keyword_tags(symptom_keywords: List[str], provider_tags: List[str]) -> int:
    score = 0
    provider_tags_lower = [tag.lower().strip() for tag in provider_tags]

    for keyword in symptom_keywords:
        kw = keyword.lower().strip()
        if not kw:
            continue

        for tag in provider_tags_lower:
            if kw == tag:
                score += 5
            elif kw in tag or tag in kw:
                score += 2

    return score


def apply_specialty_mismatch_penalty(requested_specialties: List[str], provider_specialty: str) -> int:
    penalty = 0
    provider_specialty_clean = provider_specialty.strip()

    for requested in requested_specialties:
        blocked = SPECIALTY_MISMATCH_PENALTIES.get(requested, [])
        if provider_specialty_clean in blocked:
            penalty -= 8

    return penalty


def rank_providers(
    specialties: List[str],
    city: str = "",
    insurance: str = "",
    language: str = "",
    payment_method: str = "",
    home_service: str = "",
    symptom_keywords: List[str] | None = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    symptom_keywords = symptom_keywords or []

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM providers")
    providers = cur.fetchall()

    cur.execute("SELECT provider_id, tag FROM provider_tags")
    tag_rows = cur.fetchall()

    tags_by_provider: Dict[int, List[str]] = {}
    for row in tag_rows:
        provider_id = row["provider_id"]
        tags_by_provider.setdefault(provider_id, []).append(row["tag"])

    results = []

    requested_city = city.lower().strip() if city else ""
    requested_insurance = insurance.lower().strip() if insurance else ""
    requested_language = normalize_language(language)
    requested_payment = payment_method.lower().strip() if payment_method else ""
    requested_home_service = home_service.lower().strip() if home_service else ""

    for provider in providers:
        score = 0

        provider_specialty = provider["specialty"] or ""
        provider_subspecialty = provider["subspecialty"] or ""
        provider_city = (provider["city"] or "").lower().strip()
        provider_insurance = (provider["insurance"] or "").lower().strip()
        provider_languages = (provider["languages"] or "").lower().strip()
        provider_payments = (provider["payment_methods"] or "").lower().strip()
        provider_home_service = (provider["home_service"] or "").lower().strip()

        score += score_specialty_match(
            requested_specialties=specialties,
            provider_specialty=provider_specialty,
            provider_subspecialty=provider_subspecialty
        )

        score += apply_specialty_mismatch_penalty(
            requested_specialties=specialties,
            provider_specialty=provider_specialty
        )

        if requested_city and provider_city:
            if requested_city == provider_city:
                score += 5
            elif requested_city in provider_city or provider_city in requested_city:
                score += 4

        if requested_insurance and provider_insurance:
            if requested_insurance in provider_insurance:
                score += 2

        if requested_language and provider_languages:
            if requested_language in provider_languages:
                score += 2

        if requested_payment and provider_payments:
            if requested_payment in provider_payments:
                score += 1

        if requested_home_service and provider_home_service:
            if requested_home_service == provider_home_service:
                score += 2

        provider_tags = tags_by_provider.get(provider["id"], [])
        score += score_keyword_tags(symptom_keywords, provider_tags)

        if score > 0:
            results.append({
                "id": provider["id"],
                "name": provider["name"],
                "category": provider["category"],
                "specialty": provider["specialty"],
                "subspecialty": provider["subspecialty"],
                "city": provider["city"],
                "location_text": provider["location_text"],
                "profile_url": provider["profile_url"],
                "image_url": provider["image_url"],
                "phone": provider["phone"],
                "whatsapp": provider["whatsapp"],
                "languages": provider["languages"],
                "insurance": provider["insurance"],
                "payment_methods": provider["payment_methods"],
                "home_service": provider["home_service"],
                "score": score
            })

    conn.close()

    results = [r for r in results if r["score"] >= 6]
    results.sort(key=lambda x: x["score"], reverse=True)

    if results:
        return results[:limit]

    fallback = []
    for provider in providers:
        provider_specialty = (provider["specialty"] or "").lower()
        provider_city = (provider["city"] or "").lower()

        fallback_score = 0

        if requested_city and provider_city:
            if requested_city == provider_city or requested_city in provider_city or provider_city in requested_city:
                fallback_score += 2

        if "medicina general" in provider_specialty:
            fallback_score += 3
        elif "medicina interna" in provider_specialty:
            fallback_score += 2
        elif specialties and any(s.lower() in provider_specialty for s in specialties):
            fallback_score += 2

        if fallback_score > 0:
            fallback.append({
                "id": provider["id"],
                "name": provider["name"],
                "category": provider["category"],
                "specialty": provider["specialty"],
                "subspecialty": provider["subspecialty"],
                "city": provider["city"],
                "location_text": provider["location_text"],
                "profile_url": provider["profile_url"],
                "image_url": provider["image_url"],
                "phone": provider["phone"],
                "whatsapp": provider["whatsapp"],
                "languages": provider["languages"],
                "insurance": provider["insurance"],
                "payment_methods": provider["payment_methods"],
                "home_service": provider["home_service"],
                "score": fallback_score
            })

    fallback.sort(key=lambda x: x["score"], reverse=True)
    return fallback[:limit]