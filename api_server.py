
# """
# api_server.py  (SECURITY-HARDENED)
# ------------------------------------
# Security additions vs original:
#   1. API-key authentication on all /api/* endpoints
#   2. Rate limiting (Flask-Limiter)  — prevents abuse
#   3. Security event logging via audit_logger
#   4. Injection-detected results surfaced as warnings (not silently dropped)
#   5. Low-confidence flag passed through to HR UI
#   6. .env-only secrets; no hardcoded credentials anywhere
# """

# from flask import Flask, request, jsonify, send_from_directory, Response, send_file, g
# from flask_cors import CORS
# from flask_limiter import Limiter
# from flask_limiter.util import get_remote_address
# from werkzeug.utils import secure_filename
# import os
# import json
# import sys
# import tempfile
# from datetime import datetime
# from functools import wraps
# from dotenv import load_dotenv

# load_dotenv()

# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# from core.parser import extract_resume_text
# from core.scorer import score_resume
# from core.ranker import get_recommendation
# from core.report_generator import generate_json_report, generate_html_report, generate_pdf_report
# from core.audit_logger import log_override, log_analysis_event, log_security_event

# app = Flask(__name__, static_folder="frontend", template_folder="frontend")

# CORS(app)

# # ---------------------------------------------------------------------------
# # Rate Limiting
# # ---------------------------------------------------------------------------
# limiter = Limiter(
#     key_func=get_remote_address,
#     app=app,
#     default_limits=["200 per day", "60 per hour"],
#     storage_uri="memory://",
# )

# # ---------------------------------------------------------------------------
# # Configuration
# # ---------------------------------------------------------------------------
# UPLOAD_FOLDER      = 'temp_uploads'
# ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}
# app.config['UPLOAD_FOLDER']      = UPLOAD_FOLDER
# app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB

# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# os.makedirs('outputs',     exist_ok=True)

# overrides_store = {}

# # ---------------------------------------------------------------------------
# # API Key Authentication
# # ---------------------------------------------------------------------------
# _HR_API_KEY = os.getenv("HR_API_KEY")

# def require_api_key(f):
#     @wraps(f)
#     def decorated(*args, **kwargs):
#         if not _HR_API_KEY:
#             print("[SECURITY WARNING] HR_API_KEY is not set — endpoint is unprotected!")
#             return f(*args, **kwargs)
#         provided = request.headers.get("X-API-Key", "").strip()
#         if not provided or provided != _HR_API_KEY:
#             log_security_event(
#                 "auth_failure",
#                 f"Invalid or missing API key from {get_remote_address()}",
#                 endpoint=request.path,
#             )
#             return jsonify({"error": "Unauthorised — valid X-API-Key header required"}), 401
#         return f(*args, **kwargs)
#     return decorated


# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# # ---------------------------------------------------------------------------
# # Routes
# # ---------------------------------------------------------------------------

# @app.route('/')
# def serve_frontend():
#     return send_from_directory('frontend', 'index.html')


# @app.route('/api/health', methods=['GET'])
# def health_check():
#     return jsonify({
#         'status':    'healthy',
#         'message':   'HR Resume Agent API is running',
#         'timestamp': datetime.now().isoformat(),
#     })


# @app.route('/api/analyze', methods=['POST'])
# @require_api_key
# @limiter.limit("20 per hour")
# def analyze_resumes():
#     """Analyze resumes against job description."""
#     try:
#         job_description = request.form.get('job_description', '')

#         if not job_description or len(job_description.strip()) < 10:
#             return jsonify({'error': 'Job description is required (min 10 chars)'}), 400

#         files = request.files.getlist('files')
#         if not files:
#             return jsonify({'error': 'No files uploaded'}), 400

#         results = []

#         for file in files:
#             if not (file and allowed_file(file.filename)):
#                 continue

#             filename = secure_filename(file.filename)
#             filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#             file.save(filepath)

#             try:
#                 print(f"Processing {filename}...")
#                 resume_text = extract_resume_text(filepath)

#                 if not resume_text or len(resume_text.strip()) < 50:
#                     raise ValueError("Could not extract sufficient text from resume")

#                 # score_resume returns a dict with dimension scores + total_score
#                 rubric = score_resume(job_description, resume_text)

