"""
Tests for Supabase Client and Configuration
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.supabase_client import SupabaseAdapter, get_supabase_adapter, get_supabase_client


class TestSupabaseIntegration:
    """Verifies Supabase client configuration, environment variable loading, and security."""

    def test_01_zero_hardcoding(self):
        """Verifies that src/supabase_client.py does not contain any hardcoded keys or URLs."""
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'supabase_client.py'))
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        # Assert no hardcoded URLs or JWT tokens
        assert "https://yhigjdifhrbirvrzwtgo" not in code, "Hardcoded URL detected!"
        assert "eyJhbG" not in code, "Hardcoded JWT secret detected!"
        assert "os.getenv('SUPABASE_URL')" in code
        assert "os.getenv('SUPABASE_ANON_KEY')" in code

    def test_02_adapter_reads_env_variables(self):
        """Verifies that SupabaseAdapter loads credentials from .env."""
        adapter = SupabaseAdapter()
        # Should detect the environment variables loaded from .env
        assert adapter.url is not None
        assert adapter.key is not None
        assert adapter.is_available is True
        assert adapter.client is not None

    def test_03_factory_helpers(self):
        """Verifies get_supabase_adapter() and get_supabase_client() helpers."""
        adapter = get_supabase_adapter()
        assert isinstance(adapter, SupabaseAdapter)
        client = get_supabase_client()
        assert client is not None

    def test_04_health_check_connection(self):
        """Verifies check_connection() returns health status and discovers tables."""
        adapter = get_supabase_adapter()
        check = adapter.check_connection()

        assert check['connected'] is True
        assert check['status'] == 'active'
        assert 'simulated_scenarios' in check['tables']
        assert check['tables']['simulated_scenarios']['exists'] is True

    def test_05_graceful_offline_degradation(self):
        """Verifies that unconfigured or offline adapter gracefully returns False/0 with zero crashes."""
        offline_adapter = SupabaseAdapter(supabase_url='', supabase_key='')
        assert offline_adapter.is_available is False

        # Calls should return False/0 without throwing exceptions
        assert offline_adapter.save_scenario_result(None, 'req_dummy') is False
        assert offline_adapter.save_scenario_comparison(None, 'req_dummy') is False
        assert offline_adapter.log_run('test_run', 0) is False

        status = offline_adapter.check_connection()
        assert status['connected'] is False
