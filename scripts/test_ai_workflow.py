#!/usr/bin/env python3
"""
AI Agents Workflow Test Script
Location: scripts/test_ai_workflow.py

Tests all AI agents with 5 random schemes from database.

Usage:
    python scripts/test_ai_workflow.py
    python scripts/test_ai_workflow.py --count 10  # Test 10 schemes
"""

import sys
import asyncio
import argparse
from pathlib import Path
import subprocess
import json
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ai.summarizer_agent import SummarizerAgent
from src.ai.eligibility_agent import EligibilityAgent
from src.ai.translation_agent import TranslationAgent


class WorkflowTester:
    """Test all AI agents on random schemes"""
    
    def __init__(self, num_schemes=5):
        self.num_schemes = num_schemes
        self.schemes = []
        
        # Initialize AI agents
        print("🤖 Initializing AI Agents...")
        self.summarizer = SummarizerAgent(model="llama3.1:8b")
        self.eligibility_agent = EligibilityAgent(model="qwen2.5:7b")
        self.translator = TranslationAgent(model="qwen2.5:7b")
        print("   ✅ All agents ready\n")
    
    def fetch_random_schemes(self):
        """Fetch random schemes from database"""
        print(f"📊 Fetching {self.num_schemes} random schemes from database...")
        
        query = f"""
import psycopg2
import json

conn = psycopg2.connect(
    host='localhost', database='civicsense',
    user='civicsense', password='civicsense_dev_password'
)
cur = conn.cursor()

cur.execute('''
    SELECT 
        id, title, description, opportunity_type,
        issuing_authority, eligibility, benefit_description,
        source_url
    FROM opportunities
    WHERE description IS NOT NULL 
    AND description != ''
    ORDER BY RANDOM()
    LIMIT {self.num_schemes}
''')

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
                'python3', '-c', query
            ], capture_output=True, text=True, timeout=30, check=True)
            
            self.schemes = json.loads(result.stdout)
            print(f"   ✅ Fetched {len(self.schemes)} schemes\n")
            
        except Exception as e:
            print(f"   ❌ Error fetching schemes: {e}")
            sys.exit(1)
    
    async def test_summarizer(self, scheme, index):
        """Test summarization agent"""
        print(f"\n{'='*70}")
        print(f"📝 TEST {index}: Summarization Agent")
        print(f"{'='*70}")
        print(f"Scheme: {scheme['title']}")
        print(f"Type: {scheme['opportunity_type']}")
        print(f"Ministry: {scheme['issuing_authority']}\n")
        
        print("Original Description (first 200 chars):")
        print(f"  {scheme['description'][:200]}...\n")
        
        try:
            print("🔄 Generating AI summary...")
            start_time = datetime.now()
            
            summary = await self.summarizer.summarize(scheme)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            print(f"✅ Summary generated in {duration:.2f}s\n")
            print("AI Summary:")
            print(f"  {summary}\n")
            
            # Metrics
            print("📊 Metrics:")
            print(f"  Original length: {len(scheme['description'])} chars")
            print(f"  Summary length: {len(summary)} chars")
            print(f"  Compression: {len(summary)/len(scheme['description'])*100:.1f}%")
            print(f"  Reading level: 8th grade")
            
            return {
                'success': True,
                'summary': summary,
                'duration': duration,
                'compression': len(summary)/len(scheme['description'])
            }
            
        except Exception as e:
            print(f"❌ Summarization failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def test_eligibility_parser(self, scheme, index):
        """Test eligibility parsing agent"""
        print(f"\n{'='*70}")
        print(f"🎯 TEST {index}: Eligibility Parser Agent")
        print(f"{'='*70}")
        print(f"Scheme: {scheme['title']}\n")
        
        # Parse current eligibility
        try:
            current_eligibility = json.loads(scheme.get('eligibility', '{}'))
        except:
            current_eligibility = {}
        
        print("Current Eligibility Data:")
        if current_eligibility:
            for key, value in current_eligibility.items():
                print(f"  {key}: {value}")
        else:
            print("  (None)")
        
        print()
        
        try:
            print("🔄 Parsing eligibility with AI...")
            start_time = datetime.now()
            
            # Create opportunity dict for agent
            opportunity = {
                'title': scheme['title'],
                'description': scheme['description'],
                'eligibility': current_eligibility,
                'benefit_description': scheme.get('benefit_description', '')
            }
            
            parsed = await self.eligibility_agent.explain(opportunity)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            print(f"✅ Eligibility parsed in {duration:.2f}s\n")
            print("AI Parsed Eligibility:")
            print(json.dumps(parsed, indent=2))
            
            return {
                'success': True,
                'parsed': parsed,
                'duration': duration
            }
            
        except Exception as e:
            print(f"❌ Eligibility parsing failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def test_translator(self, scheme, summary, index):
        """Test translation agent"""
        print(f"\n{'='*70}")
        print(f"🌍 TEST {index}: Translation Agent")
        print(f"{'='*70}")
        print(f"Scheme: {scheme['title']}\n")
        
        # Languages to test
        languages = [
            ('hi', 'Hindi'),
            ('bn', 'Bengali'),
            ('ta', 'Tamil'),
        ]
        
        translations = {}
        
        for lang_code, lang_name in languages:
            try:
                print(f"🔄 Translating to {lang_name}...")
                start_time = datetime.now()
                
                translation = await self.translator.translate(summary, lang_code)
                
                duration = (datetime.now() - start_time).total_seconds()
                
                print(f"✅ Translated in {duration:.2f}s")
                print(f"   Original: {summary[:80]}...")
                print(f"   {lang_name}: {translation[:80]}...\n")
                
                translations[lang_code] = {
                    'language': lang_name,
                    'translation': translation,
                    'duration': duration
                }
                
            except Exception as e:
                print(f"❌ Translation to {lang_name} failed: {e}\n")
                translations[lang_code] = {
                    'language': lang_name,
                    'error': str(e)
                }
        
        return {
            'success': len(translations) > 0,
            'translations': translations
        }
    
    async def run_complete_workflow(self):
        """Run complete workflow on all schemes"""
        print("\n" + "="*70)
        print("🚀 COMPLETE AI WORKFLOW TEST")
        print("="*70)
        print(f"Testing {len(self.schemes)} schemes")
        print(f"Agents: Summarizer, Eligibility Parser, Translator")
        print("="*70 + "\n")
        
        results = []
        
        for i, scheme in enumerate(self.schemes, 1):
            print(f"\n{'#'*70}")
            print(f"# SCHEME {i}/{len(self.schemes)}: {scheme['title'][:50]}")
            print(f"{'#'*70}")
            
            scheme_result = {
                'scheme_id': scheme['id'],
                'scheme_title': scheme['title'],
                'tests': {}
            }
            
            # Test 1: Summarization
            summary_result = await self.test_summarizer(scheme, i)
            scheme_result['tests']['summarizer'] = summary_result
            
            # Test 2: Eligibility Parsing
            eligibility_result = await self.test_eligibility_parser(scheme, i)
            scheme_result['tests']['eligibility'] = eligibility_result
            
            # Test 3: Translation (if summary succeeded)
            if summary_result['success']:
                translation_result = await self.test_translator(
                    scheme, 
                    summary_result['summary'], 
                    i
                )
                scheme_result['tests']['translator'] = translation_result
            
            results.append(scheme_result)
            
            # Small delay between schemes
            if i < len(self.schemes):
                print("\n⏳ Waiting 2 seconds before next scheme...")
                await asyncio.sleep(2)
        
        return results
    
    def print_summary(self, results):
        """Print summary of all tests"""
        print("\n\n" + "="*70)
        print("📊 WORKFLOW TEST SUMMARY")
        print("="*70 + "\n")
        
        # Overall stats
        total_tests = len(results) * 3  # 3 agents per scheme
        successful_tests = 0
        total_duration = 0
        
        for result in results:
            for test_name, test_result in result['tests'].items():
                if test_result.get('success'):
                    successful_tests += 1
                    if 'duration' in test_result:
                        total_duration += test_result['duration']
        
        print(f"Total Schemes Tested:     {len(results)}")
        print(f"Total Tests Run:          {total_tests}")
        print(f"Successful Tests:         {successful_tests}")
        print(f"Failed Tests:             {total_tests - successful_tests}")
        print(f"Success Rate:             {successful_tests/total_tests*100:.1f}%")
        print(f"Total Processing Time:    {total_duration:.2f}s")
        print(f"Average Time per Test:    {total_duration/successful_tests:.2f}s")
        
        print("\n" + "-"*70)
        print("Individual Scheme Results:")
        print("-"*70 + "\n")
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['scheme_title'][:60]}")
            print(f"   ID: {result['scheme_id']}")
            
            # Summarizer
            if result['tests']['summarizer']['success']:
                duration = result['tests']['summarizer']['duration']
                compression = result['tests']['summarizer']['compression']
                print(f"   ✅ Summarizer: {duration:.2f}s (compression: {compression*100:.1f}%)")
            else:
                print(f"   ❌ Summarizer: Failed")
            
            # Eligibility
            if result['tests']['eligibility']['success']:
                duration = result['tests']['eligibility']['duration']
                print(f"   ✅ Eligibility: {duration:.2f}s")
            else:
                print(f"   ❌ Eligibility: Failed")
            
            # Translator
            if 'translator' in result['tests']:
                trans = result['tests']['translator']
                if trans['success']:
                    lang_count = len(trans['translations'])
                    print(f"   ✅ Translator: {lang_count} languages")
                else:
                    print(f"   ❌ Translator: Failed")
            
            print()
        
        print("="*70)
        print("✅ WORKFLOW TEST COMPLETE!")
        print("="*70 + "\n")
        
        # Recommendations
        print("💡 Recommendations:")
        
        if successful_tests == total_tests:
            print("   ✅ All agents working perfectly!")
            print("   ✅ Ready for production use")
        elif successful_tests / total_tests >= 0.8:
            print("   ⚠️  Most agents working well")
            print("   📝 Review failed tests and retry")
        else:
            print("   ❌ Multiple agent failures detected")
            print("   🔧 Check Ollama installation")
            print("   🔧 Check model availability: ollama list")
            print("   🔧 Review error messages above")
        
        print()


async def main():
    parser = argparse.ArgumentParser(
        description='Test AI workflow on random schemes'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=5,
        help='Number of schemes to test (default: 5)'
    )
    
    args = parser.parse_args()
    
    # Check Ollama is running
    print("🔍 Checking Ollama status...")
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:11434/api/tags", timeout=5.0)
            if response.status_code == 200:
                models = response.json().get('models', [])
                print(f"   ✅ Ollama running with {len(models)} models")
                for model in models[:3]:
                    print(f"      • {model['name']}")
            else:
                print("   ❌ Ollama not responding")
                sys.exit(1)
    except Exception as e:
        print(f"   ❌ Cannot connect to Ollama: {e}")
        print("\n💡 Start Ollama with: ollama serve")
        sys.exit(1)
    
    print()
    
    # Run workflow test
    tester = WorkflowTester(num_schemes=args.count)
    tester.fetch_random_schemes()
    
    results = await tester.run_complete_workflow()
    
    tester.print_summary(results)


if __name__ == '__main__':
    asyncio.run(main())