#                 # --- FIX: pop internal keys before passing rubric to UI ---
#                 security_flag  = rubric.pop("_security_flag",  None)
#                 low_confidence = rubric.pop("_low_confidence", False)
#                 requirements   = rubric.pop("_requirements",   None)

#                 # --- FIX: use total_score computed inside scorer.py directly ---
#                 # scorer.py already applies the correct weighted formula (0.30/0.25/0.15/0.20/0.10)
#                 # DO NOT recompute via compute_rubric_score — that would ignore chain-of-thought reasoning
#                 final_score    = rubric.pop("total_score", 0)
#                 recommendation = get_recommendation(final_score)

#                 # Apply HR override if exists
#                 # if filename in overrides_store:
#                 #     final_score    = overrides_store[filename].get('score', final_score)
#                 #     recommendation = get_recommendation(final_score)

#                 log_analysis_event(
#                     filename, final_score, recommendation,
#                     low_confidence=low_confidence,
#                     security_flag=security_flag,
#                 )

#                 result = {
#                     'name':           filename,
#                     'score':          round(final_score, 2),
#                     'recommendation': recommendation,
#                     'low_confidence': low_confidence,
#                     'evaluation': {
#                         'skills_match':  rubric.get('skills_match',  {'score': 0, 'justification': 'N/A'}),
#                         'experience':    rubric.get('experience',     {'score': 0, 'justification': 'N/A'}),
#                         'education':     rubric.get('education',      {'score': 0, 'justification': 'N/A'}),
#                         'projects':      rubric.get('projects',       {'score': 0, 'justification': 'N/A'}),
#                         'communication': rubric.get('communication',  {'score': 0, 'justification': 'N/A'}),
#                     },
#                 }

#                 if security_flag:
#                     result['security_warning'] = security_flag

#                 results.append(result)
#                 print(f"✓ Processed {filename}: Score {final_score}"
#                       + (" [LOW CONFIDENCE]" if low_confidence else ""))

#             except Exception as e:
#                 print(f"Error processing {filename}: {e}")
#                 log_security_event("processing_error", str(e), endpoint="/api/analyze")
#                 results.append({
#                     'name': filename, 'score': 0, 'recommendation': 'Error',
#                     'low_confidence': True,
#                     'evaluation': {
#                         'skills_match':  {'score': 0, 'justification': f'Error: {str(e)[:100]}'},
#                         'experience':    {'score': 0, 'justification': 'Processing failed'},
#                         'education':     {'score': 0, 'justification': 'Check file format'},
#                         'projects':      {'score': 0, 'justification': 'Manual review recommended'},
#                         'communication': {'score': 0, 'justification': 'Review required'},
#                     },
#                 })
#             finally:
#                 if os.path.exists(filepath):
#                     os.remove(filepath)

#         results.sort(key=lambda x: x['score'], reverse=True)

#         try:
#             generate_json_report(results, 'outputs/report.json')
#             generate_html_report(results, 'outputs/report.html')
#             generate_pdf_report(results,  'outputs/report.pdf')
#         except Exception as e:
#             print(f"Report generation warning: {e}")

#         return jsonify(results)

#     except Exception as e:
#         print(f"Unexpected error: {e}")
#         log_security_event("unexpected_error", str(e), endpoint="/api/analyze")
#         return jsonify({'error': str(e)}), 500


# @app.route('/api/override', methods=['POST'])
# @require_api_key
# @limiter.limit("50 per hour")
# def save_override():
#     try:
#         data   = request.get_json()
#         name   = data.get('name')
#         score  = data.get('score')
#         reason = data.get('reason', '')

#         if not name or score is None:
#             return jsonify({'error': 'Name and score are required'}), 400

#         old_score = overrides_store.get(name, {}).get('score', None)
#         overrides_store[name] = {
#             'score':     score,
#             'reason':    reason,
#             'timestamp': datetime.now().isoformat(),
#         }
#         log_override(name, old_score, score, reason)
#         return jsonify({'status': 'success', 'message': f'Override saved for {name}'})

#     except Exception as e:
#         return jsonify({'error': str(e)}), 500


