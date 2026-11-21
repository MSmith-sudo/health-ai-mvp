import json
import httpx
from typing import Dict, Any, List
from functools import lru_cache

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"

LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "pt": "Portuguese",
}

SYSTEM_PROMPT = """
You are a compassionate symptom intake assistant for a physician directory website in El Salvador.

Your tone should feel calm, warm, respectful, and reassuring.
You should sound like a caring healthcare intake assistant, not a robot.

You may:
- ask short follow-up questions
- summarize symptoms in a gentle, human way
- extract simple structured fields

You must not diagnose disease.
You must not claim the user has a specific condition.
You must not override emergency warning signs.
Return valid JSON only.
"""


def _call_ollama(prompt: str, timeout: float = 20.0) -> Dict[str, Any]:
    response = httpx.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        },
        timeout=timeout
    )
    response.raise_for_status()
    data = response.json()
    return json.loads(data["response"])


def normalize_ui_language(language: str) -> str:
    if not language:
        return "en"

    lowered = language.lower().strip()

    mapping = {
        "english": "en",
        "en": "en",
        "spanish": "es",
        "español": "es",
        "espanol": "es",
        "es": "es",
        "french": "fr",
        "français": "fr",
        "francais": "fr",
        "fr": "fr",
        "portuguese": "pt",
        "português": "pt",
        "portugues": "pt",
        "pt": "pt",
    }
    return mapping.get(lowered, "en")


@lru_cache(maxsize=128)
def _cached_followup_questions(symptoms: str, language_code: str) -> tuple:
    language_name = LANGUAGE_NAMES.get(language_code, "English")

    prompt = f"""
{SYSTEM_PROMPT}

Respond in {language_name}.

User symptoms: {symptoms}

Return JSON exactly like this:
{{
  "questions": [
    "Question 1",
    "Question 2",
    "Question 3",
    "Question 4",
    "Question 5"
  ]
}}

Rules:
- Ask at most 5 questions
- Keep questions short and natural
- Sound caring and human, not robotic
- Include city in El Salvador
- Prefer questions that help identify the most relevant specialty
- Only ask temperature if clearly relevant
"""
    parsed = _call_ollama(prompt, timeout=12.0)
    questions = parsed.get("questions", [])
    if isinstance(questions, list) and questions:
        return tuple(questions[:5])
    return tuple()


def generate_followup_questions(symptoms: str, language: str = "en") -> List[str]:
    language_code = normalize_ui_language(language)

    try:
        cached = _cached_followup_questions(symptoms.strip(), language_code)
        if cached:
            return list(cached)
    except Exception:
        pass

    defaults = {
        "en": [
            "How long have you been feeling this way?",
            "How severe would you say it feels from 1 to 10?",
            "Where in your body is the main discomfort or pain?",
            "What city in El Salvador are you in?",
            "Do you use medical insurance?"
        ],
        "es": [
            "¿Desde hace cuánto tiempo se siente así?",
            "¿Qué tan fuerte se siente del 1 al 10?",
            "¿En qué parte del cuerpo siente la molestia o el dolor principal?",
            "¿En qué ciudad de El Salvador se encuentra?",
            "¿Usa seguro médico?"
        ],
        "fr": [
            "Depuis combien de temps vous sentez-vous ainsi ?",
            "À quel point cela vous semble-t-il intense de 1 à 10 ?",
            "À quel endroit du corps se trouve l’inconfort ou la douleur principale ?",
            "Dans quelle ville du Salvador vous trouvez-vous ?",
            "Avez-vous une assurance médicale ?"
        ],
        "pt": [
            "Há quanto tempo você está se sentindo assim?",
            "Quão intenso isso parece de 1 a 10?",
            "Em que parte do corpo está o principal desconforto ou dor?",
            "Em que cidade de El Salvador você está?",
            "Você usa seguro médico?"
        ],
    }

    return defaults.get(language_code, defaults["en"])


@lru_cache(maxsize=256)
def _cached_structured_intake(symptoms: str, followup_answers: str, language_code: str) -> str:
    language_name = LANGUAGE_NAMES.get(language_code, "English")

    prompt = f"""
{SYSTEM_PROMPT}

Respond in {language_name}.

Symptoms: {symptoms}
Follow-up answers: {followup_answers}

Return JSON exactly in this shape:
{{
  "summary": "brief, compassionate summary",
  "city": "",
  "insurance": "",
  "language": "",
  "home_service": "",
  "symptom_keywords": ["keyword1", "keyword2", "keyword3"]
}}

Rules:
- summary should sound calm, caring, and human
- summary must be short
- city must be a city in El Salvador if mentioned
- insurance should be blank if unknown
- language should be blank if unknown
- home_service should be "SI", "NO", or ""
- symptom_keywords should be a short list of plain symptom phrases
- symptom_keywords should focus on the main complaint
"""
    parsed = _call_ollama(prompt, timeout=15.0)
    return json.dumps(parsed)


def extract_structured_intake(symptoms: str, followup_answers: str, language: str = "en") -> Dict[str, Any]:
    language_code = normalize_ui_language(language)

    try:
        parsed = json.loads(_cached_structured_intake(symptoms.strip(), followup_answers.strip(), language_code))
        return {
            "summary": parsed.get("summary", ""),
            "city": parsed.get("city", ""),
            "insurance": parsed.get("insurance", ""),
            "language": parsed.get("language", language_code),
            "home_service": parsed.get("home_service", ""),
            "symptom_keywords": parsed.get("symptom_keywords", []),
        }
    except Exception:
        return {
            "summary": symptoms[:120],
            "city": "",
            "insurance": "",
            "language": language_code,
            "home_service": "",
            "symptom_keywords": []
        }