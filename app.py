import os
import re
import uuid
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv

# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

# ============================================================
# FLASK / THIRD-PARTY IMPORTS
# ============================================================

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from services.ai_service import (
    answer_pdf_question,
    generate_quiz,
    generate_study_plan,
    generate_tutor,
)
from services.pdf_service import markdown_to_pdf
from services.tts_service import text_to_speech


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)

# Maximum request size: 12 MB
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024

# Keep JSON response key order
app.config["JSON_SORT_KEYS"] = False

ALLOWED_EXTENSIONS = {"pdf"}

# TTS request limit
# This prevents accidentally sending extremely large AI responses
# to ElevenLabs.
TTS_MAX_CHARS = 1200


# ============================================================
# GENERAL HELPERS
# ============================================================

def allowed_file(filename: str) -> bool:
    """Check whether the uploaded file has an allowed extension."""

    if not filename:
        return False

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def slugify(value: str) -> str:
    """Convert a title into a safe filename."""

    value = re.sub(
        r"[^a-zA-Z0-9\s_-]",
        "",
        value,
    )

    value = re.sub(
        r"[\s_-]+",
        "-",
        value,
    )

    value = value.strip("-")

    return value[:80] or "studyforge-document"


def log_error(title: str, exc: Exception) -> None:
    """Print a consistent error message to the Flask console."""

    print(f"\n========== {title} ==========")
    print(f"Exception type: {type(exc).__name__}")
    print(f"Exception: {exc!r}")
    print("================================\n")


def friendly_error(exc: Exception) -> str:
    """
    Convert technical exceptions into user-friendly messages.
    """

    message = str(exc)
    upper_message = message.upper()
    lower_message = message.lower()

    # --------------------------------------------------------
    # GEMINI / GEMMA
    # --------------------------------------------------------

    if "GEMINI_API_KEY" in upper_message:
        return (
            "Gemma is not configured. "
            "Please add GEMINI_API_KEY to your .env file."
        )

    if (
        "GOOGLE API" in upper_message
        or "GOOGLE_API_KEY" in upper_message
    ):
        return (
            "Gemma API configuration error. "
            "Please check your GEMINI_API_KEY."
        )

    # --------------------------------------------------------
    # ELEVENLABS QUOTA
    # --------------------------------------------------------

    if (
        "QUOTA_EXCEEDED" in upper_message
        or "EXCEEDS YOUR QUOTA" in upper_message
    ):
        return (
            "ElevenLabs quota is too low for this audio request. "
            "Please add/reset ElevenLabs credits or use a shorter text."
        )

    # --------------------------------------------------------
    # ELEVENLABS API KEY
    # --------------------------------------------------------

    if "ELEVENLABS_API_KEY" in upper_message:
        return (
            "ElevenLabs is not configured. "
            "Please add ELEVENLABS_API_KEY to your .env file."
        )

    # --------------------------------------------------------
    # ELEVENLABS AUTHENTICATION
    # --------------------------------------------------------

    if (
        "ELEVENLABS" in upper_message
        and (
            "401" in message
            or "UNAUTHORIZED" in upper_message
            or "INVALID API KEY" in upper_message
        )
    ):
        return (
            "ElevenLabs authentication failed. "
            "Please check your ElevenLabs API key."
        )

    # --------------------------------------------------------
    # GENERAL AUTHENTICATION
    # --------------------------------------------------------

    if (
        "401" in message
        or "UNAUTHORIZED" in upper_message
    ):
        return (
            "API authentication failed. "
            "Please check your API key."
        )

    # --------------------------------------------------------
    # RATE LIMIT
    # --------------------------------------------------------

    if (
        "429" in message
        or "RATE LIMIT" in upper_message
        or "TOO MANY REQUESTS" in upper_message
    ):
        return (
            "API rate limit reached. "
            "Please wait a moment and try again."
        )

    # --------------------------------------------------------
    # TIMEOUT
    # --------------------------------------------------------

    if (
        "TIMEOUT" in upper_message
        or "TIMED OUT" in upper_message
    ):
        return (
            "The AI service took too long to respond. "
            "Please try again."
        )

    # --------------------------------------------------------
    # CONNECTION
    # --------------------------------------------------------

    if (
        "CONNECTION ERROR" in upper_message
        or "CONNECTION RESET" in upper_message
        or "CONNECTION ABORTED" in upper_message
    ):
        return (
            "Could not connect to the AI service. "
            "Please check your internet connection and try again."
        )

    # --------------------------------------------------------
    # GENERIC FALLBACK
    # --------------------------------------------------------

    return message[:500] if message else "Something went wrong."


# ============================================================
# HOME
# ============================================================

