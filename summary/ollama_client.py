import requests
import json
from utils.logger import logger

class OllamaClient:
    def __init__(self, host="http://localhost:11434"):
        self.host = host
        self.api_url = f"{self.host}/api/generate"
        self.tags_url = f"{self.host}/api/tags"
        
    def is_available(self):
        try:
            response = requests.get(self.tags_url, timeout=3)
            return response.status_code == 200
        except Exception:
            return False
            
    def get_models(self):
        try:
            response = requests.get(self.tags_url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                return [m['name'] for m in data.get('models', [])]
            return []
        except Exception as e:
            logger.error(f"Failed to fetch Ollama models: {e}")
            return []
            
    def generate_text(self, prompt: str, model: str):
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=120)
            if response.status_code == 200:
                return response.json().get('response', '')
            else:
                logger.error(f"Ollama error: {response.text}")
                return f"Error from Ollama: {response.status_code}"
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return "AI Generation unavailable"

    def generate_summary(self, transcript: str, model: str, language: str = "Indonesian"):
        if not transcript.strip():
            return "No transcript available to summarize."
            
        prompt = f"""You are a professional AI assistant for meeting summaries.
Your task is to summarize the following transcript clearly, concisely, and structurally.

Write the summary ENTIRELY in {language}. Use the following structure, but translate the headings into {language}:

## Executive Summary
(Write the main summary of the entire conversation)

## Main Discussion Points
(Key points discussed)

## Decisions Made
(What decisions were agreed upon)

## Action Items & Tasks
(Tasks or action items to be done next)

## Risks & Issues
(Problems or risks discussed)

Output in neat Markdown format. Do not fabricate information. Output ONLY in {language}.

Transcript:
{transcript}
"""
        return self.generate_text(prompt, model)
