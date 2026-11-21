import json
import re
import httpx
from typing import List

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"

QUESTION_FLOWS = {
    "foot_toe_injury": [
        "Did this start after a fall, twist, direct hit, or accident?",
        "Can you put weight on it or walk normally?",
        "Is there swelling, bruising, numbness, or tingling?",
        "Does the toe or foot look bent, deformed, or out of place?",
        "What city in El Salvador are you in?"
    ],
    "sore_throat": [
        "Does your throat feel scratchy, burning, swollen, or painful when swallowing?",
        "Do you also have fever, chills, cough, congestion, or runny nose?",
        "Are you having trouble swallowing liquids, breathing, or opening your mouth?",
        "How long has this throat discomfort been going on?",
        "What city in El Salvador are you in?"
    ],
    "nasal_congestion": [
        "Is your nose stuffy, runny, itchy, or painful around the sinuses?",
        "Do you feel pressure around your forehead, cheeks, or eyes?",
        "Do you also have fever, cough, sore throat, or ear pain?",
        "How many days has the congestion been happening?",
        "What city in El Salvador are you in?"
    ],
    "chest_pain": [
        "Is the chest pain sharp, tight, burning, or pressure-like?",
        "Does the pain spread to your arm, jaw, back, neck, or shoulder?",
        "Do you also feel shortness of breath, sweating, nausea, dizziness, or weakness?",
        "Did it start suddenly or during physical activity?",
        "What city in El Salvador are you in?"
    ],
    "stomach_pain": [
        "Where is the stomach or abdominal pain located?",
        "Is the pain cramping, burning, sharp, or constant?",
        "Do you also have nausea, vomiting, diarrhea, constipation, fever, or reflux?",
        "How long has this been happening?",
        "What city in El Salvador are you in?"
    ],
    "skin_problem": [
        "Is the skin issue a rash, itching, swelling, redness, acne, wound, or bump?",
        "Is it spreading, painful, warm, draining fluid, or getting worse?",
        "Did it start after a new medicine, food, insect bite, or product?",
        "How long has the skin problem been there?",
        "What city in El Salvador are you in?"
    ],
    "general": [
        "How long have these symptoms been happening?",
        "How severe does it feel from 1 to 10?",
        "Where in your body is the main discomfort?",
        "Are symptoms getting better, worse, or staying the same?",
        "What city in El Salvador are you in?"
    ]
}

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()

def detect_flow(symptoms: str) -> str:
    text = normalize(symptoms)

    checks = [
        ("chest_pain", ["chest pain", "pain in my chest", "heart", "dolor de pecho"]),
        ("foot_toe_injury", ["toe", "foot", "ankle", "broken toe", "broken foot", "sprain", "twisted"]),
        ("sore_throat", ["sore throat", "throat hurts", "garganta", "swallow"]),
        ("nasal_congestion", ["stuffy nose", "runny nose", "congestion", "sinus", "nariz"]),
        ("stomach_pain", ["stomach", "abdominal", "nausea", "vomiting", "diarrhea", "reflux"]),
        ("skin_problem", ["rash", "skin", "itch", "bump", "redness", "acne", "swelling"]),
    ]

    for flow, keywords in checks:
        if any(k in text for k in keywords):
            return flow

    return "general"

def generate_llm_questions(symptoms: str, language: str = "en") -> List[str]:
    prompt = f"""
You are a careful medical intake assistant. Do not diagnose.

The user said: "{symptoms}"

Generate 5 short follow-up questions that are specific to the user's symptoms.
Ask practical triage-style questions like severity, duration, body location, what makes it worse, and city in El Salvador.
Respond in this language code: {language}

Return JSON only:
{{
  "questions": ["q1", "q2", "q3", "q4", "q5"]
}}
"""

    response = httpx.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        },
        timeout=18.0
    )
    response.raise_for_status()
    data = response.json()
    parsed = json.loads(data["response"])
    questions = parsed.get("questions", [])

    if isinstance(questions, list) and questions:
        return questions[:5]

    return []

def generate_dynamic_questions(symptoms: str, language: str = "en") -> List[str]:
    flow = detect_flow(symptoms)

    if flow != "general":
        return QUESTION_FLOWS[flow]

    try:
        llm_questions = generate_llm_questions(symptoms, language)
        if llm_questions:
            return llm_questions
    except Exception as e:
        print("LLM dynamic question fallback failed:", e)

    return QUESTION_FLOWS["general"]