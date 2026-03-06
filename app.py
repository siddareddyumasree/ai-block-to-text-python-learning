
from flask import Flask, render_template, request, jsonify
import requests, os, contextlib, io, traceback, re, html, json
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user
)
from passlib.hash import bcrypt

# ---------------------- App / Config ----------------------
load_dotenv()
app = Flask(__name__)

# llama.cpp server (run separately)
# Example:
#   ./build/bin/llama-server -m ./phi2-chat-Q4_K_M.gguf -ngl 999 -t 8 -c 2048 --port 8080
LLAMA_URL = os.getenv("LLAMA_URL", "http://127.0.0.1:8080/v1/completions")

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login_page"

# ---------------------- Models ----------------------
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    grade = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(255), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class SavedWork(db.Model):
    __tablename__ = "saved_work"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True, nullable=False)
    feature = db.Column(db.String(50), nullable=False)     # chatbot | question | blockly | editor
    title = db.Column(db.String(255), nullable=True)       # optional human label
    payload = db.Column(db.Text, nullable=False)           # JSON/text
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    user = db.relationship("User", backref="works")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# ---------------------- LLM helpers ----------------------
STOP_WORDS = [
    "<|im_start|>", "<|im_end|>", "<im_start>", "<im_end>",
    "### Instruction:", "### Input:", "### Output:", "User:", "Assistant:"
]

def make_prompt(system_prompt: str, user_text: str) -> str:
    return (
        "### Instruction:\n"
        f"{system_prompt}\n\n"
        "### Input:\n"
        f"{user_text}\n\n"
        "### Output:"
    )

def llama_complete(system_prompt: str, user_text: str, max_tokens=320, temperature=0.5):
    prompt = make_prompt(system_prompt, user_text)
    r = requests.post(
        LLAMA_URL,
        json={
            "model": "local-phi2",
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
            "stop": STOP_WORDS,
        },
        timeout=120,
    )
    r.raise_for_status()
    return (r.json().get("choices") or [{}])[0].get("text", "").strip()

def strip_noise(s: str) -> str:
    s = re.sub(r"[^\x00-\x7F]+", "", s)  # remove non-ascii artifacts
    for t in STOP_WORDS: s = s.replace(t, "")
    return s.strip()

def detect_intent(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["traceback", "error", "bug", "fix", "not working", "debug"]): return "debug"
    if any(k in t for k in ["explain this code", "explain code", "what does this code do"]): return "explain_code"
    if any(k in t for k in ["what is", "why is", "how does", "difference between", "define", "concept"]): return "concept"
    if any(x in t for x in ["def ", "for ", "while ", "class ", "print(", "import "]): return "explain_code"
    return "code_gen"

def render_html_from_response(text: str) -> str:
    """Render markdown/code into HTML with a nice code block if present."""
    text = strip_noise(text)
    text = re.sub(r"(?i)\b(output|response)\s*:\s*", "", text).strip()
    m = re.search(r"```(?:python)?\s*([\s\S]+?)```", text, re.IGNORECASE)
    if m:
        code = m.group(1).strip()
        rest = (text[:m.start()] + text[m.end():]).strip()
        parts = [f"<pre><code class='language-python'>{html.escape(code)}</code></pre>"]
        if rest:
            parts.append(f"<div style='margin-top:10px;'>{html.escape(rest)}</div>")
        return "".join(parts)
    return f"<div>{html.escape(text)}</div>"

