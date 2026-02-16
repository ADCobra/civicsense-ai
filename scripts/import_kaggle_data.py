#!/usr/bin/env python3
"""
Import Kaggle Government Schemes Dataset
Location: scripts/import_kaggle_data.py

Imports the Kaggle CSV into PostgreSQL database.

Usage:
    python scripts/import_kaggle_data.py data/kaggle_schemes.csv
    python scripts/import_kaggle_data.py data/kaggle_schemes.csv --with-ai
"""

import sys
import csv
import json
import hashlib
from pathlib import Path
from datetime import datetime
import subprocess
import argparse

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class KaggleImporter:
    """Import Kaggle government schemes dataset"""
    
    def __init__(self, csv_path):
        self.csv_path = Path(csv_path)
        self.schemes = []
        self.stats = {
            'total': 0,
            'imported': 0,
            'skipped': 0,
            'errors': 0
        }
        
    def read_csv(self):
        """Read and parse CSV file"""
        print(f"📄 Reading CSV: {self.csv_path}")
        
        if not self.csv_path.exists():
            print(f"❌ File not found: {self.csv_path}")
            return False
        
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Show columns found
            print(f"\n📊 CSV Columns:")
            for i, col in enumerate(reader.fieldnames, 1):
                print(f"   {i}. {col}")
            print()
            
            for row in reader:
                self.schemes.append(row)
                self.stats['total'] += 1
        
        print(f"✅ Read {self.stats['total']} schemes from CSV\n")
        return True
    
    def map_to_schema(self, row):
        """
        Map CSV row to database schema
        
        Handles different possible column names from Kaggle
        """
        # Flexible column name mapping
        def get_value(row, *possible_keys):
            for key in possible_keys:
                if key in row and row[key]:
                    return row[key].strip()
            return None
        
        # Extract data with fallbacks
        title = get_value(row, 'Scheme_Name', 'scheme_name', 'Scheme Name', 'name', 'Name')
        description = get_value(row, 'Description', 'description', 'Details', 'About')
        ministry = get_value(row, 'Ministry', 'ministry', 'Department', 'Issuing_Authority')
        category = get_value(row, 'Category', 'category', 'Type', 'Scheme_Type')
        benefits = get_value(row, 'Benefits', 'benefits', 'Benefit', 'Financial_Benefit')
        eligibility = get_value(row, 'Eligibility', 'eligibility', 'Eligible', 'Who_Can_Apply')
        website = get_value(row, 'Official_Website', 'website', 'URL', 'Link', 'Source_URL')
        documents = get_value(row, 'Documents_Required', 'documents', 'Required_Documents')
        application = get_value(row, 'Application_Process', 'application', 'How_to_Apply')
        state = get_value(row, 'State', 'state', 'Applicable_State', 'Region')
        launch_year = get_value(row, 'Launch_Year', 'Year', 'Start_Year', 'Launched')
        
        if not title:
            return None
        
        # Generate unique ID
        url_for_id = website or title
        scheme_id = hashlib.md5(url_for_id.encode()).hexdigest()[:16]
        
        # Map category to our opportunity_type
        type_mapping = {
            'education': 'scholarship',
            'scholarship': 'scholarship',
            'agriculture': 'financial_aid',
            'farming': 'financial_aid',
            'health': 'welfare_scheme',
            'housing': 'welfare_scheme',
            'employment': 'welfare_scheme',
            'skill': 'skill_training',
            'training': 'skill_training',
            'pension': 'pension',
            'exam': 'competitive_exam',
            'recruitment': 'competitive_exam',
        }
        
        opportunity_type = 'welfare_scheme'  # default
        if category:
            cat_lower = category.lower()
            for key, value in type_mapping.items():
                if key in cat_lower:
                    opportunity_type = value
                    break
        
        # Parse eligibility into structured JSON
        eligibility_json = {}
        if eligibility:
            # Try to extract structured data
            elig_lower = eligibility.lower()
            
            # Age
            if 'age' in elig_lower:
                import re
                age_match = re.search(r'(\d+)\s*(?:to|-)\s*(\d+)', eligibility)
                if age_match:
                    eligibility_json['age_min'] = int(age_match.group(1))
                    eligibility_json['age_max'] = int(age_match.group(2))
            
            # Income
            if 'income' in elig_lower or 'lakh' in elig_lower:
                import re
                income_match = re.search(r'(\d+)\s*lakh', eligibility, re.IGNORECASE)
                if income_match:
                    eligibility_json['income_limit'] = int(income_match.group(1)) * 100000
            
            # Category
            if any(cat in elig_lower for cat in ['sc', 'st', 'obc']):
                categories = []
                if 'sc' in elig_lower:
                    categories.append('SC')
                if 'st' in elig_lower:
                    categories.append('ST')
                if 'obc' in elig_lower:
                    categories.append('OBC')
                eligibility_json['caste_category'] = categories
            
            # State
            if state:
                eligibility_json['state'] = state.split(',') if ',' in state else [state]
            
            # Store original text
            eligibility_json['description'] = eligibility
        
        # Parse documents
        docs_list = []
        if documents:
            # Split by common delimiters
            docs_list = [doc.strip() for doc in documents.replace(';', ',').split(',') if doc.strip()]
        
        return {
            'id': scheme_id,
            'title': title[:200],
            'description': description or title,
            'source_url': website or f'https://india.gov.in/schemes/{scheme_id}',
            'source_id': 'kaggle_dataset',
            'issuing_authority': ministry or 'Government of India',
            'opportunity_type': opportunity_type,
            'eligibility': json.dumps(eligibility_json),
            'benefit_description': benefits,
            'required_documents': json.dumps(docs_list),
            'application_process': application,
            'launch_year': launch_year,
            'published_date': datetime.now().isoformat(),
            'trust_score': 0.90,
            'verification_status': 'verified'
        }
    
    def import_to_database(self):
        """Import schemes to PostgreSQL"""
        print("💾 Importing to database...\n")
        
        for i, row in enumerate(self.schemes, 1):
            try:
                scheme = self.map_to_schema(row)
                
                if not scheme:
                    self.stats['skipped'] += 1
                    continue
                
                # Insert into database via Docker
                success = self._insert_scheme(scheme)
                
                if success:
                    self.stats['imported'] += 1
                    if i % 10 == 0:
                        print(f"   Imported {i}/{self.stats['total']}...")
                else:
                    self.stats['errors'] += 1
                    
            except Exception as e:
                print(f"   ❌ Error row {i}: {e}")
                self.stats['errors'] += 1
        
        print(f"\n✅ Import complete!")
    
    def _insert_scheme(self, scheme):
        """Insert single scheme into database"""
        
        # Escape single quotes for SQL
        def escape(val):
            if val is None:
                return 'NULL'
            return f"'{str(val).replace(chr(39), chr(39)+chr(39))}'"
        
        sql = f"""
import psycopg2
conn = psycopg2.connect(
    host='localhost', database='civicsense',
    user='civicsense', password='civicsense_dev_password'
)
cur = conn.cursor()
cur.execute('''
    INSERT INTO opportunities (
        id, source_id, source_url, title, description,
        opportunity_type, issuing_authority, published_date,
        eligibility, benefit_description, required_documents,
        trust_score, verification_status
    ) VALUES (
        {escape(scheme['id'])},
        {escape(scheme['source_id'])},
        {escape(scheme['source_url'])},
        {escape(scheme['title'])},
        {escape(scheme['description'])},
        {escape(scheme['opportunity_type'])},
        {escape(scheme['issuing_authority'])},
        CURRENT_TIMESTAMP,
        {escape(scheme['eligibility'])},
        {escape(scheme.get('benefit_description'))},
        {escape(scheme['required_documents'])},
        {scheme['trust_score']},
        {escape(scheme['verification_status'])}
    )
    ON CONFLICT (source_url) DO UPDATE SET
        title = EXCLUDED.title,
        description = EXCLUDED.description,
        eligibility = EXCLUDED.eligibility,
        benefit_description = EXCLUDED.benefit_description
''')
conn.commit()
cur.close()
conn.close()
"""
        
        try:
            subprocess.run([
                'docker', 'exec', '-i', 'civicsense_db',
                'python3', '-c', sql
            ], capture_output=True, check=True, timeout=10)
            return True
        except:
            return False
    
    def show_stats(self):
        """Show import statistics"""
        print("\n" + "="*60)
        print("📊 Import Statistics")
        print("="*60)
        print(f"Total schemes in CSV:     {self.stats['total']}")
        print(f"Successfully imported:    {self.stats['imported']}")
        print(f"Skipped (invalid):        {self.stats['skipped']}")
        print(f"Errors:                   {self.stats['errors']}")
        print(f"Success rate:             {self.stats['imported']/self.stats['total']*100:.1f}%")
        print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Import Kaggle schemes CSV')
    parser.add_argument('csv_file', help='Path to CSV file')
    parser.add_argument('--with-ai', action='store_true', help='Generate AI summaries after import')
    
    args = parser.parse_args()
    
    print("="*60)
    print("🚀 Kaggle Government Schemes Import")
    print("="*60 + "\n")
    
    # Import CSV
    importer = KaggleImporter(args.csv_file)
    
    if not importer.read_csv():
        sys.exit(1)
    
    importer.import_to_database()
    importer.show_stats()
    
    # Verify in database
    print("🔍 Verifying import...")
    result = subprocess.run([
        'docker', 'exec', '-i', 'civicsense_db',
        'psql', '-U', 'civicsense', '-d', 'civicsense', '-c',
        'SELECT COUNT(*), source_id FROM opportunities WHERE source_id = \'kaggle_dataset\' GROUP BY source_id;'
    ], capture_output=True, text=True)
    
    print(result.stdout)
    
    print("✅ Import complete!")
    print("\n📋 Next steps:")
    print("1. View imported schemes:")
    print("   docker exec -it civicsense_db psql -U civicsense -d civicsense")
    print("   SELECT title, opportunity_type FROM opportunities WHERE source_id='kaggle_dataset' LIMIT 10;")
    print()
    
    if args.with_ai:
        print("2. Generating AI summaries...")
        print("   python scripts/add_ai_summaries.py")
    else:
        print("2. (Optional) Generate AI summaries:")
        print("   python scripts/import_kaggle_data.py {} --with-ai".format(args.csv_file))
    print()
    print("3. Start API server:")
    print("   python src/api/main.py")
    print()


if __name__ == '__main__':
    main()