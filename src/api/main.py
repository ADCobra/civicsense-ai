from pathlib import Path
from dotenv import load_dotenv
import os

project_root = Path(__file__).resolve().parent.parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import csv
import json
import re
import psycopg2
import asyncio

from src.ai.match_agent import MatchAgent


# -----------------------------------------------------------------------------
# App Setup
# -----------------------------------------------------------------------------

app = FastAPI(
    title="CivicSense AI API",
    description="Discover government schemes personalized for you",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Database Configuration & In-Memory Fallback
# -----------------------------------------------------------------------------

DB_CONFIG = {
    "host": "localhost",
    "database": "civicsense",
    "user": "civicsense",
    "password": "civicsense_dev_password"
}

# When PostgreSQL is not running, use this list so the app still works
IN_MEMORY_SCHEMES: List[Dict[str, Any]] = []
_db_available: Optional[bool] = None


def _check_db():
    global _db_available
    if _db_available is not None:
        return _db_available
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.close()
        _db_available = True
    except Exception as e:
        print("PostgreSQL not available:", e)
        print("Using in-memory storage. Start Postgres to use the database.")
        _db_available = False
    return _db_available


def execute_query(query: str) -> List[Dict]:
    if not _check_db():
        return []
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(query)
        columns = [desc[0] for desc in cur.description]
        results = [dict(zip(columns, row)) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return results
    except Exception as e:
        print("Query error:", e)
        return []


def execute_count(query: str) -> int:
    if not _check_db():
        return len(IN_MEMORY_SCHEMES)
    results = execute_query(query)
    if results and "count" in results[0]:
        return results[0]["count"]
    return 0


def execute_insert_many(query: str, rows: List[tuple]) -> int:
    if not rows:
        return 0
    if not _check_db():
        return 0
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.executemany(query, rows)
        conn.commit()
        n = cur.rowcount
        cur.close()
        conn.close()
        return n
    except Exception as e:
        print("Insert error:", e)
        raise


# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------

class UserProfile(BaseModel):
    age: Optional[int] = Field(None, ge=1, le=100)
    state: Optional[str] = None
    annual_income: Optional[int] = None
    caste_category: Optional[str] = None
    occupation: Optional[str] = None
    gender: Optional[str] = None
    education: Optional[str] = None
    interests: Optional[str] = None
    is_disabled: Optional[bool] = False
    is_bpl: Optional[bool] = False


class SchemeBasic(BaseModel):
    id: str
    title: str
    opportunity_type: str
    issuing_authority: str
    ai_summary: Optional[str] = None
    match_score: Optional[float] = None


class SearchResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: List[SchemeBasic]
    facets: Optional[Dict[str, Dict[str, int]]] = None


class StatsResponse(BaseModel):
    total_schemes: int
    by_category: Dict[str, int]
    by_ministry: Dict[str, int]
    recently_added: int


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    user_id: str
    email: str
    role: str
    token: str
    is_verified: bool = False


class SendOtpRequest(BaseModel):
    aadhar_number: str


class VerifyOtpRequest(BaseModel):
    aadhar_number: str
    otp: str


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "CivicSense AI API",
        "version": "1.0.0",
        "docs": "/api/docs"
    }


@app.get("/api/v1/health")
def health_check():
    count = execute_count("SELECT COUNT(*) FROM opportunities")
    return {
        "status": "healthy",
        "database": "connected" if _check_db() else "in-memory (no PostgreSQL)",
        "total_schemes": count
    }


@app.post("/api/v1/auth/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    # Simple hardcoded check for demo purposes
    # In a real app, this would query the DB and use hashed passwords
    if req.email == "demo@civicsense.ai" and req.password == "password":
        return AuthResponse(
            user_id="user_123",
            email=req.email,
            role="user",
            token="mock_token_jwt_style"
        )
    elif req.email == "admin@civicsense.ai" and req.password == "admin":
        return AuthResponse(
            user_id="admin_001",
            email=req.email,
            role="admin",
            token="mock_token_admin"
        )
    else:
        raise HTTPException(status_code=401, detail="Invalid email or password")


@app.post("/api/v1/auth/register", response_model=AuthResponse)
async def register(req: LoginRequest):
    # For demo purposes, we just return a success response immediately.
    # In a real application, you would save the user info to the database.
    return AuthResponse(
        user_id="user_" + str(hash(req.email)),
        email=req.email,
        role="user",
        token="mock_token_registration",
        is_verified=False
    )


@app.post("/api/v1/auth/send-otp")
async def send_otp(req: SendOtpRequest):
    # Simulate sending an OTP
    if len(req.aadhar_number) != 12 or not req.aadhar_number.isdigit():
        raise HTTPException(status_code=400, detail="Invalid Aadhar number format")
    
    return {"message": "OTP sent to registered mobile number/email successfully"}


@app.post("/api/v1/auth/verify-otp")
async def verify_otp(req: VerifyOtpRequest):
    # Simulate OTP verification
    if req.otp == "123456":
        return {"message": "Verification successful", "is_verified": True}
    else:
        raise HTTPException(status_code=400, detail="Invalid OTP")


def _schemes_for_list(page: int, page_size: int) -> tuple:
    """Return (total, results) from DB or in-memory."""
    if _check_db():
        total = execute_count("SELECT COUNT(*) FROM opportunities")
        offset = (page - 1) * page_size
        results = execute_query(
            f"SELECT id, title, opportunity_type, issuing_authority, ai_summary FROM opportunities ORDER BY published_date DESC LIMIT {page_size} OFFSET {offset}"
        )
        return total, results
    total = len(IN_MEMORY_SCHEMES)
    offset = (page - 1) * page_size
    chunk = IN_MEMORY_SCHEMES[offset : offset + page_size]
    results = [
        {
            "id": s.get("id", ""),
            "title": s.get("title", ""),
            "opportunity_type": s.get("opportunity_type", "welfare_scheme"),
            "issuing_authority": s.get("issuing_authority", ""),
            "ai_summary": s.get("ai_summary"),
        }
        for s in chunk
    ]
    return total, results


@app.get("/api/v1/schemes", response_model=SearchResponse)
def list_schemes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    total, results = _schemes_for_list(page, page_size)
    return SearchResponse(
        total=total,
        page=page,
        page_size=page_size,
        results=results,
        facets={"categories": {}, "ministries": {}}
    )

def _schemes_for_match() -> List[Dict]:
    """Full scheme list for matching: from DB or IN_MEMORY_SCHEMES."""
    if _check_db():
        return execute_query("""
            SELECT id, title, description, source_url, opportunity_type, issuing_authority,
                   eligibility, benefit_description, required_documents, application_url,
                   published_date, trust_score, verification_status, ai_summary
            FROM opportunities ORDER BY trust_score DESC, published_date DESC LIMIT 50
        """)
    return list(IN_MEMORY_SCHEMES)


@app.post("/api/v1/match")
async def match_schemes(profile: UserProfile):
    results = _schemes_for_match()
    matches = []
    
    match_agent = MatchAgent()
    
    # We will process all scheme evaluations concurrently
    tasks = []
    schemes_to_process = []

    for scheme in results:
        # Parse JSON safely (DB returns strings; in-memory may already be dict/list)
        el = scheme.get("eligibility")
        if isinstance(el, dict):
            eligibility = el
        else:
            try:
                eligibility = json.loads(el or "{}") if el else {}
            except Exception:
                eligibility = {}
        # If we only have "raw" text (e.g. from CSV), parse it into age/income/caste so we can score
        if eligibility and not any(eligibility.get(k) for k in ("age_min", "age_max", "income_limit", "caste_category", "state")):
            raw = eligibility.get("raw") or ""
            if isinstance(raw, str) and raw.strip():
                parsed = _parse_eligibility_from_raw(raw)
                eligibility = {**eligibility, **{k: v for k, v in parsed.items() if k != "raw"}}
        scheme["eligibility"] = eligibility

        rd = scheme.get("required_documents")
        if isinstance(rd, list):
            scheme["required_documents"] = rd
        else:
            try:
                scheme["required_documents"] = json.loads(rd or "[]")
            except Exception:
                scheme["required_documents"] = []

        scheme_dict = dict(scheme)
        schemes_to_process.append(scheme_dict)
        
        # Add the evaluation task
        tasks.append(match_agent.evaluate(profile.model_dump(), scheme_dict))
        
    # Run all LLM evaluations concurrently
    eval_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, scheme_dict in enumerate(schemes_to_process):
        res = eval_results[i]
        if isinstance(res, Exception):
            print(f"Error evaluating scheme {scheme_dict.get('id')}: {res}")
            scheme_dict["match_score"] = 0.5
            scheme_dict["ai_reasoning"] = "AI evaluation failed."
        else:
            scheme_dict["match_score"] = res.get("match_score", 0.5)
            scheme_dict["ai_reasoning"] = res.get("ai_reasoning", "")
            
        matches.append(scheme_dict)

    # Sort by match score
    matches.sort(key=lambda x: x["match_score"], reverse=True)

    return {
        "total_matches": len(matches),
        "top_matches": matches[:5],
        "recommendations": matches[5:10]
    }

@app.get("/api/v1/stats", response_model=StatsResponse)
def get_stats():
    total = execute_count("SELECT COUNT(*) FROM opportunities")

    cat_results = execute_query("""
        SELECT opportunity_type, COUNT(*) as count
        FROM opportunities
        GROUP BY opportunity_type
    """)

    by_category = {row["opportunity_type"]: row["count"] for row in cat_results}

    min_results = execute_query("""
        SELECT issuing_authority, COUNT(*) as count
        FROM opportunities
        GROUP BY issuing_authority
    """)

    by_ministry = {row["issuing_authority"]: row["count"] for row in min_results}

    recently = execute_count("""
        SELECT COUNT(*) FROM opportunities
        WHERE published_date >= NOW() - INTERVAL '30 days'
    """)

    return StatsResponse(
        total_schemes=total,
        by_category=by_category,
        by_ministry=by_ministry,
        recently_added=recently
    )


# -----------------------------------------------------------------------------
# Seed from CSV (so you can load schemes.csv without running a separate script)
# -----------------------------------------------------------------------------

# Map CSV "Category" to DB opportunity_type (must be one of schema constraint)
CATEGORY_TO_TYPE = {
    "education": "scholarship",
    "agriculture": "financial_aid",
    "employment": "skill_training",
    "commerce": "financial_aid",
    "default": "welfare_scheme",
}


def _slug_id(title: str, max_len: int = 16) -> str:
    s = re.sub(r"[^a-z0-9]", "", title.lower())[:max_len]
    return s or "scheme"


def _parse_eligibility_from_raw(text: str) -> dict:
    """
    Parse Eligibility column text into structured fields so the matcher can score.
    e.g. "Age 18 to 25 income below 5 lakh" -> {age_min, age_max, income_limit, raw}
    """
    out = {"raw": text} if text else {}
    if not text or not isinstance(text, str):
        return out
    t = text.lower().strip()
    # Age: "age 18 to 25", "age 18-25", "18 to 25 years"
    age_match = re.search(r"age\s*(\d+)\s*(?:to|-)\s*(\d+)|(\d+)\s*(?:to|-)\s*(\d+)\s*(?:years?)?", t, re.I)
    if age_match:
        g = age_match.groups()
        a1, a2 = (g[0], g[1]) if g[0] else (g[2], g[3])
        if a1 is not None and a2 is not None:
            out["age_min"] = int(a1)
            out["age_max"] = int(a2)
    # Income: "income below 5 lakh", "below 2 lakh", "income below 2 lakh"
    income_match = re.search(r"(?:income\s+)?(?:below|under|<\s*)?\s*(\d+(?:\.\d+)?)\s*lakh", t, re.I)
    if income_match:
        out["income_limit"] = int(float(income_match.group(1)) * 100000)
    # Caste: SC, ST, OBC, General
    for cat in ["sc", "st", "obc", "general"]:
        if re.search(rf"\b{re.escape(cat)}\b", t):
            out.setdefault("caste_category", []).append(cat.upper() if cat != "general" else "General")
    return out


@app.get("/api/v1/debug-eligibility")
def debug_eligibility():
    """Return first scheme's eligibility (raw + parsed) to verify matching will work."""
    results = _schemes_for_match()
    if not results:
        return {"message": "No schemes loaded. Load schemes from CSV first.", "count": 0}
    s = results[0]
    el = s.get("eligibility")
    if isinstance(el, dict):
        elig = el
    else:
        try:
            elig = json.loads(el or "{}") if el else {}
        except Exception:
            elig = {}
    raw = elig.get("raw") or ""
    parsed = _parse_eligibility_from_raw(raw) if isinstance(raw, str) else {}
    return {
        "scheme_title": s.get("title"),
        "eligibility_stored": elig,
        "after_parse": {k: v for k, v in parsed.items() if k != "raw"},
        "has_scoring_fields": any(parsed.get(k) for k in ("age_min", "age_max", "income_limit", "caste_category", "state")),
    }


@app.post("/api/v1/seed-from-csv")
def seed_from_csv():
    """
    Load schemes from schemes.csv in the project root into the opportunities table.
    Call this once when the table is empty to get data for matching.
    """
    # schemes.csv in project root (folder that contains src/)
    project_root = Path(__file__).resolve().parent.parent
    csv_path = project_root / "schemes.csv"
    if not csv_path.exists():
        csv_path = project_root.parent / "schemes.csv"
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"schemes.csv not found. Place it in project root: {project_root}")

    rows_to_insert = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            # Normalize keys (strip BOM/spaces from column names)
            row = {k.strip().lstrip("\ufeff"): v for k, v in row.items()}
            title = (row.get("Scheme_Name") or "").strip()
            if not title:
                continue
            description = (row.get("Description") or "").strip()
            ministry = (row.get("Ministry") or "").strip() or "Government of India"
            category_key = (row.get("Category") or "").strip().lower().split()[0] if row.get("Category") else ""
            opportunity_type = CATEGORY_TO_TYPE.get(category_key, CATEGORY_TO_TYPE["default"])
            eligibility_raw = (row.get("Eligibility") or "").strip()
            eligibility_dict = _parse_eligibility_from_raw(eligibility_raw)
            eligibility = json.dumps(eligibility_dict)
            url = (row.get("Official_Website") or "").strip() or f"https://example.com/scheme-{i}"
            # Ensure unique id per row (varchar 16)
            base_id = _slug_id(title)
            scheme_id = base_id if len(base_id) <= 16 else base_id[:16]
            if any(r[0] == scheme_id for r in rows_to_insert):
                scheme_id = f"{base_id[:12]}{i}"[:16]
            published = "2024-01-01 00:00:00"
            ai_summary = description[:500] if description else title
            rows_to_insert.append((
                scheme_id, "csv", url, title, description, opportunity_type,
                ministry, "Central", published, eligibility, "[]", None,
                ai_summary, url, 0.9, "pending",
            ))

    if not rows_to_insert:
        return {"message": "No rows in schemes.csv", "inserted": 0}

    if not _check_db():
        # In-memory: build dicts and add to IN_MEMORY_SCHEMES (skip duplicate source_url)
        existing_urls = {s.get("source_url") for s in IN_MEMORY_SCHEMES}
        inserted = 0
        for t in rows_to_insert:
            (scheme_id, source_id, url, title, desc, opp_type, ministry, auth_level,
             published, eligibility_json, req_docs_json, benefit_amt, ai_summary, app_url, trust, status) = t
            if url in existing_urls:
                continue
            existing_urls.add(url)
            try:
                elig = json.loads(eligibility_json) if isinstance(eligibility_json, str) else (eligibility_json or {})
            except Exception:
                elig = {}
            try:
                req_docs = json.loads(req_docs_json) if isinstance(req_docs_json, str) else (req_docs_json or [])
            except Exception:
                req_docs = []
            IN_MEMORY_SCHEMES.append({
                "id": scheme_id, "source_id": source_id, "source_url": url, "title": title,
                "description": desc, "opportunity_type": opp_type, "issuing_authority": ministry,
                "authority_level": auth_level, "published_date": published, "eligibility": elig,
                "required_documents": req_docs, "benefit_amount": benefit_amt,
                "benefit_description": None, "application_url": app_url,
                "trust_score": trust, "verification_status": status, "ai_summary": ai_summary,
            })
            inserted += 1
        return {"message": f"Loaded {inserted} schemes from schemes.csv (in-memory)", "inserted": inserted}

    sql = """
    INSERT INTO opportunities (
        id, source_id, source_url, title, description, opportunity_type,
        issuing_authority, authority_level, published_date,
        eligibility, required_documents, benefit_amount,
        ai_summary, application_url, trust_score, verification_status
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s::timestamp,
        %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s
    )
    ON CONFLICT (source_url) DO UPDATE SET
        title = EXCLUDED.title,
        description = EXCLUDED.description,
        eligibility = EXCLUDED.eligibility,
        ai_summary = EXCLUDED.ai_summary
    """
    try:
        n = execute_insert_many(sql, rows_to_insert)
        return {"message": f"Loaded {n} schemes from schemes.csv", "inserted": n}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------------------------
# Run
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)