#!/usr/bin/env python3
"""
Add AI Summaries to Opportunities
Location: scripts/add_ai_summaries.py

Uses Ollama to generate summaries for opportunities without them.
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ai.summarizer_agent import SummarizerAgent
import subprocess

print("="*60)
print("🤖 Adding AI Summaries with Ollama")
print("="*60 + "\n")

# Check Ollama is running
print("1. Checking Ollama...")
try:
    import httpx
    async def check():
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:11434/api/tags", timeout=5.0)
            return response.status_code == 200
    
    if asyncio.run(check()):
        print("   ✅ Ollama is running\n")
    else:
        print("   ❌ Ollama not responding")
        sys.exit(1)
except:
    print("   ❌ Cannot connect to Ollama")
    print("   Make sure Ollama is running: ollama serve")
    sys.exit(1)

# Get opportunities from database
print("2. Fetching opportunities from database...")

get_opps = """
import psycopg2
import json

conn = psycopg2.connect(
    host="localhost",
    database="civicsense",
    user="civicsense",
    password="civicsense_dev_password"
)
cur = conn.cursor()

cur.execute('''
    SELECT id, title, description, benefit_amount, issuing_authority
    FROM opportunities
    WHERE ai_summary IS NULL OR ai_summary = ''
''')

opps = []
for row in cur.fetchall():
    opps.append({
        'id': row[0],
        'title': row[1],
        'description': row[2] or '',
        'benefit_amount': float(row[3]) if row[3] else None,
        'issuing_authority': row[4] or 'Government of India'
    })

print(json.dumps(opps))
cur.close()
conn.close()
"""

result = subprocess.run([
    'docker', 'exec', '-i', 'civicsense_db',
    'python3', '-c', get_opps
], capture_output=True, text=True)

import json
opportunities = json.loads(result.stdout)

print(f"   ✅ Found {len(opportunities)} opportunities needing summaries\n")

if not opportunities:
    print("✅ All opportunities already have AI summaries!")
    sys.exit(0)

# Generate summaries with Ollama
print("3. Generating AI summaries with Ollama...\n")

async def generate_summaries():
    agent = SummarizerAgent(model="llama3.1:8b")
    
    summaries = {}
    
    for i, opp in enumerate(opportunities, 1):
        try:
            print(f"   [{i}/{len(opportunities)}] {opp['title'][:50]}...")
            
            summary = await agent.summarize(opp)
            summaries[opp['id']] = summary
            
            print(f"       ✅ Generated: {summary[:80]}...")
            
        except Exception as e:
            print(f"       ❌ Failed: {e}")
            summaries[opp['id']] = opp['description'][:200] + "..."
    
    return summaries

summaries = asyncio.run(generate_summaries())

print(f"\n   ✅ Generated {len(summaries)} summaries\n")

# Update database
print("4. Updating database...")

for opp_id, summary in summaries.items():
    # Escape single quotes for SQL
    summary_safe = summary.replace("'", "''")
    
    update_sql = f"""
import psycopg2
conn = psycopg2.connect(
    host="localhost",
    database="civicsense",
    user="civicsense",
    password="civicsense_dev_password"
)
cur = conn.cursor()
cur.execute('''
    UPDATE opportunities
    SET ai_summary = %s
    WHERE id = %s
''', ('''{summary_safe}''', '''{opp_id}'''))
conn.commit()
cur.close()
conn.close()
"""
    
    subprocess.run([
        'docker', 'exec', '-i', 'civicsense_db',
        'python3', '-c', update_sql
    ], capture_output=True)

print("   ✅ Database updated\n")

# Show results
print("="*60)
print("📊 Results")
print("="*60 + "\n")

result = subprocess.run([
    'docker', 'exec', '-i', 'civicsense_db',
    'psql', '-U', 'civicsense', '-d', 'civicsense', '-c',
    "SELECT title, LEFT(ai_summary, 60) FROM opportunities WHERE ai_summary IS NOT NULL LIMIT 5;"
], capture_output=True, text=True)

print(result.stdout)

print("="*60)
print("✅ AI Enhancement Complete!")
print("="*60)
print("\n📋 View all summaries:")
print("   docker exec -it civicsense_db psql -U civicsense -d civicsense")
print("   SELECT title, ai_summary FROM opportunities;")
print()