@app.get("/")
def index():
    """Render the main StudyForge AI interface."""

    return render_template("index.html")


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():
    """Return application and API configuration status."""

    return jsonify(
        {
            "status": "ok",
            "gemma_configured": bool(
                os.getenv("GEMINI_API_KEY")
            ),
            "elevenlabs_configured": bool(
                os.getenv("ELEVENLABS_API_KEY")
            ),
        }
    )


# ============================================================
# AI TUTOR
# ============================================================

@app.post("/api/tutor")
def api_tutor():
    """Generate an AI-powered lesson."""

    data = request.get_json(silent=True) or {}

    topic = (data.get("topic") or "").strip()
    level = (data.get("level") or "beginner").strip()
    language = (data.get("language") or "English").strip()
    follow_up = (data.get("follow_up") or "").strip()

    if not topic:
        return jsonify(
            {
                "error": "Please enter a topic."
            }
        ), 400

    try:
        result = generate_tutor(
            topic=topic,
            level=level,
            language=language,
            follow_up=follow_up,
        )

        return jsonify(
            {
                "content": result
            }
        )

    except Exception as exc:
        log_error("TUTOR ERROR", exc)

        return jsonify(
            {
                "error": friendly_error(exc)
            }
        ), 500


# ============================================================
# STUDY PLAN
# ============================================================

@app.post("/api/study-plan")
def api_study_plan():
    """Generate a personalized study plan."""

    data = request.get_json(silent=True) or {}

    topic = (data.get("topic") or "").strip()
    minutes = data.get("minutes", 60)
    days = data.get("days", 7)
    level = (data.get("level") or "beginner").strip()
    language = (data.get("language") or "English").strip()

    if not topic:
        return jsonify(
            {
                "error": "Please enter a topic."
            }
        ), 400

    # --------------------------------------------------------
    # Validate numeric values
    # --------------------------------------------------------

    try:
        minutes = int(minutes)
        days = int(days)
    except (TypeError, ValueError):
        return jsonify(
            {
                "error": "Time and duration must be valid numbers."
            }
        ), 400

    # Keep values inside safe limits
    minutes = max(10, min(720, minutes))
    days = max(1, min(365, days))

    try:
        result = generate_study_plan(
            topic=topic,
            minutes=minutes,
            days=days,
            level=level,
            language=language,
        )

        return jsonify(
            {
                "content": result
            }
        )

    except Exception as exc:
        log_error("STUDY PLAN ERROR", exc)

        return jsonify(
            {
                "error": friendly_error(exc)
            }
        ), 500


# ============================================================
# QUIZ
# ============================================================

@app.post("/api/quiz")
def api_quiz():
    """Generate an AI-powered multiple-choice quiz."""

    data = request.get_json(silent=True) or {}

    topic = (data.get("topic") or "").strip()
    difficulty = (data.get("difficulty") or "medium").strip()
    language = (data.get("language") or "English").strip()

    # --------------------------------------------------------
    # Validate question count
    # --------------------------------------------------------

    try:
        count = int(data.get("count", 5))
    except (TypeError, ValueError):
        return jsonify(
            {
                "error": "Question count must be a number."
            }
        ), 400

    # Keep quiz size reasonable
    count = max(1, min(20, count))

    if not topic:
        return jsonify(
            {
                "error": "Please enter a topic."
            }
        ), 400

    try:
        quiz = generate_quiz(
            topic=topic,
            difficulty=difficulty,
            count=count,
            language=language,
        )

        return jsonify(
            {
                "quiz": quiz
            }
        )

    except Exception as exc:
        log_error("QUIZ ERROR", exc)

        return jsonify(
            {
                "error": friendly_error(exc)
            }
        ), 500


# ============================================================
# PDF UPLOAD
# ============================================================

@app.post("/api/pdf/upload")
def api_pdf_upload():
    """Upload and process a PDF file."""

    file = request.files.get("file")

    # --------------------------------------------------------
    # Validate file
    # --------------------------------------------------------

    if not file or not file.filename:
        return jsonify(
            {
                "error": "Please choose a PDF file."
            }
        ), 400

    if not allowed_file(file.filename):
        return jsonify(
            {
                "error": "Only PDF files are supported."
            }
        ), 400

    safe_name = secure_filename(file.filename)

    if not safe_name:
        return jsonify(
            {
                "error": "Invalid PDF filename."
            }
        ), 400

    # --------------------------------------------------------
    # Create unique file ID
    # --------------------------------------------------------

    file_id = f"{uuid.uuid4().hex}_{safe_name}"
    path = UPLOAD_DIR / file_id

    try:
        file.save(path)

        # Import here to avoid unnecessary startup work
        from services.pdf_service import (
            extract_pdf_text,
            split_pdf_text,
        )

        text = extract_pdf_text(path)

        if not text.strip():
            path.unlink(missing_ok=True)

            return jsonify(
                {
                    "error": "No readable text was found in this PDF."
                }
            ), 400

        chunks = split_pdf_text(text)

        return jsonify(
            {
                "file_id": file_id,
                "filename": safe_name,
                "pages_text_length": len(text),
                "chunks": len(chunks),
                "message": "PDF uploaded successfully.",
            }
        )

    except Exception as exc:
        # Remove uploaded file if processing failed
        path.unlink(missing_ok=True)

        log_error("PDF UPLOAD ERROR", exc)

        return jsonify(
            {
                "error": friendly_error(exc)
            }
        ), 500


