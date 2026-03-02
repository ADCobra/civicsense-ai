# File: src/ai/translation_agent.py

"""
Translation Agent using Ollama
Translates opportunities to Indian languages
"""

from .base_agent import BaseAIAgent
import logging

class TranslationAgent(BaseAIAgent):
    """Translates opportunities to multiple Indian languages using Ollama"""
    
    SUPPORTED_LANGUAGES = {
        'hi': 'Hindi (हिंदी)',
        'bn': 'Bengali (বাংলা)',
        'te': 'Telugu (తెలుగు)',
        'mr': 'Marathi (मराठी)',
        'ta': 'Tamil (தமிழ்)',
        'gu': 'Gujarati (ગુજરાતી)',
        'kn': 'Kannada (ಕನ್ನಡ)',
        'ml': 'Malayalam (മലയാളം)',
        'pa': 'Punjabi (ਪੰਜਾਬੀ)',
        'or': 'Odia (ଓଡ଼ିଆ)'
    }
    
    def __init__(self, model: str = "qwen2.5:7b"):
        """
        Initialize translation agent
        
        Recommended models for multilingual:
        - qwen2.5:7b (excellent for Indian languages)
        - aya:8b (specifically trained for multilingual, including Indian languages)
        - llama3.1:8b (decent multilingual support)
        """
        super().__init__(model=model, temperature=0.2)  # Lower temp for accuracy
    
    def _get_translation_prompt(self, target_lang: str) -> str:
        """Get language-specific system prompt"""
        lang_name = self.SUPPORTED_LANGUAGES.get(target_lang, 'Hindi')
        
        return f"""You are a professional translator specializing in Indian government communications.

Your task: Translate the following text to {lang_name}.

CRITICAL REQUIREMENTS:
1. Maintain formal but accessible tone
2. Preserve all numbers, dates, amounts (₹), and proper nouns
3. Use culturally appropriate terms for government schemes
4. For technical terms with no common translation, keep original and add explanation in {lang_name}
5. Maintain the EXACT meaning - do not summarize or simplify
6. Use proper script for the target language
7. Keep formatting (line breaks, bullet points)

IMPORTANT:
- Translate "scholarship" appropriately (छात्रवृत्ति in Hindi, స్కాలర్‌షిప్ in Telugu, etc.)
- Keep official scheme names in original if they're well-known (e.g., PM-KISAN)
- Translate government department names accurately
- Keep website URLs and emails in original

Respond ONLY with the translation, no explanations or notes."""
    
    async def translate(self, text: str, target_lang: str) -> str:
        """
        Translate text to target language
        
        Args:
            text: Text to translate
            target_lang: Language code (hi, bn, te, mr, ta, gu, kn, ml, pa, or)
        
        Returns:
            Translated text
        """
        if target_lang not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {target_lang}. Supported: {list(self.SUPPORTED_LANGUAGES.keys())}")
        
        # Don't translate if already in target language or empty
        if not text or len(text.strip()) < 5:
            return text
        
        system_prompt = self._get_translation_prompt(target_lang)
        
        user_message = f"""Translate the following to {self.SUPPORTED_LANGUAGES[target_lang]}:

{text}

Translation:"""

        try:
            translation = await self._call_ollama(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.2,  # Low temperature for consistent translation
                max_tokens=2048
            )
            
            # Clean up response
            translation = translation.strip()
            
            # Remove any artifacts
            translation = translation.replace('Translation:', '').strip()
            
            return translation
            
        except Exception as e:
            self.logger.error(f"Translation failed for {target_lang}: {e}")
            # Return original text as fallback
            return text
    
    async def translate_opportunity(self, 
                                   opportunity_data: dict, 
                                   target_languages: list) -> dict:
        """
        Translate all relevant fields of an opportunity
        
        Args:
            opportunity_data: Dict with title, ai_summary, ai_eligibility_explanation
            target_languages: List of language codes to translate to
        
        Returns:
            Dict mapping language codes to translated content
        """
        translations = {}
        
        for lang in target_languages:
            if lang not in self.SUPPORTED_LANGUAGES:
                self.logger.warning(f"Skipping unsupported language: {lang}")
                continue
            
            try:
                # Translate key fields
                translated = {}
                
                if 'title' in opportunity_data:
                    translated['title'] = await self.translate(
                        opportunity_data['title'], lang
                    )
                
                if 'ai_summary' in opportunity_data:
                    translated['ai_summary'] = await self.translate(
                        opportunity_data['ai_summary'], lang
                    )
                
                if 'ai_eligibility_explanation' in opportunity_data:
                    # If it's a dict, translate the simple_explanation
                    elig_text = opportunity_data['ai_eligibility_explanation']
                    if isinstance(elig_text, dict):
                        elig_text = elig_text.get('simple_explanation', '')
                    
                    if elig_text:
                        translated['ai_eligibility_explanation'] = await self.translate(
                            elig_text, lang
                        )
                
                translations[lang] = translated
                self.logger.info(f"Successfully translated to {self.SUPPORTED_LANGUAGES[lang]}")
                
            except Exception as e:
                self.logger.error(f"Failed to translate to {lang}: {e}")
                continue
        
        return translations
    
    async def batch_translate(self, 
                            texts: list, 
                            target_lang: str,
                            batch_size: int = 5) -> list:
        """
        Translate multiple texts efficiently
        
        Args:
            texts: List of texts to translate
            target_lang: Target language code
            batch_size: Number of texts to combine in one request
        
        Returns:
            List of translated texts
        """
        if not texts:
            return []
        
        translated = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Combine with separators
            combined = "\n---SEPARATOR---\n".join(batch)
            
            # Translate batch
            result = await self.translate(combined, target_lang)
            
            # Split back
            batch_translated = result.split("---SEPARATOR---")
            translated.extend([t.strip() for t in batch_translated])
        
        return translated


# Example usage
async def test_translation_agent():
    """Test the translation agent"""
    agent = TranslationAgent(model="qwen2.5:7b")
    
    # Check model availability
    if not await agent.check_model_available():
        print("Model not found. Pulling model...")
        await agent.pull_model()
    
    # Test single translation
    english_text = "₹6,000 per year for small farmers! If you own less than 2 hectares of farmland, you can receive ₹2,000 every 4 months directly in your bank account."
    
    print("Original (English):")
    print(english_text)
    print()
    
    # Translate to Hindi
    hindi = await agent.translate(english_text, 'hi')
    print("Hindi Translation:")
    print(hindi)
    print()
    
    # Translate opportunity data
    opportunity = {
        'title': 'PM-KISAN Scheme',
        'ai_summary': english_text,
        'ai_eligibility_explanation': 'You can apply if you own less than 2 hectares of farmland and are an Indian citizen.'
    }
    
    translations = await agent.translate_opportunity(
        opportunity, 
        target_languages=['hi', 'te', 'mr']
    )
    
    print("Full Opportunity Translations:")
    for lang, content in translations.items():
        print(f"\n{agent.SUPPORTED_LANGUAGES[lang]}:")
        print(f"Title: {content['title']}")
        print(f"Summary: {content['ai_summary']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_translation_agent())