# @app.route('/api/overrides', methods=['GET'])
# @require_api_key
# def get_overrides():
#     return jsonify(overrides_store)


# @app.route('/api/fetch-linkedin', methods=['POST'])
# @require_api_key
# @limiter.limit("10 per hour")
# def fetch_linkedin():
#     try:
#         data = request.get_json()
#         url  = data.get('url', '').strip()

#         if not url or 'linkedin.com' not in url:
#             return jsonify({'error': 'Please provide a valid LinkedIn profile URL'}), 400

#         from core.linkedin_fetcher import fetch_linkedin_profile
#         profile_text = fetch_linkedin_profile(url)

#         if not profile_text or len(profile_text.strip()) < 50:
#             return jsonify({'error': 'Could not extract profile data from LinkedIn'}), 400

#         return jsonify({'text': profile_text, 'status': 'success'})

#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         # print(f"LinkedIn fetch error: {e}")
#         return jsonify({'error': str(e)}), 500


# # ---------------------------------------------------------------------------
# # Export routes
# # ---------------------------------------------------------------------------

# @app.route('/api/export/json', methods=['POST'])
# @require_api_key
# def export_json():
#     try:
#         data    = request.get_json()
#         content = json.dumps(data, indent=4)
#         return Response(content, mimetype='application/json',
#                         headers={'Content-Disposition': 'attachment; filename=hr_report.json'})
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500


# @app.route('/api/export/html', methods=['POST'])
# @require_api_key
# def export_html():
#     try:
#         data = request.get_json()
#         tmp  = tempfile.mktemp(suffix='.html')
#         generate_html_report(data, tmp)
#         with open(tmp) as f:
#             content = f.read()
#         os.remove(tmp)
#         return Response(content, mimetype='text/html',
#                         headers={'Content-Disposition': 'attachment; filename=hr_report.html'})
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500


# @app.route('/api/export/pdf', methods=['POST'])
# @require_api_key
# def export_pdf():
#     try:
#         data = request.get_json()
#         tmp  = tempfile.mktemp(suffix='.pdf')
#         generate_pdf_report(data, tmp)
#         return send_file(tmp, mimetype='application/pdf',
#                          as_attachment=True, download_name='hr_report.pdf')
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500


# # ---------------------------------------------------------------------------
# # Rate-limit error handler
# # ---------------------------------------------------------------------------
# @app.errorhandler(429)
# def ratelimit_handler(e):
#     log_security_event("rate_limit_exceeded", str(e), endpoint=request.path)
#     return jsonify({"error": "Too many requests — please slow down", "retry_after": "60s"}), 429


# # ---------------------------------------------------------------------------
# # Entry point
# # ---------------------------------------------------------------------------
# if __name__ == '__main__':
#     print("=" * 60)
#     print("🚀 HR Resume Agent API Server  [SECURITY-HARDENED]")
#     print("=" * 60)
#     if not _HR_API_KEY:
#         print("⚠️  WARNING: HR_API_KEY not set — endpoints are unprotected!")
#         print("   Add  HR_API_KEY=your-secret  to your .env file.")
#     else:
#         print("✅  API key authentication: ENABLED")
#     print("✅  Rate limiting:            ENABLED")
#     print("✅  PII masking in logs:      ENABLED")
#     print("✅  Prompt injection guard:   ENABLED  (via scorer + sanitizer)")
#     print("✅  Pydantic output schema:   ENABLED  (via llm_utils)")
#     print(f"\n📍 http://localhost:8000")
#     print("=" * 60)
#     app.run(host='0.0.0.0', port=8000, debug=False)



"""
api_server.py  (SECURITY-HARDENED)
------------------------------------
Security additions vs original:
  1. API-key authentication on all /api/* endpoints
  2. Rate limiting (Flask-Limiter)  — prevents abuse
  3. Security event logging via audit_logger
  4. Injection-detected results surfaced as warnings (not silently dropped)
  5. Low-confidence flag passed through to HR UI
  6. .env-only secrets; no hardcoded credentials anywhere
"""

from flask import Flask, request, jsonify, send_from_directory, Response, send_file, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
import os
import json
import sys
import tempfile
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

