# File: src/api/main.py
"""
CivicSense AI - FastAPI Backend
Complete REST API for government schemes
"""

from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import subprocess
import json

app = FastAPI(
    title="CivicSense AI API",
    description="Discover government schemes personalized for you",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS - Allow frontend to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specify frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Pydantic Models (Request/Response schemas)
# ============================================================================

class UserProfile(BaseModel):
    """User profile for personalized matching"""
    age: Optional[int] = Field(None, ge=1, le=100, description="Age in years")
    state: Optional[str] = Field(None, description="State of residence")
    district: Optional[str] = Field(None, description="District")
    education_level: Optional[str] = Field(None, description="Highest education: below_10th, 10th, 12th, graduate, postgraduate")
    annual_income: Optional[int] = Field(None, ge=0, description="Annual family income in INR")
    caste_category: Optional[str] = Field(None, description="General, SC, ST, OBC")
    occupation: Optional[str] = Field(None, description="student, farmer, employed, unemployed, self_employed")
    gender: Optional[str] = Field(None, description="male, female, other")
    is_disabled: Optional[bool] = Field(False, description="Person with disability")
    is_bpl: Optional[bool] = Field(False, description="Below Poverty Line")


class SchemeBasic(BaseModel):
    """Basic scheme information"""
    id: str
    title: str
    opportunity_type: str
    issuing_authority: str
    ai_summary: Optional[str] = None
    match_score: Optional[float] = None


class SchemeDetail(SchemeBasic):
    """Detailed scheme information"""
    description: str
    source_url: str
    eligibility: Dict[str, Any]
    benefit_description: Optional[str] = None
    required_documents: List[str] = []
    application_url: Optional[str] = None
    published_date: str
    trust_score: float
    verification_status: str


class SearchResponse(BaseModel):
    """Search results"""
    total: int
    page: int
    page_size: int
    results: List[SchemeBasic]
    facets: Optional[Dict[str, Dict[str, int]]] = None


class MatchResponse(BaseModel):
    """Matching results"""
    total_matches: int
    top_matches: List[SchemeDetail]
    recommendations: List[SchemeDetail]


class StatsResponse(BaseModel):
    """Statistics"""
    total_schemes: int
    by_category: Dict[str, int]
    by_ministry: Dict[str, int]
    recently_added: int


# ============================================================================
# Database Helper Functions
# ============================================================================

def execute_query(query: str) -> List[Dict]:
    """Execute SQL query via Docker and return results as list of dicts"""
    
    python_code = f"""
import psycopg2
import json
conn = psycopg2.connect(
    host='localhost', database='civicsense',
    user='civicsense', password='civicsense_dev_password'
)
cur = conn.cursor()
cur.execute('''{query}''')
columns = [desc[0] for desc in cur.description]
results = []
for row in cur.fetchall():
    results.append(dict(zip(columns, row)))
print(json.dumps(results, default=str))
cur.close()
conn.close()
"""
    
    try:
        result = subprocess.run([
            'docker', 'exec', '-i', 'civicsense_db',
            'python3', '-c', python_code
        ], capture_output=True, text=True, timeout=30, check=True)
        
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Query error: {e}")
        return []


def execute_count(query: str) -> int:
    """Execute COUNT query"""
    results = execute_query(query)
    if results and 'count' in results[0]:
        return results[0]['count']
    return 0


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
def root():
    """API root"""
    return {
        "message": "CivicSense AI API",
        "version": "1.0.0",
        "docs": "/api/docs"
    }


@app.get("/api/v1/health")
def health_check():
    """Health check endpoint"""
    try:
        count = execute_count("SELECT COUNT(*) FROM opportunities")
        return {
            "status": "healthy",
            "database": "connected",
            "total_schemes": count
        }
    except:
        return {
            "status": "unhealthy",
            "database": "disconnected"
        }


@app.get("/api/v1/schemes", response_model=SearchResponse)
def list_schemes(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by opportunity_type"),
    ministry: Optional[str] = Query(None, description="Filter by ministry"),
    state: Optional[str] = Query(None, description="Filter by state"),
    q: Optional[str] = Query(None, description="Search query")
):
    """
    List all schemes with pagination and filters
    
    - **page**: Page number (starts from 1)
    - **page_size**: Number of results per page
    - **category**: Filter by type (scholarship, welfare_scheme, etc.)
    - **ministry**: Filter by issuing ministry
    - **state**: Filter by applicable state
    - **q**: Search in title and description
    """
    
    # Build query
    where_clauses = []
    
    if category:
        where_clauses.append(f"opportunity_type = '{category}'")
    
    if ministry:
        where_clauses.append(f"issuing_authority ILIKE '%{ministry}%'")
    
    if state:
        where_clauses.append(f"eligibility::text ILIKE '%{state}%'")
    
    if q:
        where_clauses.append(f"(title ILIKE '%{q}%' OR description ILIKE '%{q}%')")
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Get total count
    count_query = f"SELECT COUNT(*) FROM opportunities WHERE {where_sql}"
    total = execute_count(count_query)
    
    # Get paginated results
    offset = (page - 1) * page_size
    query = f"""
        SELECT id, title, opportunity_type, issuing_authority, ai_summary
        FROM opportunities
        WHERE {where_sql}
        ORDER BY published_date DESC
        LIMIT {page_size} OFFSET {offset}
    """
    
    results = execute_query(query)
    
    # Get facets (counts by category and ministry)
    facets_query = f"""
        SELECT 
            opportunity_type,
            issuing_authority,
            COUNT(*) as cnt
        FROM opportunities
        WHERE {where_sql}
        GROUP BY opportunity_type, issuing_authority
    """
    
    facets_raw = execute_query(facets_query)
    
    # Process facets
    facets = {
        "categories": {},
        "ministries": {}
    }
    
    for row in facets_raw:
        cat = row.get('opportunity_type', 'unknown')
        ministry = row.get('issuing_authority', 'unknown')
        count = row.get('cnt', 0)
        
        facets["categories"][cat] = facets["categories"].get(cat, 0) + count
        facets["ministries"][ministry] = facets["ministries"].get(ministry, 0) + count
    
    return SearchResponse(
        total=total,
        page=page,
        page_size=page_size,
        results=results,
        facets=facets
    )


@app.get("/api/v1/schemes/{scheme_id}", response_model=SchemeDetail)
def get_scheme(scheme_id: str):
    """
    Get detailed information about a specific scheme
    
    - **scheme_id**: Unique scheme identifier
    """
    
    query = f"""
        SELECT 
            id, title, description, source_url, opportunity_type,
            issuing_authority, eligibility, benefit_description,
            required_documents, application_url, published_date,
            trust_score, verification_status, ai_summary
        FROM opportunities
        WHERE id = '{scheme_id}'
    """
    
    results = execute_query(query)
    
    if not results:
        raise HTTPException(status_code=404, detail="Scheme not found")
    
    scheme = results[0]
    
    # Parse JSON fields
    try:
        scheme['eligibility'] = json.loads(scheme.get('eligibility', '{}'))
    except:
        scheme['eligibility'] = {}
    
    try:
        scheme['required_documents'] = json.loads(scheme.get('required_documents', '[]'))
    except:
        scheme['required_documents'] = []
    
    return scheme


@app.get("/api/v1/schemes/search", response_model=SearchResponse)
def search_schemes(
    q: str = Query(..., min_length=2, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """
    Full-text search across schemes
    
    - **q**: Search query (searches in title, description, benefits)
    """
    
    # Use PostgreSQL full-text search
    where = f"(title ILIKE '%{q}%' OR description ILIKE '%{q}%' OR benefit_description ILIKE '%{q}%')"
    
    total = execute_count(f"SELECT COUNT(*) FROM opportunities WHERE {where}")
    
    offset = (page - 1) * page_size
    query = f"""
        SELECT id, title, opportunity_type, issuing_authority, ai_summary
        FROM opportunities
        WHERE {where}
        ORDER BY published_date DESC
        LIMIT {page_size} OFFSET {offset}
    """
    
    results = execute_query(query)
    
    return SearchResponse(
        total=total,
        page=page,
        page_size=page_size,
        results=results
    )


@app.post("/api/v1/match", response_model=MatchResponse)
def match_schemes(profile: UserProfile):
    """
    Find schemes matching user profile
    
    Provides personalized scheme recommendations based on:
    - Age, income, education, caste category
    - State, occupation, gender
    - Disability status, BPL status
    """
    
    # Build eligibility conditions
    conditions = ["1=1"]  # Always true
    
    # Age filter
    if profile.age:
        conditions.append(f"""(
            (eligibility::jsonb->>'age_min')::int <= {profile.age} 
            OR eligibility::jsonb->>'age_min' IS NULL
        )""")
        conditions.append(f"""(
            (eligibility::jsonb->>'age_max')::int >= {profile.age}
            OR eligibility::jsonb->>'age_max' IS NULL
        )""")
    
    # Income filter
    if profile.annual_income:
        conditions.append(f"""(
            (eligibility::jsonb->>'income_limit')::int >= {profile.annual_income}
            OR eligibility::jsonb->>'income_limit' IS NULL
        )""")
    
    # Category filter
    if profile.caste_category:
        conditions.append(f"""(
            eligibility::jsonb->'caste_category' @> '["{profile.caste_category}"]'::jsonb
            OR eligibility::jsonb->'caste_category' IS NULL
        )""")
    
    # State filter
    if profile.state:
        conditions.append(f"""(
            eligibility::jsonb->'state' @> '["{profile.state}"]'::jsonb
            OR eligibility::jsonb->'state' IS NULL
            OR eligibility::text ILIKE '%all india%'
        )""")
    
    where_sql = " AND ".join(conditions)
    
    # Get matching schemes
    query = f"""
        SELECT 
            id, title, description, source_url, opportunity_type,
            issuing_authority, eligibility, benefit_description,
            required_documents, application_url, published_date,
            trust_score, verification_status, ai_summary
        FROM opportunities
        WHERE {where_sql}
        ORDER BY trust_score DESC, published_date DESC
        LIMIT 50
    """
    
    results = execute_query(query)
    
    # Calculate match scores
    matches = []
    for scheme in results:
        # Parse JSON
        try:
            scheme['eligibility'] = json.loads(scheme.get('eligibility', '{}'))
        except:
            scheme['eligibility'] = {}
        
        try:
            scheme['required_documents'] = json.loads(scheme.get('required_documents', '[]'))
        except:
            scheme['required_documents'] = []
        
        # Calculate match score (0-1)
        score = calculate_match_score(profile, scheme)
        scheme['match_score'] = score
        
        matches.append(scheme)
    
    # Sort by match score
    matches.sort(key=lambda x: x.get('match_score', 0), reverse=True)
    
    # Top matches (score > 0.7)
    top_matches = [m for m in matches if m.get('match_score', 0) > 0.7][:10]
    
    # Recommendations (score 0.5-0.7)
    recommendations = [m for m in matches if 0.5 <= m.get('match_score', 0) <= 0.7][:10]
    
    return MatchResponse(
        total_matches=len(matches),
        top_matches=top_matches,
        recommendations=recommendations
    )


def calculate_match_score(profile: UserProfile, scheme: Dict) -> float:
    """Calculate how well a scheme matches user profile"""
    
    score = 0.0
    max_score = 0.0
    
    eligibility = scheme.get('eligibility', {})
    
    # Age match (20 points)
    if eligibility.get('age_min') or eligibility.get('age_max'):
        max_score += 20
        if profile.age:
            age_min = eligibility.get('age_min', 0)
            age_max = eligibility.get('age_max', 100)
            if age_min <= profile.age <= age_max:
                score += 20
    
    # Income match (20 points)
    if eligibility.get('income_limit'):
        max_score += 20
        if profile.annual_income:
            if profile.annual_income <= eligibility.get('income_limit', float('inf')):
                score += 20
    
    # Category match (15 points)
    if eligibility.get('caste_category'):
        max_score += 15
        if profile.caste_category in eligibility.get('caste_category', []):
            score += 15
    
    # State match (10 points)
    if eligibility.get('state'):
        max_score += 10
        if profile.state in eligibility.get('state', []):
            score += 10
    
    # Occupation match (10 points)
    if 'occupation' in str(scheme.get('description', '')).lower():
        max_score += 10
        if profile.occupation and profile.occupation in str(scheme.get('description', '')).lower():
            score += 10
    
    # Gender match (5 points)
    if 'women' in str(scheme.get('title', '')).lower() or 'girl' in str(scheme.get('title', '')).lower():
        max_score += 5
        if profile.gender == 'female':
            score += 5
    
    # Disability match (10 points)
    if 'disability' in str(scheme.get('title', '')).lower():
        max_score += 10
        if profile.is_disabled:
            score += 10
    
    # BPL match (10 points)
    if 'bpl' in str(scheme.get('description', '')).lower() or 'poverty' in str(scheme.get('description', '')).lower():
        max_score += 10
        if profile.is_bpl:
            score += 10
    
    # Normalize to 0-1
    if max_score > 0:
        return round(score / max_score, 2)
    else:
        return 0.5  # Neutral if no specific criteria


@app.get("/api/v1/categories")
def get_categories():
    """Get all available scheme categories"""
    
    query = """
        SELECT opportunity_type, COUNT(*) as count
        FROM opportunities
        GROUP BY opportunity_type
        ORDER BY count DESC
    """
    
    results = execute_query(query)
    
    return {
        "categories": [
            {
                "id": row['opportunity_type'],
                "name": row['opportunity_type'].replace('_', ' ').title(),
                "count": row['count']
            }
            for row in results
        ]
    }


@app.get("/api/v1/ministries")
def get_ministries():
    """Get all issuing ministries"""
    
    query = """
        SELECT issuing_authority, COUNT(*) as count
        FROM opportunities
        GROUP BY issuing_authority
        ORDER BY count DESC
        LIMIT 50
    """
    
    results = execute_query(query)
    
    return {
        "ministries": [
            {
                "name": row['issuing_authority'],
                "count": row['count']
            }
            for row in results
        ]
    }


@app.get("/api/v1/stats", response_model=StatsResponse)
def get_stats():
    """Get overall statistics"""
    
    total = execute_count("SELECT COUNT(*) FROM opportunities")
    
    by_category = {}
    cat_results = execute_query("""
        SELECT opportunity_type, COUNT(*) as count
        FROM opportunities
        GROUP BY opportunity_type
    """)
    for row in cat_results:
        by_category[row['opportunity_type']] = row['count']
    
    by_ministry = {}
    min_results = execute_query("""
        SELECT issuing_authority, COUNT(*) as count
        FROM opportunities
        GROUP BY issuing_authority
        ORDER BY count DESC
        LIMIT 10
    """)
    for row in min_results:
        by_ministry[row['issuing_authority']] = row['count']
    
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


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting CivicSense AI API...")
    print("📖 Docs: http://localhost:8000/api/docs")
    print("🔍 API: http://localhost:8000/api/v1/schemes")
    uvicorn.run(app, host="0.0.0.0", port=8000)