# ---------- Helpers for robust question generation ----------
def _sanitize_q(raw: str, topic: str) -> str:
    """Clean model output down to one coding-task line (no answers/headers)."""
    if not raw:
        return ""
    s = strip_noise(raw)

    # remove code fences / inline code
    s = re.sub(r"```.*?```", "", s, flags=re.S)
    s = re.sub(r"`[^`]*`", "", s)

    # cut anything after typical “answer-ish” markers
    s = re.sub(r"(?i)(answer|solution|explanation|example|sample output|output|steps|hint)\s*:\s*.*", "", s)

    # keep first non-empty line
    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    s = lines[0] if lines else ""

    # collapse weird spaces and trailing punctuation spam
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s*[\-\:\*#]+$", "", s).strip()

    # if it looks conceptual, nudge it into a coding task
    if re.match(r"(?i)\s*(what|why|how|define|explain)\b", s):
        s = f"Use {topic} to write a short Python program that demonstrates it in action."
    return s

def _fallback_q(topic: str) -> str:
    """Always return a simple coding task for the given topic."""
    t = topic.lower()
    if "variable" in t:
        return "Create two variables name and age, assign your own values, then print: Hello <name>, you are <age>."
    if "loop" in t:
        return "Read an integer n and use a for loop to print the sum of numbers from 1 to n."
    if "conditional" in t or "if" in t:
        return "Read an integer score and print 'Pass' if score >= 50 else 'Fail' using an if-elif-else block."
    if "function" in t:
        return "Write a function count_vowels(s) that returns how many vowels are in the string s; show one example call."
    if "list" in t:
        return "Given a list of integers, print the largest number and its index in the list."
    if "string" in t:
        return "Ask the user for a sentence and print the sentence reversed without using slicing shortcuts."
    if "dictionary" in t:
        return "Create a dictionary of three countries to their capitals and print each pair as 'Country: Capital'."
    if "input" in t or "output" in t:
        return "Read two integers from input and print their sum, difference, product, and integer division result."
    if "boolean" in t:
        return "Read two integers a and b, then print True if a is even AND b is odd, otherwise print False."
    if "array" in t:
        return "Read a line of space-separated integers into a list and print the list without duplicates (preserve order)."
    if "class" in t or "object" in t:
        return "Define a class Book with title and author; create one object and print 'title by author'."
    # generic fallback
    return f"Write a small Python program that uses {topic} to transform input and print a result."

# ---------------------- Pages ----------------------
from flask import render_template as _rt

@app.route('/')
def home(): return _rt('index.html')

@app.route('/python_editor')
def python_editor(): return _rt('python_editor.html')

@app.route('/question_generator')
def question_generator(): return _rt('question_generator.html')

@app.route('/blockly_solver')
def blockly_solver(): return _rt('blockly_solver.html')

@app.route('/chatbot')
def chatbot(): return _rt('chatbot.html')

@app.route("/learn")
def learn(): return _rt("learn.html")

@app.route("/learn/<topic_name>")
def learn_topic(topic_name):
    try: return _rt(f"topics/{topic_name}.html")
    except Exception: return f"<h3 style='padding: 40px;'>Topic page not found for: <code>{html.escape(topic_name)}</code></h3>", 404

# ---------------------- Auth (pages) ----------------------
@app.route("/register", methods=["GET"])
def register_page(): return _rt("register.html")

@app.route("/login", methods=["GET"])
def login_page(): return _rt("login.html")

# ---------------------- Auth (JSON) ----------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    grade = (data.get("grade") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()
    if not name or not email or not password:
        return jsonify({"error": "name, email and password are required"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "email already registered"}), 409
    user = User(name=name, grade=grade or None, email=email, password_hash=bcrypt.hash(password))
    db.session.add(user); db.session.commit()
    return jsonify({"message": "registered"}), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()
    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.verify(password, user.password_hash):
        return jsonify({"error": "invalid credentials"}), 401
    login_user(user)
    return jsonify({"message": "logged_in", "user_id": user.id})

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "logged_out"})

@app.route("/me", methods=["GET"])
def me():
    if current_user.is_authenticated:
        return jsonify({"authenticated": True, "email": current_user.email, "name": current_user.name, "grade": current_user.grade})
    return jsonify({"authenticated": False})

# ---------------------- Save / Load / Delete ----------------------
@app.route("/api/save_work", methods=["POST"])
@login_required
def save_work():
    data = request.get_json() or {}
    feature = (data.get("feature") or "").strip()
    title = (data.get("title") or "").strip()
    payload = data.get("payload")
    if not feature or payload is None:
        return jsonify({"error": "feature and payload required"}), 400
    if not isinstance(payload, str):
        payload = json.dumps(payload, ensure_ascii=False)
    rec = SavedWork(user_id=current_user.id, feature=feature, title=title or None, payload=payload)
    db.session.add(rec); db.session.commit()
    return jsonify({"message": "saved", "id": rec.id})

@app.route("/api/work", methods=["GET"])
@login_required
def list_work():
    feature = (request.args.get("feature") or "").strip()
    try:
        limit = int(request.args.get("limit", "50"))
        offset = int(request.args.get("offset", "0"))
    except ValueError:
        return jsonify({"error": "limit/offset must be integers"}), 400
    q = SavedWork.query.filter_by(user_id=current_user.id)
    if feature: q = q.filter_by(feature=feature)
    q = q.order_by(SavedWork.updated_at.desc()).offset(offset).limit(min(limit, 200))
    items = []
    for r in q.all():
        items.append({
            "id": r.id,
            "feature": r.feature,
            "title": r.title,
            "payload": r.payload,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None
        })
    return jsonify({"items": items})