# ── CHANGED: point to core/ package instead of flat imports ──
from core.parser import extract_resume_text
from core.scorer import score_resume
from core.ranker import get_recommendation
from core.report_generator import generate_json_report, generate_html_report, generate_pdf_report
from core.audit_logger import log_override, log_analysis_event, log_security_event

app = Flask(
    __name__,
    static_folder="frontend",   # ── CHANGED: serve static files from frontend/
    template_folder="frontend"
)
CORS(app)

# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "60 per hour"],
    storage_uri="memory://",
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
UPLOAD_FOLDER      = 'temp_uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}
app.config['UPLOAD_FOLDER']      = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('outputs',     exist_ok=True)

overrides_store = {}

# ---------------------------------------------------------------------------
# API Key Authentication
# ---------------------------------------------------------------------------
_HR_API_KEY = os.getenv("HR_API_KEY")

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not _HR_API_KEY:
            print("[SECURITY WARNING] HR_API_KEY is not set — endpoint is unprotected!")
            return f(*args, **kwargs)
        provided = request.headers.get("X-API-Key", "").strip()
        if not provided or provided != _HR_API_KEY:
            log_security_event(
                "auth_failure",
                f"Invalid or missing API key from {get_remote_address()}",
                endpoint=request.path,
            )
            return jsonify({"error": "Unauthorised — valid X-API-Key header required"}), 401
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def serve_frontend():
    return send_from_directory('frontend', 'index.html')

@app.route('/frontend/<path:filename>')
def serve_static(filename):
    return send_from_directory('frontend', filename)


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status':    'healthy',
        'message':   'HR Resume Agent API is running',
        'timestamp': datetime.now().isoformat(),
    })


@app.route('/api/analyze', methods=['POST'])
@require_api_key
@limiter.limit("20 per hour")
def analyze_resumes():
    """Analyze resumes against job description."""
    try:
        job_description = request.form.get('job_description', '')

        if not job_description or len(job_description.strip()) < 10:
            return jsonify({'error': 'Job description is required (min 10 chars)'}), 400

        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No files uploaded'}), 400

        results = []

        for file in files:
            if not (file and allowed_file(file.filename)):
                continue

            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                print(f"Processing {filename}...")
                resume_text = extract_resume_text(filepath)

                if not resume_text or len(resume_text.strip()) < 50:
                    raise ValueError("Could not extract sufficient text from resume")

                rubric = score_resume(job_description, resume_text)

                security_flag  = rubric.pop("_security_flag",  None)
                low_confidence = rubric.pop("_low_confidence", False)
                requirements   = rubric.pop("_requirements",   None)

                final_score    = rubric.pop("total_score", 0)
                recommendation = get_recommendation(final_score)

                log_analysis_event(
                    filename, final_score, recommendation,
                    low_confidence=low_confidence,
                    security_flag=security_flag,
                )

                result = {
                    'name':           filename,
                    'score':          round(final_score, 2),
                    'recommendation': recommendation,
                    'low_confidence': low_confidence,
                    'evaluation': {
                        'skills_match':  rubric.get('skills_match',  {'score': 0, 'justification': 'N/A'}),
                        'experience':    rubric.get('experience',     {'score': 0, 'justification': 'N/A'}),
                        'education':     rubric.get('education',      {'score': 0, 'justification': 'N/A'}),
                        'projects':      rubric.get('projects',       {'score': 0, 'justification': 'N/A'}),
                        'communication': rubric.get('communication',  {'score': 0, 'justification': 'N/A'}),
                    },
                }

                if security_flag:
                    result['security_warning'] = security_flag

                results.append(result)
                print(f"✓ Processed {filename}: Score {final_score}"
                      + (" [LOW CONFIDENCE]" if low_confidence else ""))

            except Exception as e:
                print(f"Error processing {filename}: {e}")
                log_security_event("processing_error", str(e), endpoint="/api/analyze")
                results.append({
                    'name': filename, 'score': 0, 'recommendation': 'Error',
                    'low_confidence': True,
                    'evaluation': {
                        'skills_match':  {'score': 0, 'justification': f'Error: {str(e)[:100]}'},
                        'experience':    {'score': 0, 'justification': 'Processing failed'},
                        'education':     {'score': 0, 'justification': 'Check file format'},
                        'projects':      {'score': 0, 'justification': 'Manual review recommended'},
                        'communication': {'score': 0, 'justification': 'Review required'},
                    },
                })
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)

        results.sort(key=lambda x: x['score'], reverse=True)

        try:
            generate_json_report(results, 'outputs/report.json')
            generate_html_report(results, 'outputs/report.html')
            generate_pdf_report(results,  'outputs/report.pdf')
        except Exception as e:
            print(f"Report generation warning: {e}")

        return jsonify(results)

    except Exception as e:
        print(f"Unexpected error: {e}")
        log_security_event("unexpected_error", str(e), endpoint="/api/analyze")
        return jsonify({'error': str(e)}), 500


