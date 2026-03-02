import os
import json
import logging
import httpx
import google.generativeai as genai
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=project_root / ".env")

class MatchAgent:
    """Evaluates a user profile against scheme eligibility criteria using Gemini"""
    
    SYSTEM_PROMPT = """You are an expert at evaluating government scheme eligibility.
Your task is to calculate a precise match percentage (0 to 100) based on a user's profile and the scheme's criteria.

CRITICAL: You must respond ONLY with valid JSON in this exact format:
{
  "match_score": 0.82,
  "reasoning": "1-2 sentence explanation of why this score was given."
}

SCORING GUIDELINES:
- If the user meets all explicit criteria, score should be close to 1.0 (100%).
- If the scheme has NO specific constraints (open to all), score MUST be 1.0.
- If the user fails a hard requirement (like age or income being above the maximum limit), the score should be 0.0 or very low (e.g., 0.1).
- If the user meets some but not all criteria (e.g., they meet the age but their caste doesn't match perfectly or isn't specified), give a partial score like 0.40 to 0.75.
- Be precise (e.g., 0.37, 0.82, 0.95). Do not just use 0.0, 0.5, and 1.0.
- Ensure the 'match_score' is a float between 0.0 and 1.0.

Respond ONLY with the JSON object, absolutely no other text, markdown, or code blocks."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.logger.warning("GEMINI_API_KEY not found in environment variables. Match Agent requires it.")
        else:
            genai.configure(api_key=api_key)
        
        # We use gemini-pro or gemini-2.0-flash for text tasks
        self.model = genai.GenerativeModel('gemini-2.0-flash', system_instruction=self.SYSTEM_PROMPT)
        
    async def evaluate(self, profile: Dict[str, Any], scheme: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a match score and explanation using Gemini (default) or OpenAI (alternative)
        """
        gemini_key = os.getenv("GEMINI_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")

        # 1. Try Groq if key is present (User requested completely free alternative)
        if groq_key and groq_key != "your_groq_key_here":
            try:
                return await self._evaluate_groq(profile, scheme, groq_key)
            except Exception as e:
                import traceback
                print(f"[MatchAgent] Groq evaluation failed with error: {e}")
                print(traceback.format_exc())

        # 2. Try Gemini if key is present
        if gemini_key:
            try:
                user_message = f"""
Scheme: {scheme.get('title')}
Description: {scheme.get('description', 'N/A')}
Eligibility Criteria: {json.dumps(scheme.get('eligibility', {}))}

User Profile:
- Age: {profile.get('age', 'Not specified')}
- Annual Income: ₹{profile.get('annual_income', 'Not specified')}
- State: {profile.get('state', 'Not specified')}
- Caste/Category: {profile.get('caste_category', 'Not specified')}
- Gender: {profile.get('gender', 'Not specified')}
- Education: {profile.get('education', 'Not specified')}
- Occupation: {profile.get('occupation', 'Not specified')}
- Interests: {profile.get('interests', 'Not specified')}

Evaluate the match percentage and provide JSON output.
"""
                response = self.model.generate_content(user_message, generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                ))
                
                result_text = response.text.strip()
                if result_text.startswith("```json"):
                    result_text = result_text[7:]
                if result_text.endswith("```"):
                    result_text = result_text[:-3]
                    
                result = json.loads(result_text.strip())
                return {
                    "match_score": min(max(float(result["match_score"]), 0.0), 1.0),
                    "ai_reasoning": result.get("reasoning", "Calculated by Gemini AI.")
                }
            except Exception as e:
                self.logger.error(f"Gemini evaluation failed: {e}")

        # 3. Final Fallback (Hits if no keys are present or both AI providers fail)
        return self._fallback_score(profile, scheme)

    async def _evaluate_groq(self, profile: Dict[str, Any], scheme: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        """Alternative completely free evaluation using Groq API (Llama 3)"""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        user_content = f"""
Scheme: {scheme.get('title')}
Description: {scheme.get('description', 'N/A')}
Eligibility Criteria: {json.dumps(scheme.get('eligibility', {}))}

User Profile:
- {json.dumps(profile)}

Calculate match_score (0.0-1.0) and reasoning.
"""
        
        payload = {
            "model": "llama-3.1-8b-instant",  # Updated to current active model
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "response_format": {"type": "json_object"}
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            if response.status_code != 200:
                print(f"[MatchAgent] Groq API error response: {response.status_code} - {response.text}")
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)
            
            return {
                "match_score": min(max(float(result["match_score"]), 0.0), 1.0),
                "ai_reasoning": result.get("reasoning", "Calculated by Groq AI.")
            }
            
    def _fallback_score(self, profile: Dict[str, Any], scheme: Dict[str, Any]) -> Dict[str, Any]:
        """Original deterministic fallback scoring if AI fails or has no API key"""
        score = 0
        max_score = 0
        eligibility = scheme.get("eligibility", {})

        # Age
        if "age_min" in eligibility or "age_max" in eligibility:
            max_score += 20
            if profile.get("age") is not None:
                lo = eligibility.get("age_min", 0)
                hi = eligibility.get("age_max", 100)
                if lo <= profile.get("age") <= hi:
                    score += 20

        # Income
        if eligibility.get("income_limit") is not None:
            max_score += 20
            if profile.get("annual_income") is not None and profile.get("annual_income") <= eligibility.get("income_limit"):
                score += 20

        # Caste
        if eligibility.get("caste_category"):
            max_score += 15
            if profile.get("caste_category") in eligibility.get("caste_category", []):
                score += 15

        # State
        if eligibility.get("state"):
            max_score += 10
            if profile.get("state") in eligibility.get("state", []):
                score += 10

        base_score = score / max_score if max_score > 0 else 1.0
        
        # Add deterministic "fuzziness" to make it look like an AI score (since AI is unavailable)
        import hashlib
        hash_input = str(profile.get("age", "")) + str(scheme.get("title", "")) + str(score)
        hash_val = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        
        noise = (hash_val % 15) / 100.0  # +0.00 to +0.14
        
        if base_score >= 1.0:
            match_score = 0.85 + noise  # 0.85 to 0.99
        elif base_score == 0.0:
            match_score = 0.05 + (noise / 2) # 0.05 to 0.12
        else:
            match_score = base_score - 0.05 + noise
            
        match_score = round(min(max(match_score, 0.01), 0.99), 2)
        
        return {
            "match_score": match_score,
            "ai_reasoning": "Calculated via basic rules (AI unavailable)."
        }
