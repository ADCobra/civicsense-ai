# File: src/ai/summarizer_agent.py

"""
Summarization Agent using Ollama
Generates concise, actionable summaries of government opportunities
"""

from .base_agent import BaseAIAgent
import logging

class SummarizerAgent(BaseAIAgent):
    """Generates concise, actionable summaries using free Ollama models"""
    
    SYSTEM_PROMPT = """You are an expert at summarizing Indian government opportunities for citizens.

Your goal: Create a 2-3 sentence summary that clearly explains:
1. What the opportunity is
2. Who can benefit (eligibility in simple terms)
3. Key deadline or action needed

CRITICAL REQUIREMENTS:
- Use simple language (8th grade reading level)
- Avoid bureaucratic jargon
- Be specific about benefits (mention amounts in ₹ if available)
- Include urgency if deadline is near
- Write in active voice
- Keep it under 100 words
- Start with the benefit/amount if applicable

GOOD EXAMPLE:
Input: "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN) is a Central Sector Scheme..."
Output: "₹6,000 per year for small farmers! If you own less than 2 hectares of farmland, you can receive ₹2,000 every 4 months directly in your bank account. Registration is open year-round through your nearest CSC center."

BAD EXAMPLE (too formal):
"The PM-KISAN scheme provides financial assistance to eligible farmers. Applicants must fulfill the criteria and submit applications at designated centers."

Write ONLY the summary, no explanations or preamble."""

    def __init__(self, model: str = "llama3.1:8b"):
        """
        Initialize summarizer agent
        
        Recommended models:
        - llama3.1:8b (balanced, fast)
        - qwen2.5:7b (multilingual, great for Indian context)
        - mistral:7b (concise, factual)
        """
        super().__init__(model=model, temperature=0.3)
        
    async def summarize(self, opportunity_data: dict) -> str:
        """
        Generate summary for an opportunity
        
        Args:
            opportunity_data: Dict with keys: title, description, 
                            issuing_authority, benefit_description, application_end
        
        Returns:
            Concise summary string
        """
        # Build user message with all context
        user_message = f"""Opportunity Title: {opportunity_data.get('title', 'N/A')}

Full Description: {opportunity_data.get('description', 'N/A')}

Issuing Authority: {opportunity_data.get('issuing_authority', 'Government of India')}

Benefit/Amount: {opportunity_data.get('benefit_description') or opportunity_data.get('benefit_amount', 'Not specified')}

Deadline: {opportunity_data.get('application_end', 'Rolling basis')}

Create a clear, compelling summary following the guidelines above. Focus on what matters most to citizens."""

        try:
            summary = await self._call_ollama(
                system_prompt=self.SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.3,
                max_tokens=200  # Keep summaries short
            )
            
            # Clean up the response
            summary = summary.strip()
            
            # Remove any markdown or formatting artifacts
            summary = summary.replace('**', '').replace('*', '')
            
            # Ensure it's not too long
            if len(summary) > 500:
                summary = summary[:497] + "..."
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Summarization failed: {e}")
            # Fallback to simple template-based summary
            return self._fallback_summary(opportunity_data)
    
    def _fallback_summary(self, opportunity_data: dict) -> str:
        """Fallback template-based summary if AI fails"""
        title = opportunity_data.get('title', 'Government Opportunity')
        benefit = opportunity_data.get('benefit_description') or \
                 f"₹{opportunity_data.get('benefit_amount', 'Variable')}" if opportunity_data.get('benefit_amount') else "Benefits available"
        
        return f"{title}: {benefit}. Check eligibility and apply through official portal."


# Example usage
async def test_summarizer():
    """Test the summarizer agent"""
    agent = SummarizerAgent(model="llama3.1:8b")
    
    # Check if model is available
    if not await agent.check_model_available():
        print("Model not found. Pulling model...")
        await agent.pull_model()
    
    # Test data
    sample_opportunity = {
        'title': 'National Scholarship Portal - Post Matric Scholarship for SC Students',
        'description': 'Central Sector Scheme providing financial assistance to Scheduled Caste students for pursuing post-matriculation or post-secondary studies to enable them to complete their education. Students studying in classes 11th and 12th and pursuing post SSC studies can apply.',
        'issuing_authority': 'Ministry of Social Justice and Empowerment',
        'benefit_amount': 15000.0,
        'benefit_description': '₹10,000-20,000 per year depending on course',
        'application_end': '2025-03-30'
    }
    
    summary = await agent.summarize(sample_opportunity)
    print("Generated Summary:")
    print(summary)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_summarizer())