import os
import time
from pathlib import Path
from urllib.parse import quote
from flask import Flask, render_template, request, jsonify, abort
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "photos").strip("/")
DATA_XLSX_PATH = os.getenv("DATA_XLSX_PATH", "data/reviews.xlsx")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret")
ADMIN_RELOAD_TOKEN = os.getenv("ADMIN_RELOAD_TOKEN", "")

BASE_DIR = Path(__file__).resolve().parent.parent  # project root
XLSX_FILE = (BASE_DIR / DATA_XLSX_PATH).resolve()

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(BASE_DIR / "static"))
app.secret_key = FLASK_SECRET_KEY

CACHE = {
    "loaded_at": 0,
    "rows": [],
    "branches": [],
    "file_mtime": None
}

def clamp_rating(x):
    try:
        v = float(x)
    except Exception:
        return 0.0
    if v < 1: v = 1.0
    if v > 5: v = 5.0
    return round(v, 1)

def normalize_image_path(raw: str) -> str:
    """
    Accepts:
    - student_images/xxx.jpg
    - photos/student_images/xxx.jpg  (bucket included)
    - /student_images/xxx.jpg
    - full URL (http...)
    Returns:
    - usable URL for public bucket OR placeholder marker.
    """
    if not raw or str(raw).strip().lower() in ("nan", "none", ""):
        return ""

    s = str(raw).strip()

    # If already a full URL, return as-is
    if s.startswith("http://") or s.startswith("https://"):
        return s

    # remove leading slashes
    s = s.lstrip("/")

    # If user accidentally included bucket name (photos/...), strip it
    # e.g. photos/student_images/.. -> student_images/..
    if s.startswith(SUPABASE_BUCKET + "/"):
        s = s[len(SUPABASE_BUCKET) + 1 :]

    # URL-encode path safely (spaces etc.)
    safe_path = "/".join(quote(part) for part in s.split("/"))

    # Build Supabase public URL
    # https://<project>.supabase.co/storage/v1/object/public/<bucket>/<path>
    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{safe_path}"

def load_reviews(force=False):
    if not XLSX_FILE.exists():
        raise FileNotFoundError(f"Excel file not found: {XLSX_FILE}")

    mtime = XLSX_FILE.stat().st_mtime
    if (not force) and CACHE["file_mtime"] == mtime and CACHE["rows"]:
        return

    df = pd.read_excel(XLSX_FILE, engine="openpyxl")

    required = ["S.No", "Roll Number", "Full Name", "Branch", "Rating (1-5)", "Review/Comment", "Image Path"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing column in Excel: {col}")

    rows = []
    for _, r in df.iterrows():
        roll = str(r.get("Roll Number", "")).strip()
        name = str(r.get("Full Name", "")).strip()
        branch = str(r.get("Branch", "")).strip()
        rating = clamp_rating(r.get("Rating (1-5)", 0))
        comment = str(r.get("Review/Comment", "")).strip()
        if comment.lower() in ("nan", "none"):
            comment = ""
        img_raw = r.get("Image Path", "")
        img_url = normalize_image_path(img_raw)

        rows.append({
            "sno": int(r.get("S.No")) if str(r.get("S.No")).strip().isdigit() else r.get("S.No"),
            "roll": roll,
            "name": name,
            "branch": branch,
            "rating": rating,
            "comment": comment if comment else "No comment provided.",
            "img_url": img_url
        })

    branches = sorted({x["branch"] for x in rows if x["branch"]})

    CACHE["rows"] = rows
    CACHE["branches"] = branches
    CACHE["file_mtime"] = mtime
    CACHE["loaded_at"] = int(time.time())

def query_rows(q, branch, sort_key):
    rows = CACHE["rows"]

    if q:
        qq = q.strip().lower()
        rows = [
            r for r in rows
            if qq in (r["roll"] or "").lower()
            or qq in (r["name"] or "").lower()
            or qq in (r["branch"] or "").lower()
        ]

    if branch and branch != "All":
        rows = [r for r in rows if r["branch"] == branch]

    if sort_key == "rating_desc":
        rows = sorted(rows, key=lambda x: (x["rating"], x["sno"]), reverse=True)
    elif sort_key == "name_asc":
        rows = sorted(rows, key=lambda x: (x["name"] or "").lower())
    else:  # default: latest by S.No desc
        rows = sorted(rows, key=lambda x: x["sno"], reverse=True)

    return rows

@app.get("/")
def home():
    load_reviews()

    q = request.args.get("q", "").strip()
    branch = request.args.get("branch", "All").strip()
    sort_key = request.args.get("sort", "latest").strip()
    page = request.args.get("page", "1").strip()

    try:
        page = max(1, int(page))
    except Exception:
        page = 1

    per_page = 10

    filtered = query_rows(q, branch, sort_key)
    total = len(filtered)
    pages = max(1, (total + per_page - 1) // per_page)
    if page > pages:
        page = pages

    start = (page - 1) * per_page
    end = start + per_page
    items = filtered[start:end]

    return render_template(
        "index.html",
        items=items,
        branches=CACHE["branches"],
        q=q,
        branch=branch,
        sort=sort_key,
        page=page,
        pages=pages,
        total=total,
        loaded_at=CACHE["loaded_at"]
    )

@app.post("/admin/reload")
def admin_reload():
    if not ADMIN_RELOAD_TOKEN:
        abort(403)
    token = request.headers.get("x-reload-token", "")
    if token != ADMIN_RELOAD_TOKEN:
        abort(403)
    load_reviews(force=True)
    return jsonify({"ok": True, "count": len(CACHE["rows"]), "loaded_at": CACHE["loaded_at"]})

# Vercel entrypoint
# Vercel auto-detects `app` in this file.

