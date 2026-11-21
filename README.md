Health AI MVP

A FastAPI prototype that helps users describe symptoms, answer follow-up questions, and find physician listings in El Salvador that may match their symptoms and location. It provides care-routing guidance and provider matches; it does not diagnose medical conditions.

Features

FastAPI web application with Jinja templates and static assets.

Symptom intake with symptom-specific follow-up questions.

Structured intake and follow-up text generated through a local Ollama model (llama3.2:3b), with fallback behavior when the model is unavailable.

Specialty inference and provider ranking using specialty, city, insurance, language, home-service, and symptom-tag information.

Red-flag detection with emergency guidance and a clear medical disclaimer.

Paginated provider results (8 per page).

SQLite provider database, plus scripts to scrape and normalize provider listings.

Requirements

Python 3.10 or later

Ollama, with the llama3.2:3b model available locally for LLM-powered intake

Internet access when collecting provider data with the scraper

Python packages are listed in requirements.txt.

Setup

Run these commands from the project root, where app.py and requirements.txt are located.

py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

Install Ollama separately, then download the model:

ollama pull llama3.2:3b

Keep the Ollama service running while using LLM-powered intake. The application calls Ollama at http://localhost:11434.

Run the application

uvicorn app:app --reload

Open http://127.0.0.1:8000 in your browser. The interactive page is served by the FastAPI app from templates/, with assets from static/.

Provider data

The application reads provider records from medicos.db. To collect and rebuild the provider data, run the scripts from the project root:

python scrape_directory.py
python normalize_data.py

The scraper collects public listings from Médicos de El Salvador, writes raw_providers.json, and the normalizer writes clean_providers.json while rebuilding the SQLite database.

refresh_data.py runs both steps and attempts to notify a running app at http://127.0.0.1:8000/admin/reload. It writes timestamped logs under logs/ and backups under backups/.

To seed the database with the sample records in ingest_seed.py, run:

python ingest_seed.py

Seeding clears existing provider rows before inserting the sample data.

API routes

Method

Route

Purpose

GET

/

Serves the web interface.

GET

/health

Returns a simple health status.

POST

/start

Accepts symptoms and returns follow-up questions and any warning flag.

POST

/recommend

Accepts symptoms and follow-up answers, then returns care level and ranked provider results.

POST

/admin/reload

Initializes the provider database schema.

The form endpoints accept symptoms; /recommend also accepts followup_answers. Both support an optional language field, and /recommend accepts an optional page field.

Safety and limitations

This is an MVP for symptom intake and provider discovery, not a medical device or diagnostic service. Its keyword-based warning detection can miss urgent conditions or flag non-urgent symptoms. Users with severe or urgent symptoms should seek emergency care. Provider information may be incomplete or change; confirm details directly with the provider.

The application sends symptom text to the local Ollama service configured in the code. Review the model and data-handling setup before exposing the app to other users or deploying it publicly.
