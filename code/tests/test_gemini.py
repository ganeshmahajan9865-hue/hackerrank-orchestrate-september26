"""
Unit Tests for Gemini Client Module — Buy or Wait?
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.gemini_client import GeminiClient, get_gemini_client


def test_gemini_client_init():
    """Verifies that GeminiClient initializes properly without error."""
    client = GeminiClient(api_key='test_mock_key_12345')
    assert client.api_key == 'test_mock_key_12345'
    assert client.is_available is True
    assert client.timeout == 15


def test_gemini_unconfigured():
    """Verifies that an unconfigured client gracefully reports unconfigured status."""
    client = GeminiClient(api_key='')
    assert client.is_available is False
    health = client.check_connection()
    assert health['status'] == 'unconfigured'


def test_gemini_offline_fallback():
    """Verifies that text generation returns None on unconfigured client allowing local fallback."""
    client = GeminiClient(api_key='')
    res = client.generate_text('Test prompt')
    assert res is None


def test_gemini_caching_mechanism(tmp_path):
    """Verifies in-memory and disk caching prevents duplicate processing."""
    cache_dir = str(tmp_path / 'cache')
    client = GeminiClient(api_key='test_key', cache_dir=cache_dir)
    
    # Store directly in cache
    client._set_cache('test_key_hash', {'text': 'Cached explanation', 'model': 'gemini-3.6-flash'})
    
    # Retrieve from cache
    retrieved = client._get_cache('test_key_hash')
    assert retrieved is not None
    assert retrieved['text'] == 'Cached explanation'


def test_singleton_getter():
    """Verifies that get_gemini_client returns a singleton instance."""
    c1 = get_gemini_client()
    c2 = get_gemini_client()
    assert c1 is c2
