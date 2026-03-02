#!/usr/bin/env python3
"""
Seed the opportunities table with sample schemes.
Uses the same DB config as the API (src/api/main.py) so it works with local Postgres or Docker.

Run from project root (use the same env as the API so psycopg2 is available):
  python scripts/seed_opportunities.py
  # or:  .venv\\Scripts\\python scripts/seed_opportunities.py

If the table doesn't exist, create it first: psql -U civicsense -d civicsense -f db/schema.sql
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Reuse API config (supports .env override)
try:
    from dotenv import load_dotenv
    load_dotenv(project_root / ".env")
except ImportError:
    pass

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "database": os.environ.get("DB_NAME", "civicsense"),
    "user": os.environ.get("DB_USER", "civicsense"),
    "password": os.environ.get("DB_PASSWORD", "civicsense_dev_password"),
}


def get_conn():
    import psycopg2
    return psycopg2.connect(**DB_CONFIG)


def table_exists(cur):
    cur.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'opportunities'
    """)
    return cur.fetchone() is not None


def seed():
    conn = get_conn()
    cur = conn.cursor()

    if not table_exists(cur):
        raise RuntimeError(
            "Table 'opportunities' does not exist. Create it first with:\n"
            "  psql -U civicsense -d civicsense -f db/schema.sql\n"
            "Or, if using Docker: docker exec -i civicsense_db psql -U civicsense -d civicsense -f /tmp/schema.sql"
        )

    # Sample schemes with eligibility the /match API can score (age, income, caste, state)
    rows = [
        (
            "pmkisan_01",
            "manual",
            "https://pmkisan.gov.in",
            "PM-KISAN - Pradhan Mantri Kisan Samman Nidhi",
            "₹6,000 per year to small and marginal farmers in three equal installments.",
            "financial_aid",
            "Ministry of Agriculture",
            "Central",
            "2024-01-01 00:00:00",
            '{"age_min": 18, "age_max": 100, "income_limit": 100000, "state": ["Maharashtra", "Uttar Pradesh", "Bihar", "West Bengal"]}',
            "[]",
            6000.0,
            "₹6,000 per year for small farmers. ₹2,000 every 4 months in your bank account.",
            "https://pmkisan.gov.in",
            0.95,
            "verified",
        ),
        (
            "nsp_sc_01",
            "manual",
            "https://scholarships.gov.in/sc",
            "Post Matric Scholarship for SC Students",
            "Financial assistance to SC students for post-matriculation studies.",
            "scholarship",
            "Ministry of Social Justice",
            "Central",
            "2024-01-15 00:00:00",
            '{"age_min": 16, "age_max": 35, "income_limit": 250000, "caste_category": ["SC"]}',
            "[]",
            15000.0,
            "₹10,000–20,000 per year for SC students in higher education.",
            "https://scholarships.gov.in",
            0.98,
            "verified",
        ),
        (
            "nsp_obc_01",
            "manual",
            "https://scholarships.gov.in/obc",
            "Post Matric Scholarship for OBC Students",
            "Financial assistance to OBC students for post-matriculation studies.",
            "scholarship",
            "Ministry of Social Justice",
            "Central",
            "2024-02-01 00:00:00",
            '{"age_min": 16, "age_max": 35, "income_limit": 100000, "caste_category": ["OBC"]}',
            "[]",
            12000.0,
            "Scholarship for OBC students pursuing higher education.",
            "https://scholarships.gov.in",
            0.97,
            "verified",
        ),
        (
            "pmuy_01",
            "manual",
            "https://pmuy.gov.in",
            "PM Ujjwala Yojana - Free LPG Connection",
            "Free LPG connection to women from BPL households.",
            "subsidy",
            "Ministry of Petroleum",
            "Central",
            "2024-01-10 00:00:00",
            '{"age_min": 18, "income_limit": 100000, "state": ["Maharashtra", "Uttar Pradesh", "Rajasthan"]}',
            "[]",
            None,
            "Free LPG connection and first refill subsidy for eligible women.",
            "https://pmuy.gov.in",
            0.96,
            "verified",
        ),
        (
            "skill_india_01",
            "manual",
            "https://skillindia.gov.in",
            "Skill India - Short Term Training",
            "Short-term skill training for youth with placement support.",
            "skill_training",
            "Ministry of Skill Development",
            "Central",
            "2024-03-01 00:00:00",
            '{"age_min": 18, "age_max": 45}',
            "[]",
            None,
            "Free skill training and certification. Age 18–45.",
            "https://skillindia.gov.in",
            0.92,
            "verified",
        ),
    ]

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
        ai_summary = EXCLUDED.ai_summary,
        trust_score = EXCLUDED.trust_score
    """
    try:
        for row in rows:
            cur.execute(sql, row)
        conn.commit()
        print(f"✅ Inserted/updated {len(rows)} sample opportunities.")
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    print("Seeding opportunities table (same DB as API)...")
    try:
        seed()
        print("Done. Restart the API if it was running, then use Match schemes in the app.")
    except Exception as e:
        print(f"Failed: {e}")
        sys.exit(1)