@app.route('/api/override', methods=['POST'])
@require_api_key
@limiter.limit("50 per hour")
def save_override():
    try:
        data   = request.get_json()
        name   = data.get('name')
        score  = data.get('score')
        reason = data.get('reason', '')

        if not name or score is None:
            return jsonify({'error': 'Name and score are required'}), 400

        old_score = overrides_store.get(name, {}).get('score', None)
        overrides_store[name] = {
            'score':     score,
            'reason':    reason,
            'timestamp': datetime.now().isoformat(),
        }
        log_override(name, old_score, score, reason)
        return jsonify({'status': 'success', 'message': f'Override saved for {name}'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/overrides', methods=['GET'])
@require_api_key
def get_overrides():
    return jsonify(overrides_store)


@app.route('/api/fetch-linkedin', methods=['POST'])
@require_api_key
@limiter.limit("10 per hour")
def fetch_linkedin():
    try:
        data = request.get_json()
        url  = data.get('url', '').strip()

        if not url or 'linkedin.com' not in url:
            return jsonify({'error': 'Please provide a valid LinkedIn profile URL'}), 400

        # ── CHANGED: import from core/
        from core.linkedin_fetcher import fetch_linkedin_profile
        profile_text = fetch_linkedin_profile(url)

        if not profile_text or len(profile_text.strip()) < 50:
            return jsonify({'error': 'Could not extract profile data from LinkedIn'}), 400

        return jsonify({'text': profile_text, 'status': 'success'})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Export routes
# ---------------------------------------------------------------------------

@app.route('/api/export/json', methods=['POST'])
@require_api_key
def export_json():
    try:
        data    = request.get_json()
        content = json.dumps(data, indent=4)
        return Response(content, mimetype='application/json',
                        headers={'Content-Disposition': 'attachment; filename=hr_report.json'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/html', methods=['POST'])
@require_api_key
def export_html():
    try:
        data = request.get_json()
        tmp  = tempfile.mktemp(suffix='.html')
        generate_html_report(data, tmp)
        with open(tmp) as f:
            content = f.read()
        os.remove(tmp)
        return Response(content, mimetype='text/html',
                        headers={'Content-Disposition': 'attachment; filename=hr_report.html'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/pdf', methods=['POST'])
@require_api_key
def export_pdf():
    try:
        data = request.get_json()
        tmp  = tempfile.mktemp(suffix='.pdf')
        generate_pdf_report(data, tmp)
        return send_file(tmp, mimetype='application/pdf',
                         as_attachment=True, download_name='hr_report.pdf')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Rate-limit error handler
# ---------------------------------------------------------------------------
@app.errorhandler(429)
def ratelimit_handler(e):
    log_security_event("rate_limit_exceeded", str(e), endpoint=request.path)
    return jsonify({"error": "Too many requests — please slow down", "retry_after": "60s"}), 429


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 HR Resume Agent API Server  [SECURITY-HARDENED]")
    print("=" * 60)
    if not _HR_API_KEY:
        print("⚠️  WARNING: HR_API_KEY not set — endpoints are unprotected!")
        print("   Add  HR_API_KEY=your-secret  to your .env file.")
    else:
        print("✅  API key authentication: ENABLED")
    print("✅  Rate limiting:            ENABLED")
    print("✅  PII masking in logs:      ENABLED")
    print("✅  Prompt injection guard:   ENABLED  (via scorer + sanitizer)")
    print("✅  Pydantic output schema:   ENABLED  (via llm_utils)")
    print(f"\n📍 http://localhost:8000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=8000, debug=False)