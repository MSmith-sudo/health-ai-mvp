from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from db import init_db, rank_providers
from llm_client import generate_followup_questions, extract_structured_intake
from specialty_map import infer_specialties_from_text, has_red_flags, normalize_text
from math import ceil 
from triage_questions import generate_dynamic_questions

import time

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")



@app.on_event("startup")
def startup_event():
    init_db()


def infer_care_level(text: str) -> str:
    lowered = normalize_text(text)

    if has_red_flags(lowered):
        return "Emergencia"

    urgent_keywords = [
        "high fever",
        "severe pain",
        "persistent vomiting",
        "difficulty breathing",
        "cannot keep fluids down",
        "can't keep fluids down",
        "stuffy nose with breathing trouble",
    ]

    if any(k in lowered for k in urgent_keywords):
        return "Atención urgente"

    return "Consulta ambulatoria"


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )


@app.post("/start")
def start(
    symptoms: str = Form(...),
    language: str = Form("en")
):
    normalized_symptoms = normalize_text(symptoms)
    start_time = time.time()

    try:
        questions = generate_dynamic_questions(normalized_symptoms, language)
    except Exception as e:
        print("Dynamic question generation failed:", e)
        questions = [
            "How long have these symptoms been happening?",
            "How severe are they from 1 to 10?",
            "Where in your body is the main discomfort?",
            "Are symptoms getting better, worse, or staying the same?",
            "What city in El Salvador are you in?"
        ]

    print("Start route time:", time.time() - start_time)

    return JSONResponse({
        "status": "ok",
        "symptoms": symptoms,
        "questions": questions,
        "warning": "Possible warning signs detected." if has_red_flags(normalized_symptoms) else "",
        "language": language
    })

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/admin/reload")
def reload_data():
    init_db()
    return {"status" : "reloaded"}

@app.post("/recommend")
def recommend(
    symptoms: str = Form(...),
    followup_answers: str = Form(...),
    language: str = Form("en"),
    page: int = Form(1)
):
    normalized_symptoms = normalize_text(symptoms)
    normalized_followup = normalize_text(followup_answers)
    combined_text = f"{normalized_symptoms} {normalized_followup}"

    route_start = time.time()
    emergency_detected = has_red_flags(combined_text)

    llm_start = time.time()
    try:
        intake = extract_structured_intake(normalized_symptoms, normalized_followup, language)
    except Exception as e:
        print("Structured intake extraction failed:", e)
        intake = {
            "summary": normalized_symptoms[:120],
            "city": "",
            "insurance": "",
            "language": language,
            "home_service": "",
            "symptom_keywords": []
        }
    print("LLM time:", time.time() - llm_start)

    specialty_seed_text = " ".join([
        normalized_symptoms,
        normalized_followup,
        intake.get("summary", ""),
        " ".join(intake.get("symptom_keywords", []))
    ])

    specialties = infer_specialties_from_text(specialty_seed_text)

    if emergency_detected:
        emergency_specialties = []
        lowered = combined_text.lower()

        if any(term in lowered for term in ["chest pain", "pain in my chest", "pain in chest", "heart", "dolor de pecho"]):
            emergency_specialties.append("Cardiólogos")

        if any(term in lowered for term in ["trouble breathing", "shortness of breath", "cannot breathe", "can't breathe"]):
            emergency_specialties.append("Neumólogos")

        emergency_specialties.append("Medicina General")

        merged = emergency_specialties + specialties
        seen = set()
        specialties = []
        for s in merged:
            if s not in seen:
                specialties.append(s)
                seen.add(s)

    providers = rank_providers(
        specialties=specialties,
        city=intake.get("city", ""),
        insurance=intake.get("insurance", ""),
        language=intake.get("language", ""),
        payment_method="",
        home_service=intake.get("home_service", ""),
        symptom_keywords=intake.get("symptom_keywords", []),
        limit=100
    )

    if not providers and specialties:
        providers = rank_providers(
            specialties=specialties,
            city="",
            insurance="",
            language="",
            payment_method="",
            home_service="",
            symptom_keywords=[],
            limit=100
        )

    per_page = 8
    total_results = len(providers)
    total_pages = max(1, ceil(total_results / per_page))
    current_page = max(1, min(page, total_pages))

    start_idx = (current_page - 1) * per_page
    end_idx = start_idx + per_page
    paged_providers = providers[start_idx:end_idx]

    disclaimer = (
        "This tool does not provide a diagnosis. If symptoms feel severe or urgent, seek emergency care immediately."
        if emergency_detected
        else
        "This tool does not provide a diagnosis. It only helps match symptoms to likely care options and nearby physicians."
    )

    emergency_message = ""
    if emergency_detected:
        emergency_message = (
            "Possible warning signs were detected from what you described. "
            "Please seek emergency care right away or call local emergency services. "
            "Below are nearby related providers for follow-up support, but emergency care should come first."
        )

    print("Total recommend time:", time.time() - route_start)

    return JSONResponse({
        "care_level": "Emergencia" if emergency_detected else infer_care_level(combined_text),
        "specialties": specialties,
        "summary": intake.get("summary", ""),
        "structured_intake": intake,
        "providers": paged_providers,
        "total_results": total_results,
        "page": current_page,
        "total_pages": total_pages,
        "emergency_detected": emergency_detected,
        "emergency_message": emergency_message,
        "disclaimer": disclaimer,
        "language": language
    })