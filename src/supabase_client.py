"""
Supabase Storage and Integration Module

Provides an optional persistent cloud backend for:
- Saving What-If purchase scenario simulations and comparisons
- Exporting / syncing output predictions to Supabase PostgreSQL
- Logging execution runs and model usage history

Design Principles:
1. Zero Hardcoding: Reads credentials strictly from environment variables (.env).
2. Non-Intrusive & Non-Blocking: If Supabase credentials are not configured,
   the adapter degrades gracefully with zero errors, zero latency, and zero broken tests.
3. Offline Safe: Never blocks the core offline evaluation pipeline (code/main.py).
4. Secure: Keeps all sensitive credentials inside .env; never leaks secrets to logs.
"""

import os
import sys
from typing import Dict, List, Optional, Any, Union
import datetime
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Robust .env loading from current directory or project root
try:
    from dotenv import load_dotenv
    # Check current directory and repository root candidates
    for cand in [
        os.path.join(os.getcwd(), '.env'),
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env')),
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    ]:
        if os.path.isfile(cand):
            load_dotenv(cand)
            break
except ImportError:
    pass

try:
    from supabase import create_client, Client
    SUPABASE_INSTALLED = True
except ImportError:
    SUPABASE_INSTALLED = False
    Client = Any


class SupabaseAdapter:
    """
    Optional Supabase Cloud Database Client.
    
    Provides structured persistence for scenarios, evaluation predictions,
    and audit logs when configured.
    """

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None
    ):
        # Read from arguments or environment variables (zero hardcoded values)
        if supabase_url is not None:
            self.url = supabase_url
        else:
            self.url = os.getenv('SUPABASE_URL') or os.getenv('NEXT_PUBLIC_SUPABASE_URL')

        if supabase_key is not None:
            self.key = supabase_key
        else:
            self.key = (
                os.getenv('SUPABASE_ANON_KEY')
                or os.getenv('SUPABASE_KEY')
                or os.getenv('SUPABASE_SERVICE_ROLE_KEY')
                or os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
            )
        self.client: Optional[Client] = None
        self._initialize_client()

    def _initialize_client(self):
        """Initializes the Supabase client if credentials and package are available."""
        if not SUPABASE_INSTALLED:
            return
        if self.url and self.key:
            try:
                self.client = create_client(self.url, self.key)
            except Exception as e:
                # Log without crashing
                print(f"[Supabase] Notice: Client initialization failed ({e}). Running in offline mode.")
                self.client = None

    @property
    def is_available(self) -> bool:
        """Returns True if Supabase is installed, configured, and initialized."""
        return self.client is not None

    def check_connection(self) -> Dict[str, Any]:
        """
        Performs a health check and table discovery test against the Supabase project.
        Returns a diagnostic status dictionary without exposing secret keys.
        """
        if not self.is_available:
            return {
                'connected': False,
                'status': 'offline_or_unconfigured',
                'url': self.url or 'Not configured',
                'tables': {}
            }

        tables_to_check = [
            'simulated_scenarios',
            'scenario_comparisons',
            'evaluation_predictions',
            'run_history'
        ]
        table_statuses = {}
        for tbl in tables_to_check:
            try:
                res = self.client.table(tbl).select('*').limit(1).execute()
                table_statuses[tbl] = {'exists': True, 'accessible': True}
            except Exception as e:
                msg = str(e)
                if '42501' in msg or 'security policy' in msg.lower():
                    table_statuses[tbl] = {'exists': True, 'accessible': 'rls_restricted'}
                else:
                    table_statuses[tbl] = {'exists': False, 'error': msg}

        return {
            'connected': True,
            'status': 'active',
            'url': self.url,
            'tables': table_statuses
        }

    def save_scenario_result(
        self,
        scenario_result: Any,
        request_id: str,
        user_id: Optional[str] = None,
        table_name: str = 'simulated_scenarios'
    ) -> bool:
        """
        Saves a single what-if scenario result to Supabase.
        Returns True if successfully written, False if offline or unconfigured.
        """
        if not self.is_available:
            return False

        try:
            earliest = scenario_result.earliest_date_for_full_payment
            if not earliest or str(earliest).strip().lower() in ('none', 'nan', ''):
                earliest = None

            record = {
                'request_id': request_id,
                'user_id': user_id or 'unknown',
                'purchase_amount': float(scenario_result.purchase_amount),
                'payment_method': str(scenario_result.payment_method),
                'affordability_status': str(scenario_result.affordability_status),
                'amount_safe_to_pay': float(scenario_result.amount_safe_to_pay),
                'payment_plan': str(scenario_result.payment_plan),
                'earliest_date_for_full_payment': earliest,
                'spending_changes_needed': str(scenario_result.spending_changes_needed),
                'minimum_projected_balance': float(scenario_result.minimum_projected_balance),
                'decision_explanation': str(scenario_result.decision_explanation),
                'is_safe': bool(scenario_result.is_safe),
                'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            self.client.table(table_name).insert(record).execute()
            return True
        except Exception as e:
            print(f"[Supabase] Notice: Could not save scenario ({e}).")
            return False

    def save_scenario_comparison(
        self,
        comparison: Any,
        request_id: str,
        user_id: Optional[str] = None,
        table_name: str = 'scenario_comparisons'
    ) -> bool:
        """
        Persists a multi-scenario comparison batch and best recommendation.
        """
        if not self.is_available:
            return False

        try:
            best = comparison.best_scenario
            record = {
                'request_id': request_id,
                'user_id': user_id or 'unknown',
                'scenarios_count': len(comparison.scenarios),
                'best_scenario_label': best.scenario_label if best else None,
                'best_payment_method': best.payment_method if best else None,
                'best_affordability_status': best.affordability_status if best else None,
                'summary': comparison.comparison_summary,
                'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            self.client.table(table_name).insert(record).execute()

            # Also persist individual scenarios
            for s in comparison.scenarios:
                self.save_scenario_result(s, request_id, user_id)

            return True
        except Exception as e:
            print(f"[Supabase] Notice: Could not save comparison ({e}).")
            return False

    def sync_predictions(
        self,
        df_output: pd.DataFrame,
        table_name: str = 'evaluation_predictions',
        batch_size: int = 50
    ) -> int:
        """
        Syncs output.csv predictions into a Supabase table.
        Returns count of synced rows (0 if offline or unconfigured).
        """
        if not self.is_available:
            return 0

        synced_count = 0
        try:
            records = []
            for _, row in df_output.iterrows():
                row_dict = {}
                for col in df_output.columns:
                    val = row[col]
                    if col == 'earliest_date_for_full_payment':
                        if pd.isna(val) or val is None or str(val).strip().lower() in ('nan', 'none', ''):
                            row_dict[col] = None
                        else:
                            row_dict[col] = str(val).strip()
                    elif pd.isna(val) or val is None:
                        row_dict[col] = ''
                    elif isinstance(val, (int, float)):
                        row_dict[col] = float(val)
                    else:
                        row_dict[col] = str(val)
                records.append(row_dict)

            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                self.client.table(table_name).upsert(batch).execute()
                synced_count += len(batch)
            return synced_count
        except Exception as e:
            print(f"[Supabase] Notice: Sync predictions failed ({e}).")
            return synced_count

    def log_run(
        self,
        run_name: str,
        total_requests: int,
        metrics: Optional[Dict[str, Any]] = None,
        table_name: str = 'run_history'
    ) -> bool:
        """
        Logs a pipeline execution run and summary metrics to Supabase.
        """
        if not self.is_available:
            return False

        try:
            payload = {
                'run_name': run_name,
                'total_requests': total_requests,
                'metrics': metrics or {},
                'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            self.client.table(table_name).insert(payload).execute()
            return True
        except Exception as e:
            print(f"[Supabase] Notice: Log run failed ({e}).")
            return False


# Module-level singleton instance & helper factory functions
_default_adapter: Optional[SupabaseAdapter] = None


def get_supabase_adapter() -> SupabaseAdapter:
    """Returns the singleton SupabaseAdapter instance."""
    global _default_adapter
    if _default_adapter is None:
        _default_adapter = SupabaseAdapter()
    return _default_adapter


def get_supabase_client(
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None
) -> Optional[Client]:
    """
    Returns the initialized Supabase client directly, or None if offline/unconfigured.
    Reads SUPABASE_URL and SUPABASE_ANON_KEY from .env if arguments are omitted.
    """
    if supabase_url or supabase_key:
        adapter = SupabaseAdapter(supabase_url=supabase_url, supabase_key=supabase_key)
        return adapter.client
    return get_supabase_adapter().client
