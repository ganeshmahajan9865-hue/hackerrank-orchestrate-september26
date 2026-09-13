"""
Gemini Client Module — Buy or Wait?

Provides secure, cached, rate-limit-safe integration with Google Gemini LLM and Vision.
Supports:
- Zero-exposure key management (reads GEMINI_API_KEY, GOOGLE_API_KEY, API_Key from .env)
- Multimodal receipt extraction via Gemini Vision
- Text explanation refinement via Gemini Flash
- Multi-tier in-memory and disk caching to eliminate redundant API calls
- Graceful offline fallback when network or quota is unavailable
"""

import os
import sys
import json
import hashlib
import base64
from typing import Dict, Any, Optional, List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import requests

DEFAULT_MODELS = [
    'gemini-3.6-flash',
    'gemini-3.5-flash',
    'gemini-flash-latest'
]


class GeminiClient:
    """Client for Google Gemini REST API with caching and deterministic fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 15,
        cache_dir: str = '.cache/gemini',
        preferred_model: str = 'gemini-3.6-flash'
    ):
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = (
                os.getenv('GEMINI_API_KEY')
                or os.getenv('GOOGLE_API_KEY')
                or os.getenv('API_Key')
                or os.getenv('API_KEY')
            )
        self.timeout = timeout
        self.cache_dir = os.path.abspath(cache_dir)
        self.preferred_model = preferred_model
        self.memory_cache: Dict[str, Any] = {}

        if not os.path.exists(self.cache_dir):
            try:
                os.makedirs(self.cache_dir, exist_ok=True)
            except Exception:
                pass

    @property
    def is_available(self) -> bool:
        """Returns True if an API key is present."""
        return bool(self.api_key and len(self.api_key.strip()) > 10)

    def _get_cache(self, key: str) -> Optional[Any]:
        """Retrieves item from memory or disk cache."""
        if key in self.memory_cache:
            return self.memory_cache[key]

        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.memory_cache[key] = data
                return data
            except Exception:
                pass
        return None

    def _set_cache(self, key: str, data: Any):
        """Saves item to memory and disk cache."""
        self.memory_cache[key] = data
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def check_connection(self) -> Dict[str, Any]:
        """Checks API health and model access without exposing credentials."""
        if not self.is_available:
            return {
                'status': 'unconfigured',
                'message': 'No GEMINI_API_KEY found in environment or .env'
            }

        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                models = [
                    m['name'] for m in resp.json().get('models', [])
                    if 'generateContent' in m.get('supportedGenerationMethods', [])
                ]
                return {
                    'status': 'active',
                    'available_models_count': len(models),
                    'preferred_model': self.preferred_model,
                    'supported': any(self.preferred_model in m for m in models)
                }
            else:
                return {
                    'status': 'error',
                    'code': resp.status_code,
                    'message': 'Failed to query models API'
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Network error: {type(e).__name__}'
            }

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.0
    ) -> Optional[str]:
        """
        Generates text using Gemini with caching.
        Returns None if offline or failed, allowing caller to use local fallback.
        """
        if not self.is_available:
            return None

        model_name = model or self.preferred_model
        cache_key = hashlib.sha256(f"text:{model_name}:{system_instruction}:{prompt}".encode('utf-8')).hexdigest()
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached.get('text')

        payload: Dict[str, Any] = {
            'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {'temperature': temperature}
        }
        if system_instruction:
            payload['systemInstruction'] = {'parts': [{'text': system_instruction}]}

        models_to_try = [model_name] + [m for m in DEFAULT_MODELS if m != model_name]

        for candidate_model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{candidate_model}:generateContent?key={self.api_key}"
            try:
                resp = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get('candidates', [])
                    if candidates:
                        parts = candidates[0].get('content', {}).get('parts', [])
                        if parts:
                            text = parts[0].get('text', '').strip()
                            self._set_cache(cache_key, {'text': text, 'model': candidate_model})
                            return text
                elif resp.status_code in [404, 400]:
                    continue
                elif resp.status_code == 429:
                    break
            except Exception:
                continue

        return None

    def extract_receipt(
        self,
        image_path: str,
        model: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extracts structured financial transaction fields from an image receipt.
        Returns dict with keys: amount, currency, biller, document_type.
        """
        if not self.is_available or not os.path.exists(image_path):
            return None

        try:
            with open(image_path, 'rb') as f:
                img_bytes = f.read()
            file_hash = hashlib.sha256(img_bytes).hexdigest()
        except Exception:
            return None

        cache_key = f"vision_{file_hash}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        mime_type = 'image/png' if image_path.lower().endswith('.png') else 'image/jpeg'

        prompt = (
            "Analyze this receipt/invoice/bill image and extract: "
            "1. total amount (float, e.g. 4365000.0), "
            "2. currency (3-letter ISO code, e.g. IDR, INR, USD), "
            "3. biller or merchant name, "
            "4. document_type (e.g. payslip, invoice, bill, receipt). "
            "Return strictly valid JSON with keys: amount, currency, biller, document_type."
        )

        model_name = model or self.preferred_model
        models_to_try = [model_name] + [m for m in DEFAULT_MODELS if m != model_name]

        for candidate_model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{candidate_model}:generateContent?key={self.api_key}"
            payload = {
                'contents': [{
                    'parts': [
                        {'text': prompt},
                        {'inlineData': {'mimeType': mime_type, 'data': img_b64}}
                    ]
                }],
                'generationConfig': {
                    'responseMimeType': 'application/json',
                    'temperature': 0.0
                }
            }

            try:
                resp = requests.post(url, json=payload, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get('candidates', [])
                    if candidates:
                        parts = candidates[0].get('content', {}).get('parts', [])
                        if parts:
                            raw_json = parts[0].get('text', '').strip()
                            parsed = json.loads(raw_json)
                            if 'amount' in parsed:
                                if isinstance(parsed['amount'], str):
                                    cleaned = parsed['amount'].replace(',', '').replace('$', '').strip()
                                    parsed['amount'] = float(cleaned)
                                else:
                                    parsed['amount'] = float(parsed['amount'])
                            self._set_cache(cache_key, parsed)
                            return parsed
                elif resp.status_code in [404, 400]:
                    continue
                elif resp.status_code == 429:
                    break
            except Exception:
                continue

        return None


_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """Singleton getter for GeminiClient."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client
