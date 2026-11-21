from db import init_db, clear_db, insert_provider

SEED_PROVIDERS = [
    {
        "name": "Centro Médico Escalón",
        "specialty": "Medicina General",
        "category": "Especialidades de Medicina",
        "city": "San Salvador",
        "home_service": "SI",
        "profile_url": "/clinica/centro-medico-escalon",
        "languages": ["Español"],
        "insurance": ["ASESUISA", "SISA", "Todas"],
        "payment_methods": ["Efectivo", "Tarjeta", "Transferencias bancarias"],
        "symptom_tags": ["fever", "fatigue", "general pain", "headache", "cough"]
    },
    {
        "name": "Clínica Gastro Santa Tecla",
        "specialty": "Gastroenterólogos",
        "category": "Especialidades de Medicina",
        "city": "Santa Tecla",
        "home_service": "NO",
        "profile_url": "/clinica/gastro-santa-tecla",
        "languages": ["Español", "Inglés"],
        "insurance": ["ASSA", "ACSA", "Todas"],
        "payment_methods": ["Efectivo", "Tarjeta"],
        "symptom_tags": ["stomach pain", "nausea", "vomiting", "diarrhea", "reflux"]
    },
    {
        "name": "Unidad ENT San Salvador",
        "specialty": "Otorrinolaringólogos",
        "category": "Medicos Cirujanos",
        "city": "San Salvador",
        "home_service": "NO",
        "profile_url": "/doctor/unidad-ent-san-salvador",
        "languages": ["Español", "Inglés"],
        "insurance": ["MAPFRE", "SISA", "Todas"],
        "payment_methods": ["Efectivo", "Tarjeta", "Cheque"],
        "symptom_tags": ["sore throat", "ear pain", "sinus pressure", "congestion", "tonsils"]
    },
    {
        "name": "Neumología Santa Ana",
        "specialty": "Neumólogos",
        "category": "Especialidades de Medicina",
        "city": "Santa Ana",
        "home_service": "NO",
        "profile_url": "/clinica/neumologia-santa-ana",
        "languages": ["Español"],
        "insurance": ["ASSA", "Palig", "Todas"],
        "payment_methods": ["Efectivo", "Tarjeta"],
        "symptom_tags": ["cough", "shortness of breath", "wheezing", "chest congestion"]
    },
    {
        "name": "Dermacenter San Miguel",
        "specialty": "Dermatólogos",
        "category": "Especialidades de Medicina",
        "city": "San Miguel",
        "home_service": "NO",
        "profile_url": "/doctor/dermacenter-san-miguel",
        "languages": ["Español"],
        "insurance": ["ASESUISA", "ACSA", "Todas"],
        "payment_methods": ["Efectivo", "Tarjeta", "BTC"],
        "symptom_tags": ["rash", "itching", "skin lesion", "redness", "eczema", "acne"]
    }
]

if __name__ == "__main__":
    init_db()
    clear_db()

    for provider in SEED_PROVIDERS:
        insert_provider(provider)

    print("Database seeded successfully.")