# File: src/ai/base_agent.py

"""
Base AI Agent using Ollama (Free, Self-hosted LLM)
Supports models like Llama 3.1, Mistral, Qwen, etc.
"""

from typing import Dict, List, Optional
import httpx
import json
import logging
import os

class BaseAIAgent:
    """Base class for all AI agents using Ollama"""
    
    def __init__(self, 
                 model: str = "llama3.1:8b",
                 ollama_url: str = None,
                 temperature: float = 0.3):
        """
        Initialize AI agent with Ollama
        
        Args:
            model: Ollama model name (llama3.1:8b, mistral:7b, qwen2.5:7b)
            ollama_url: Ollama API URL (default: http://localhost:11434)
            temperature: Model temperature (0.0-1.0)
        """
        self.model = model
        self.ollama_url = ollama_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.temperature = temperature
        self.logger = logging.getLogger(self.__class__.__name__)
        
    async def _call_ollama(self, 
                          system_prompt: str, 
                          user_message: str,
                          temperature: float = None,
                          max_tokens: int = 4096,
                          response_format: str = "text") -> str:
        """
        Call Ollama API with error handling
        
        Args:
            system_prompt: System instructions
            user_message: User query
            temperature: Override default temperature
            max_tokens: Maximum response length
            response_format: "text" or "json"
        
        Returns:
            Generated text
        """
        try:
            # Prepare request
            url = f"{self.ollama_url}/api/generate"
            
            # Combine system and user message
            full_prompt = f"""<|system|>
{system_prompt}
<|end|>
<|user|>
{user_message}
<|end|>
<|assistant|>"""
            
            payload = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature or self.temperature,
                    "num_predict": max_tokens,
                    "top_p": 0.9,
                    "top_k": 40
                }
            }
            
            # If JSON format requested, add to system prompt
            if response_format == "json":
                payload["format"] = "json"
            
            # Make async request
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                return result["response"].strip()
                
        except httpx.TimeoutException:
            self.logger.error(f"Ollama request timeout for model {self.model}")
            raise Exception("AI service timeout - please try again")
            
        except httpx.HTTPError as e:
            self.logger.error(f"Ollama HTTP error: {e}")
            raise Exception(f"AI service error: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Ollama error: {e}")
            raise
    
    async def _call_ollama_chat(self,
                               messages: List[Dict],
                               temperature: float = None,
                               max_tokens: int = 4096) -> str:
        """
        Call Ollama Chat API (better for conversation-style prompts)
        
        Args:
            messages: List of {"role": "system/user/assistant", "content": "..."}
            temperature: Override default temperature
            max_tokens: Maximum response length
        
        Returns:
            Generated text
        """
        try:
            url = f"{self.ollama_url}/api/chat"
            
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature or self.temperature,
                    "num_predict": max_tokens
                }
            }
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                return result["message"]["content"].strip()
                
        except Exception as e:
            self.logger.error(f"Ollama chat error: {e}")
            raise
    
    async def check_model_available(self) -> bool:
        """Check if the specified model is available in Ollama"""
        try:
            url = f"{self.ollama_url}/api/tags"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                models = response.json()
                available_models = [m["name"] for m in models.get("models", [])]
                
                if self.model not in available_models:
                    self.logger.warning(f"Model {self.model} not found. Available: {available_models}")
                    return False
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to check Ollama models: {e}")
            return False
    
    async def pull_model(self) -> bool:
        """Pull/download the model if not available"""
        try:
            self.logger.info(f"Pulling model {self.model}... (this may take a few minutes)")
            
            url = f"{self.ollama_url}/api/pull"
            payload = {"name": self.model}
            
            async with httpx.AsyncClient(timeout=600.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                self.logger.info(f"Successfully pulled model {self.model}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to pull model: {e}")
            return False


# Utility function for standalone usage
async def get_completion(prompt: str, 
                        model: str = "llama3.1:8b",
                        system_prompt: str = "You are a helpful assistant.") -> str:
    """
    Simple wrapper for one-off completions
    
    Usage:
        response = await get_completion("What is the capital of India?")
    """
    agent = BaseAIAgent(model=model)
    return await agent._call_ollama(system_prompt, prompt)