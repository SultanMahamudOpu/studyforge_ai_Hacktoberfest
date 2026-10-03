# StudyForge AI

An AI-powered student learning assistant built for hackathons with:

- Flask + Python backend
- HTML/CSS/JavaScript frontend
- LangChain orchestration
- Google Gemma via Gemini API
- ElevenLabs Text-to-Speech
- AI Tutor
- AI Study Planner
- Smart Quiz
- PDF Reader & grounded chat
- PDF export
- Render-ready deployment

## 1. Features

### AI Tutor
Enter a topic and learner level. StudyForge generates structured learning material with explanations, examples, common mistakes, self-check questions, and a summary.

The result can be:
- read in the browser
- exported as PDF
- converted to audio with ElevenLabs
- extended with a follow-up question

### AI Study Planner
Provide:
- topic
- daily study time
- number of days
- level

The app generates a day-by-day study roadmap with objectives, study blocks, active recall, review, milestones, and final assessment.

### Smart Quiz
Provide:
- topic
- difficulty
- question count

Gemma returns structured JSON. The browser renders the quiz interactively and calculates:
- score
- correct answers
- incorrect answers
- explanations for every question

### PDF Reader & Chat
Upload a text-based PDF. The app extracts text, splits it into chunks, retrieves relevant excerpts, and asks Gemma to answer only from those excerpts.

If the answer is not supported, the API returns `NOT_FOUND_IN_PDF` and the UI displays that the information is not present in the uploaded document.

> This first version uses lightweight lexical retrieval, so it does not require a separate embedding API.

## 2. Local setup

Use Python 3.11+ or 3.13.

```bash
git clone <your-repository-url>
cd studyforge_ai

python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
```

Install:

```bash
pip install -r requirements.txt
```

Create environment file:

```bash
copy .env.example .env
```

Then put your API keys in `.env`.

Run:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## 3. API keys

The application expects:

```text
GEMINI_API_KEY=
ELEVENLABS_API_KEY=
```

The model is configurable:

```text
GEMMA_MODEL=gemma-3-27b-it
```

If a different Gemma model is available for your account, change this value without changing the rest of the application.

## 4. Render

Render can deploy this project directly.

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
gunicorn app:app
```

Add these environment variables in Render:

```text
GEMINI_API_KEY
GEMMA_MODEL
ELEVENLABS_API_KEY
ELEVENLABS_VOICE_ID
ELEVENLABS_MODEL_ID
```

Do not commit `.env`.

## 5. Project structure

```text
studyforge_ai/
├── app.py
├── requirements.txt
├── render.yaml
├── .env.example
├── .gitignore
├── README.md
├── uploads/
├── services/
│   ├── __init__.py
│   ├── ai_service.py
│   ├── pdf_service.py
│   └── tts_service.py
├── templates/
│   └── index.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── app.js
```

## 6. Hackathon presentation idea

The product story is:

> "StudyForge AI turns a student's topic, schedule, quiz needs, and study documents into one personalized learning workspace."

For the demo:
1. Show the dashboard.
2. Generate a short AI Tutor lesson.
3. Export it to PDF.
4. Play the lesson using ElevenLabs.
5. Generate a study plan.
6. Generate a quiz and submit it.
7. Upload a PDF and ask a question that exists in the document.
8. Ask a question that is not in the PDF and show the grounded `not found` behavior.

## 7. Important production notes

This is a hackathon-ready starter, not a full multi-user SaaS backend.

For a larger deployment, add:
- authentication
- persistent database
- per-user file ownership
- object storage for uploads
- rate limiting
- background jobs for long TTS/PDF generation
- stronger semantic retrieval/vector database
- automatic cleanup of uploaded PDFs
- usage/cost limits
- monitoring/logging

For Render's ephemeral filesystem, do not treat `uploads/` as permanent storage.
"# studyforge_ai_Hacktoberfest" 
