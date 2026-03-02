# File: src/ai/eligibility_agent.py

"""
Eligibility Reasoning Agent using Ollama
Analyzes and explains eligibility criteria in simple terms
"""

from .base_agent import BaseAIAgent
import json
import logging

class EligibilityAgent(BaseAIAgent):
    """Analyzes eligibility criteria and provides clear explanations"""
    
    SYSTEM_PROMPT = """You are an expert at explaining government eligibility criteria to Indian citizens.

Your task: Convert complex eligibility rules into simple, checkable conditions.

CRITICAL: You must respond ONLY with valid JSON in this exact format:
{
  "simple_explanation": "2-3 sentence plain language explanation",
  "checklist": [
    "✓ Condition 1 in simple terms",
    "✓ Condition 2 in simple terms",
    "✓ Condition 3 in simple terms"
  ],
  "edge_cases": [
    "What if I'm exactly at the age limit?",
    "Does part-time work count?"
  ],
  "disqualifiers": [
    "You cannot apply if you already receive XYZ benefit",
    "Not eligible if annual income exceeds limit"
  ]
}

GUIDELINES:
- Use everyday language, not bureaucratic terms
- Provide specific numbers (ages, income limits in ₹)
- Explain abbreviations (SC = Scheduled Caste)
- Flag common misunderstandings
- Be encouraging but accurate
- Each checklist item must start with "✓ "
- Keep simple_explanation under 150 words
- List 2-4 checklist items
- List 1-3 edge cases (common questions)
- List 1-3 disqualifiers (reasons for rejection)

GOOD EXAMPLE:
{
  "simple_explanation": "You can apply if you're a Scheduled Caste student who has passed 10th grade and is currently studying in class 11th or higher. Your family's annual income must be less than ₹2.5 lakh per year. Both male and female students are eligible.",
  "checklist": [
    "✓ You belong to Scheduled Caste (SC) category",
    "✓ You have passed 10th standard exam",
    "✓ Currently studying in class 11th, 12th, or college",
    "✓ Family income is below ₹2,50,000 per year"
  ],
  "edge_cases": [
    "What if my caste certificate is from another state?",
    "Can I apply if I'm in the final year of my course?"
  ],
  "disqualifiers": [
    "Cannot apply if you're already receiving another central scholarship",
    "Not eligible if you've failed the previous year"
  ]
}

Respond ONLY with the JSON object, no additional text."""

    def __init__(self, model: str = "qwen2.5:7b"):
        """
        Initialize eligibility agent
        
        Recommended models:
        - qwen2.5:7b (excellent for structured output, multilingual)
        - llama3.1:8b (good reasoning)
        - mistral:7b (precise, factual)
        """
        super().__init__(model=model, temperature=0.2)  # Lower temp for accuracy
        
    async def explain(self, opportunity_data: dict) -> dict:
        """
        Generate eligibility explanation
        
        Args:
            opportunity_data: Dict with keys: title, description, eligibility
        
        Returns:
            Dict with simple_explanation, checklist, edge_cases, disqualifiers
        """
        # Extract eligibility information
        eligibility = opportunity_data.get('eligibility', {})
        
        # Build detailed context
        eligibility_context = {
            'title': opportunity_data.get('title', 'N/A'),
            'age_range': f"{eligibility.get('min_age', 'Any')} to {eligibility.get('max_age', 'Any')} years",
            'states': eligibility.get('states') or ['All India'],
            'education': eligibility.get('education_level', []),
            'income_limit': f"₹{eligibility.get('income_limit'):,}" if eligibility.get('income_limit') else 'No limit',
            'caste_category': eligibility.get('caste_category', []),
            'gender': eligibility.get('gender', 'Any'),
            'occupation': eligibility.get('occupation', []),
            'other_conditions': eligibility.get('custom_conditions', [])
        }
        
        user_message = f"""Opportunity: {eligibility_context['title']}

Eligibility Criteria:
- Age Range: {eligibility_context['age_range']}
- States/Regions: {', '.join(eligibility_context['states'])}
- Education Required: {', '.join(eligibility_context['education']) if eligibility_context['education'] else 'Any'}
- Income Limit: {eligibility_context['income_limit']}
- Caste/Category: {', '.join(eligibility_context['caste_category']) if eligibility_context['caste_category'] else 'All categories'}
- Gender: {eligibility_context['gender']}
- Occupation: {', '.join(eligibility_context['occupation']) if eligibility_context['occupation'] else 'Any'}
- Additional Conditions: {'; '.join(eligibility_context['other_conditions']) if eligibility_context['other_conditions'] else 'None'}

Create a clear eligibility explanation in JSON format as specified."""

        try:
            # Request JSON format from Ollama
            response = await self._call_ollama(
                system_prompt=self.SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.2,
                max_tokens=1024,
                response_format="json"
            )
            
            # Parse JSON
            result = json.loads(response)
            
            # Validate structure
            if not self._validate_response(result):
                raise ValueError("Invalid response structure")
            
            return result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {e}")
            self.logger.debug(f"Raw response: {response}")
            return self._fallback_explanation(eligibility_context)
            
        except Exception as e:
            self.logger.error(f"Eligibility explanation failed: {e}")
            return self._fallback_explanation(eligibility_context)
    
    def _validate_response(self, result: dict) -> bool:
        """Validate the AI response structure"""
        required_keys = ['simple_explanation', 'checklist', 'edge_cases', 'disqualifiers']
        
        # Check all keys present
        if not all(key in result for key in required_keys):
            return False
        
        # Check types
        if not isinstance(result['simple_explanation'], str):
            return False
        if not isinstance(result['checklist'], list):
            return False
        if not isinstance(result['edge_cases'], list):
            return False
        if not isinstance(result['disqualifiers'], list):
            return False
        
        # Check checklist items start with ✓
        if not all(item.startswith('✓') for item in result['checklist']):
            return False
        
        return True
    
    def _fallback_explanation(self, eligibility_context: dict) -> dict:
        """Fallback template-based explanation if AI fails"""
        checklist = []
        
        if eligibility_context['age_range'] != 'Any to Any years':
            checklist.append(f"✓ Age between {eligibility_context['age_range']}")
        
        if eligibility_context['states'] != ['All India']:
            checklist.append(f"✓ Resident of {', '.join(eligibility_context['states'][:3])}")
        
        if eligibility_context['education']:
            checklist.append(f"✓ Education: {', '.join(eligibility_context['education'][:2])}")
        
        if eligibility_context['income_limit'] != 'No limit':
            checklist.append(f"✓ Family income below {eligibility_context['income_limit']}")
        
        return {
            'simple_explanation': f"Check the eligibility criteria for {eligibility_context['title']}. Review the checklist below to see if you qualify.",
            'checklist': checklist if checklist else ["✓ Check official notification for detailed criteria"],
            'edge_cases': ["Contact the issuing authority for specific cases"],
            'disqualifiers': ["Incomplete applications will be rejected"]
        }


# Example usage
async def test_eligibility_agent():
    """Test the eligibility agent"""
    agent = EligibilityAgent(model="qwen2.5:7b")
    
    # Check model availability
    if not await agent.check_model_available():
        print("Model not found. Pulling model...")
        await agent.pull_model()
    
    # Test data
    sample_opportunity = {
        'title': 'National Scholarship Portal - Post Matric Scholarship',
        'description': 'Scholarship for SC students',
        'eligibility': {
            'min_age': None,
            'max_age': None,
            'states': [],  # All India
            'education_level': ['class_10th', 'class_12th', 'graduate'],
            'caste_category': ['SC'],
            'income_limit': 250000,
            'gender': 'any',
            'custom_conditions': ['Student must be currently enrolled in a recognized institution']
        }
    }
    
    result = await agent.explain(sample_opportunity)
    print("Eligibility Explanation:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_eligibility_agent())