# ============================================================
# PDF CHAT
# ============================================================

@app.post("/api/pdf/chat")
def api_pdf_chat():
    """Answer questions based on an uploaded PDF."""

    data = request.get_json(silent=True) or {}

    file_id = (data.get("file_id") or "").strip()
    question = (data.get("question") or "").strip()

    if not file_id or not question:
        return jsonify(
            {
                "error": "PDF and question are required."
            }
        ), 400

    # --------------------------------------------------------
    # Security validation
    # --------------------------------------------------------

    if Path(file_id).name != file_id:
        return jsonify(
            {
                "error": "Invalid file id."
            }
        ), 400

    path = UPLOAD_DIR / file_id

    if not path.exists():
        return jsonify(
            {
                "error": (
                    "PDF session expired. "
                    "Please upload it again."
                )
            }
        ), 404

    try:
        answer = answer_pdf_question(
            path,
            question,
        )

        return jsonify(
            {
                "answer": answer
            }
        )

    except Exception as exc:
        log_error("PDF CHAT ERROR", exc)

        return jsonify(
            {
                "error": friendly_error(exc)
            }
        ), 500


# ============================================================
# EXPORT PDF
# ============================================================

@app.post("/api/export/pdf")
def api_export_pdf():
    """Convert generated content into a downloadable PDF."""

    data = request.get_json(silent=True) or {}

    title = (
        data.get("title")
        or "StudyForge AI Document"
    ).strip()

    content = (
        data.get("content")
        or ""
    ).strip()

    if not content:
        return jsonify(
            {
                "error": "There is no content to export."
            }
        ), 400

    try:
        pdf_bytes = markdown_to_pdf(
            title,
            content,
        )

        return send_file(
            BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{slugify(title)}.pdf",
        )

    except Exception as exc:
        log_error("PDF EXPORT ERROR", exc)

        return jsonify(
            {
                "error": friendly_error(exc)
            }
        ), 500


# ============================================================
# TEXT TO SPEECH
# ============================================================

@app.post("/api/tts")
def api_tts():
    """
    Convert text to speech using ElevenLabs.

    The text is limited to TTS_MAX_CHARS to prevent
    unnecessarily large ElevenLabs requests.
    """

    data = request.get_json(silent=True) or {}

    text = (data.get("text") or "").strip()

    if not text:
        return jsonify(
            {
                "error": "Text is required."
            }
        ), 400

    # --------------------------------------------------------
    # Limit ElevenLabs request size
    # --------------------------------------------------------

    if len(text) > TTS_MAX_CHARS:
        text = text[:TTS_MAX_CHARS].rstrip() + "..."

    try:
        audio = text_to_speech(text)

        if not audio:
            raise RuntimeError(
                "ElevenLabs returned empty audio data."
            )

        return send_file(
            BytesIO(audio),
            mimetype="audio/mpeg",
            as_attachment=False,
            download_name="studyforge-audio.mp3",
        )

    except Exception as exc:
        log_error("TTS ERROR", exc)

        return jsonify(
            {
                "error": friendly_error(exc)
            }
        ), 500


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(413)
def request_too_large(error):
    """Handle requests larger than MAX_CONTENT_LENGTH."""

    return jsonify(
        {
            "error": (
                "The uploaded file or request is too large. "
                "Maximum allowed size is 12 MB."
            )
        }
    ), 413


@app.errorhandler(404)
def not_found(error):
    """Handle unknown routes."""

    return jsonify(
        {
            "error": "The requested endpoint was not found."
        }
    ), 404


@app.errorhandler(500)
def internal_server_error(error):
    """Handle unexpected Flask errors."""

    return jsonify(
        {
            "error": "An unexpected server error occurred."
        }
    ), 500


# ============================================================
# APPLICATION START
# ============================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))

    print("\n" + "=" * 60)
    print("StudyForge AI")
    print("=" * 60)
    print(f"Server: http://0.0.0.0:{port}")
    print(f"Gemma configured: {bool(os.getenv('GEMINI_API_KEY'))}")
    print(
        "ElevenLabs configured: "
        f"{bool(os.getenv('ELEVENLABS_API_KEY'))}"
    )
    print(f"TTS maximum characters: {TTS_MAX_CHARS}")
    print("=" * 60 + "\n")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )
