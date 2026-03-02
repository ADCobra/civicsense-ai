#!/usr/bin/env python3
"""
Create the opportunities table using the same DB as the API.
No psql or Docker needed — run with:  python scripts/run_schema.py

From project root:  python scripts/run_schema.py
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

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

# Minimal schema: only the opportunities table (what the API and CSV seed need)
OPPORTUNITIES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS opportunities (
    id VARCHAR(16) PRIMARY KEY,
    source_id VARCHAR(100) NOT NULL,
    source_url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    opportunity_type VARCHAR(50) NOT NULL,
    issuing_authority VARCHAR(200),
    authority_level VARCHAR(20),
    scheme_code VARCHAR(100),
    published_date TIMESTAMP NOT NULL,
    application_start TIMESTAMP,
    application_end TIMESTAMP,
    last_updated TIMESTAMP DEFAULT NOW(),
    eligibility JSONB NOT NULL DEFAULT '{}',
    benefit_amount DECIMAL(15,2),
    benefit_description TEXT,
    application_url TEXT,
    required_documents JSONB DEFAULT '[]',
    application_mode VARCHAR(20) DEFAULT 'online',
    ai_summary TEXT,
    ai_eligibility_explanation JSONB,
    common_mistakes JSONB DEFAULT '[]',
    trust_score DECIMAL(3,2) CHECK (trust_score BETWEEN 0 AND 1),
    verification_status VARCHAR(20) DEFAULT 'pending',
    ai_quality_score DECIMAL(3,2),
    translations JSONB DEFAULT '{}',
    view_count INTEGER DEFAULT 0,
    application_count INTEGER DEFAULT 0,
    save_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT valid_verification_status CHECK (
        verification_status IN ('pending', 'verified', 'flagged', 'rejected')
    ),
    CONSTRAINT valid_opportunity_type CHECK (
        opportunity_type IN (
            'scholarship', 'welfare_scheme', 'competitive_exam',
            'job_notification', 'skill_training', 'financial_aid',
            'subsidy', 'pension', 'certificate'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_opp_type ON opportunities(opportunity_type);
CREATE INDEX IF NOT EXISTS idx_opp_published ON opportunities(published_date DESC);
CREATE INDEX IF NOT EXISTS idx_opp_status ON opportunities(verification_status);
CREATE INDEX IF NOT EXISTS idx_opp_source ON opportunities(source_id);
"""


def main():
    print("Connecting to database (same as API)...")
    print(f"  host={DB_CONFIG['host']}, database={DB_CONFIG['database']}, user={DB_CONFIG['user']}")
    try:
        import psycopg2
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()
        for stmt in OPPORTUNITIES_TABLE_SQL.split(";"):
            stmt = stmt.strip()
            if not stmt:
                continue
            cur.execute(stmt)
        cur.close()
        conn.close()
        print("Done. Table 'opportunities' is ready.")
        print("Next: start the API and in the app click 'Load schemes from CSV'.")
    except Exception as e:
        print(f"Error: {e}")
        if "does not exist" in str(e).lower() or "connection" in str(e).lower():
            print("\nMake sure PostgreSQL is running and the database exists.")
            print("To create database and user (run in PowerShell as admin or use pgAdmin):")
            print('  psql -U postgres -c "CREATE USER civicsense WITH PASSWORD \'civicsense_dev_password\';"')
            print('  psql -U postgres -c "CREATE DATABASE civicsense OWNER civicsense;"')
        sys.exit(1)


if __name__ == "__main__":
    main()