@app.route("/api/work/<int:work_id>", methods=["GET", "DELETE"])
@login_required
def get_or_delete_work(work_id):
    rec = SavedWork.query.filter_by(id=work_id, user_id=current_user.id).first()
    if not rec:
        return jsonify({"error": "not found"}), 404
    if request.method == "GET":
        return jsonify({
            "id": rec.id,
            "feature": rec.feature,
            "title": rec.title,
            "payload": rec.payload,
            "created_at": rec.created_at.isoformat() if rec.created_at else None,
            "updated_at": rec.updated_at.isoformat() if rec.updated_at else None
        })
    db.session.delete(rec); db.session.commit()
    return jsonify({"message": "deleted"})

@app.route("/api/load_work", methods=["GET"])
@login_required
def load_work():
    return list_work()

# ---------------------- APIs: Question Generator / Chatbot / Runner ----------------------
@app.route('/generate_question', methods=['POST'])
def generate_question_api():
    """
    Always return ONE clean coding question (no 'One possible question is', no answers).
    """
    try:
        data = request.get_json() or {}
        topic = (data.get('topic') or "").strip()
        if not topic:
            return jsonify({'error': 'Topic not provided'}), 400
        system_prompt = (
            "You generate exactly ONE Python CODING QUESTION.\n"
            "Rules:\n"
            "- It MUST require writing runnable Python code.\n"
            "- It MUST be related to the given topic.\n"
            "- Do NOT include answers, solutions, sample outputs, or explanations.\n"
            "- Output only the plain question text on one line.")
        user_text = f"Topic: {topic}\nGive one clear python coding question using this topic only."
        raw = llama_complete(system_prompt, user_text, max_tokens=80, temperature=0.3)
        q = strip_noise(raw)
        q = re.sub(r"```.*?```", "", q, flags=re.S)
        q = re.sub(r"`[^`]*`", "", q)
        q = re.sub(r"(?i)(answer|solution|explanation|example|output)[:].*", "", q)
        q = (q.splitlines() or [""])[0].strip()
        # ✨ remove filler prefixes like "One possible question is", "Question:", etc.
        q = re.sub(r"(?i)^(one possible question is|possible question is|here'?s a question|question)\s*[:\-]*\s*", "", q).strip()
        # fallback if blank
        if not q:
            q = f"Write a Python program that demonstrates {topic} with a small example."

        return jsonify({'question': q})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chatbot_response', methods=['POST'])
def chatbot_response():
    """
    Handles debug / explain_code / concept / code_gen intents.
    We ask for code + short explanation where sensible; output is rendered cleanly.
    """
    try:
        data = request.get_json() or {}
        user_message = (data.get('user_message') or "").strip()
        if not user_message:
            return jsonify({'error': 'User message not provided'}), 400

        intent = detect_intent(user_message)

        if intent == "debug":
            system_prompt = (
                "You are a senior Python tutor.\n"
                "Task: Fix the user's code and explain the bug briefly.\n"
                "Format:\n"
                "1) Corrected code in a ```python fenced block.\n"
                "2) One short paragraph explaining the bug and the fix.\n"
                "Answer only in that format."
            )
            temp = 0.25
            max_tok = 900

        elif intent == "explain_code":
            system_prompt = (
                "You are a senior Python tutor.\n"
                "Explain clearly what the code does.\n"
                "If useful, include an improved version inside a ```python fenced block, "
                "then a short explanation paragraph.\n"
                "No extra sections."
            )
            temp = 0.35
            max_tok = 900

        elif intent == "concept":
            system_prompt = (
                "You are a senior Python tutor.\n"
                "Give a clear, concise explanation of the concept with a tiny code snippet if helpful "
                "in a ```python fenced block. Keep it short and focused."
            )
            temp = 0.45
            max_tok = 700

        else:  # code_gen
            system_prompt = (
                "You are a senior Python tutor.\n"
                "First provide correct Python code in a ```python fenced block, "
                "then a short explanation paragraph. No extra headings."
            )
            temp = 0.35
            max_tok = 900

        raw = llama_complete(system_prompt, user_message, max_tokens=max_tok, temperature=temp)
        html_out = render_html_from_response(raw)
        return jsonify({'bot_response': html_out})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/run', methods=['POST'])
def run_code():
    data = request.get_json() or {}
    code = data.get('code', '')
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            exec(code, {})
        result = output.getvalue()
    except Exception:
        result = traceback.format_exc()
    return jsonify({'output': result})

# ---------------------- Main ----------------------
if __name__ == '__main__':
    app.run(debug=True)
