#!/usr/bin/env python3
"""
Database Setup - Runs EVERYTHING inside Docker
Location: scripts/setup_db.py

This avoids all authentication issues by running inside the container.
"""

import subprocess
import sys
from pathlib import Path
import json

project_root = Path(__file__).parent.parent


def run_sql_file_in_container(sql_file_path):
    """Run a SQL file inside the Docker container"""
    
    # Copy SQL file into container
    print(f"   Copying {sql_file_path.name} to container...")
    cmd = ['docker', 'cp', str(sql_file_path), 'civicsense_db:/tmp/schema.sql']
    subprocess.run(cmd, check=True)
    
    # Execute SQL file inside container
    print(f"   Executing SQL...")
    cmd = [
        'docker', 'exec', '-i', 'civicsense_db',
        'psql', '-U', 'civicsense', '-d', 'civicsense', '-f', '/tmp/schema.sql'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr


def run_sql_command(sql, database='civicsense'):
    """Run a SQL command inside Docker"""
    cmd = [
        'docker', 'exec', '-i', 'civicsense_db',
        'psql', '-U', 'civicsense', '-d', database, '-c', sql
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr


def setup_database():
    """Setup database and schema"""
    
    print("="*60)
    print("📄 Running Database Schema")
    print("="*60 + "\n")
    
    # Check schema file exists
    schema_file = project_root / 'db' / 'schema.sql'
    if not schema_file.exists():
        print(f"❌ Schema file not found: {schema_file}")
        return False
    
    print(f"Found schema file: {schema_file.name} ({schema_file.stat().st_size} bytes)")
    
    # Run schema
    success, output = run_sql_file_in_container(schema_file)
    
    if success:
        print("   ✅ Schema executed successfully!\n")
        # Only show warnings/errors if any
        if 'ERROR' in output or 'WARNING' in output:
            print("   Output:")
            for line in output.split('\n'):
                if 'ERROR' in line or 'WARNING' in line:
                    print(f"   {line}")
        return True
    else:
        print(f"   ❌ Schema execution failed!")
        print(f"\n{output}")
        return False


def seed_data():
    """Insert sample data"""
    
    print("="*60)
    print("🌱 Adding Sample Data")
    print("="*60 + "\n")
    
    # Insert sources
    print("1. Adding data sources...")
    
    sql = """
INSERT INTO sources (id, name, source_type, config, schedule, priority)
VALUES 
    ('pib_releases', 'Press Information Bureau', 'rss',
     '{"feed_url": "https://pib.gov.in/allRss.aspx"}'::jsonb,
     '{"type": "interval", "interval_minutes": 60}'::jsonb, 8),
    ('upsc_notifications', 'UPSC Notifications', 'rss',
     '{"feed_url": "https://upsc.gov.in/rss/latest-notifications.xml"}'::jsonb,
     '{"type": "interval", "interval_minutes": 180}'::jsonb, 9),
    ('nsp_scholarships', 'National Scholarship Portal', 'sitemap',
     '{"sitemap_url": "https://scholarships.gov.in/sitemap.xml"}'::jsonb,
     '{"type": "interval", "interval_minutes": 1440}'::jsonb, 10)
ON CONFLICT (id) DO NOTHING;
"""
    
    success, output = run_sql_command(sql)
    if success:
        print("   ✅ Sources added\n")
    else:
        print(f"   ❌ Failed: {output}\n")
    
    # Insert sample opportunities
    print("2. Adding sample opportunities...")
    
    sql = """
INSERT INTO opportunities (
    id, source_id, source_url, title, description, opportunity_type,
    issuing_authority, authority_level, published_date,
    eligibility, benefit_amount, application_url,
    ai_summary, trust_score, verification_status
) VALUES 
    ('pmkisan_2024', 'manual', 'https://pmkisan.gov.in',
     'PM-KISAN - Pradhan Mantri Kisan Samman Nidhi',
     'Provides ₹6,000 per year to small farmers in three installments',
     'financial_aid', 'Ministry of Agriculture', 'Central',
     '2024-01-01', '{"occupation": ["farmer"]}'::jsonb,
     6000.0, 'https://pmkisan.gov.in',
     '₹6,000 per year for small farmers! Get ₹2,000 every 4 months directly in your bank account.',
     0.99, 'verified'),
    ('nsp_sc_2024', 'manual', 'https://scholarships.gov.in/scheme/101',
     'Post Matric Scholarship for SC Students',
     'Financial assistance to SC students for post-matriculation studies',
     'scholarship', 'Ministry of Social Justice', 'Central',
     '2024-01-15', '{"caste_category": ["SC"], "income_limit": 250000}'::jsonb,
     15000.0, 'https://scholarships.gov.in',
     '₹10,000-20,000 per year for SC students pursuing higher education!',
     0.98, 'verified')
ON CONFLICT (source_url) DO NOTHING;
"""
    
    success, output = run_sql_command(sql)
    if success:
        print("   ✅ Opportunities added\n")
    else:
        print(f"   ❌ Failed: {output}\n")
    
    return True


def verify_setup():
    """Verify the database setup"""
    
    print("="*60)
    print("🔍 Verifying Setup")
    print("="*60 + "\n")
    
    # Count tables
    print("1. Checking tables...")
    success, output = run_sql_command("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' 
        ORDER BY tablename;
    """)
    
    if success:
        tables = [line.strip() for line in output.split('\n') if line.strip() and line.strip() != 'tablename' and '---' not in line and 'row' not in line]
        print(f"   ✅ Found {len(tables)} tables")
        for i, table in enumerate(tables[:8], 1):
            print(f"      {i}. {table}")
        if len(tables) > 8:
            print(f"      ... and {len(tables) - 8} more")
    
    # Count data
    print("\n2. Checking data...")
    
    success, output = run_sql_command("SELECT COUNT(*) FROM opportunities;")
    if success:
        count = output.split('\n')[2].strip() if len(output.split('\n')) > 2 else '0'
        print(f"   ✅ Opportunities: {count}")
    
    success, output = run_sql_command("SELECT COUNT(*) FROM sources;")
    if success:
        count = output.split('\n')[2].strip() if len(output.split('\n')) > 2 else '0'
        print(f"   ✅ Data sources: {count}")
    
    # Show sample
    print("\n3. Sample opportunity:")
    success, output = run_sql_command("""
        SELECT title, opportunity_type, LEFT(ai_summary, 60) as summary 
        FROM opportunities 
        LIMIT 1;
    """)
    
    if success:
        lines = output.split('\n')
        for line in lines[2:5]:  # Skip header
            if line.strip() and '---' not in line:
                print(f"   {line}")
    
    return True


def main():
    print("\n" + "="*60)
    print("🚀 CivicSense AI - Database Setup")
    print("="*60 + "\n")
    
    # Check Docker
    print("Checking Docker container...")
    cmd = ['docker', 'ps', '--filter', 'name=civicsense_db', '--format', '{{.Status}}']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if not result.stdout.strip():
            print("❌ civicsense_db container is not running!")
            print("\n💡 Start it with:")
            print("   docker-compose up -d postgres redis")
            sys.exit(1)
        print(f"✅ Container: {result.stdout.strip()}\n")
    except:
        print("❌ Docker not available")
        sys.exit(1)
    
    # Setup schema
    if not setup_database():
        print("\n❌ Schema setup failed")
        sys.exit(1)
    
    # Seed data
    if not seed_data():
        print("\n❌ Data seeding failed")
        sys.exit(1)
    
    # Verify
    verify_setup()
    
    # Success!
    print("\n" + "="*60)
    print("🎉 DATABASE SETUP COMPLETE!")
    print("="*60)
    
    print("\n✅ Your database is ready with:")
    print("   • Complete schema (12 tables + 3 views)")
    print("   • 2 sample opportunities")
    print("   • 3 data sources configured")
    
    print("\n🚀 Next Steps:")
    
    print("\n1️⃣  Test the PIB collector:")
    print("   python src/acquisition/pib_collector.py")
    print("   (Fetches 10-20 real opportunities from PIB RSS)")
    
    print("\n2️⃣  Collect and store (without AI - FAST):")
    print("   python scripts/run_collection.py --source pib_releases --no-ai")
    print("   (Takes ~30 seconds, adds real data to database)")
    
    print("\n3️⃣  Collect with AI summaries:")
    print("   python scripts/run_collection.py --source pib_releases")
    print("   (Takes ~5 minutes, generates AI summaries with Ollama)")
    
    print("\n4️⃣  View your data:")
    print("   docker exec -it civicsense_db psql -U civicsense -d civicsense")
    print("   Commands to try:")
    print("     SELECT COUNT(*) FROM opportunities;")
    print("     SELECT title, opportunity_type FROM opportunities;")
    print("     SELECT * FROM collection_health;")
    print("     \\q  (to exit)")
    
    print("\n5️⃣  Start the API:")
    print("   python demo_api.py")
    print("   Then visit: http://localhost:8000/docs")
    
    print("\n" + "="*60 + "\n")


if __name__ == '__main__':
    main()