import os
import requests
from dotenv import load_dotenv

load_dotenv()

class GroqClient:
    """Client for Llama 3.3 via Groq API."""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        
        self.base_url = "https://api.groq.com/openai/v1"
        self.model = "llama-3.3-70b-versatile"
    
    def chat(self, messages, model=None):
        """
        Send a chat completion request to Groq.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Optional model override
            
        Returns:
            String response content
        """
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
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
            raise Exception(f"Groq API request failed: {e}")
