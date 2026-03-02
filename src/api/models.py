# User Profile for Matching
{
  "age": 22,
  "state": "Bihar",
  "district": "Patna",
  "education_level": "graduate",
  "annual_income": 250000,
  "caste_category": "General",
  "occupation": "student",
  "gender": "male"
}

# Scheme Response
{
  "id": "scheme_001",
  "title": "PM-KISAN Scheme",
  "ministry": "Ministry of Agriculture",
  "category": "agriculture",
  "ai_summary": "₹6,000 per year for farmers...",
  "eligibility": {
    "occupation": ["farmer"],
    "land_holding": "< 2 hectares"
  },
  "benefits": "₹6,000 annual income support",
  "application_url": "https://pmkisan.gov.in",
  "match_score": 0.95, 
  "tags": ["agriculture", "income_support", "direct_benefit"]
}

# Search Results
{
  "total": 150,
  "page": 1,
  "page_size": 20,
  "results": [  "schemes with match_score and ai_summary" ],
  "facets": {
    "categories": {"agriculture": 30, "education": 25},
    "ministries": {"Ministry of Agriculture": 20}
  }
}