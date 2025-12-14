import os
import requests
from dotenv import load_dotenv

load_dotenv()

class DeepSeekClient:
    """Client for DeepSeek R1 via OpenRouter API."""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
        
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "tngtech/deepseek-r1t-chimera:free"
    
    def chat(self, messages, model=None):
        """
        Send a chat completion request to DeepSeek R1 via OpenRouter.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Optional model override (defaults to deepseek/deepseek-r1)
            
        Returns:
            Dict with response in format: {"message": {"content": "response text"}}
        """
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/CODERTG2/LegalAI",
            "X-Title": "LegalAI"
        }
        
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
            
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            data = response.json()
            
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenRouter API request failed: {e}")
