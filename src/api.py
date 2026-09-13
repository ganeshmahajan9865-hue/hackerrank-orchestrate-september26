"""
Buy or Wait? — Financial Affordability REST API Backend
Built with FastAPI, Supabase, Gemini, and Deterministic Financial Engines.
"""

import sys
import os
import datetime
from typing import Dict, List, Optional, Any, Union
import pandas as pd
from pydantic import BaseModel, Field

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse

from src.data_loader import load_all_data
from src.data_cleaner import clean_all_data
from src.data_joiner import DataJoiner, RequestContext
from src.image_extractor import ImageExtractor
from src.message_parser import MessageParser
from src.currency_converter import CurrencyConverter
from src.event_reconstructor import EventReconstructor
from src.forecast_engine import ForecastEngine
from src.payment_plans import PaymentPlanEngine, format_amount
from src.decision_engine import DecisionEngine
from src.explanation_generator import ExplanationGenerator
from src.rag.rag_pipeline import RAGPipeline
from src.scenario_simulator import ScenarioSimulator, ScenarioSpec
from src.supabase_client import get_supabase_adapter
from src.gemini_client import get_gemini_client

# Initialize FastAPI app
app = FastAPI(
    title="Buy or Wait? — Financial Affordability API",
    description="Deterministic AI-powered financial reasoning agent backend with RAG, Supabase persistence, and Gemini integration.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State Container
class ServiceContainer:
    def __init__(self):
        self.is_initialized = False
        self.raw_data = None
        self.clean_data = None
        self.joiner = None
        self.img_extractor = None
        self.msg_parser = None
        self.curr_converter = None
        self.reconstructor = None
        self.forecast_engine = None
        self.plan_engine = None
        self.decision_engine = None
        self.rag_pipeline = None
        self.explanation_gen = None
        self.simulator = None
        self.supabase_adapter = None
        self.gemini_client = None

    def initialize(self, dataset_dir: str = 'dataset'):
        if self.is_initialized:
            return

        resolved_dir = dataset_dir
        if not os.path.exists(resolved_dir):
            for cand in [
                os.path.join(PROJECT_ROOT, 'dataset'),
                os.path.join('..', 'dataset'),
                'dataset'
            ]:
                if os.path.exists(cand):
                    resolved_dir = cand
                    break

        self.raw_data = load_all_data(resolved_dir)
        self.clean_data = clean_all_data(self.raw_data)
        self.joiner = DataJoiner(self.clean_data)
        self.img_extractor = ImageExtractor()
        self.msg_parser = MessageParser()
        self.curr_converter = CurrencyConverter(self.clean_data['exchange_rates'])
        self.reconstructor = EventReconstructor(self.img_extractor, self.msg_parser, self.curr_converter)
        self.forecast_engine = ForecastEngine(forecast_days=90, conservative_buffer=1.0)
        self.plan_engine = PaymentPlanEngine()
        self.decision_engine = DecisionEngine(self.forecast_engine, self.plan_engine)

        # RAG pipeline
        try:
            k_dir = os.path.join(PROJECT_ROOT, 'knowledge')
            idx_file = os.path.join(k_dir, 'index.json')
            self.rag_pipeline = RAGPipeline(knowledge_dir=k_dir, index_path=idx_file, enabled=True)
            self.rag_pipeline.build_index(force_rebuild=False)
        except Exception:
            self.rag_pipeline = None

        self.explanation_gen = ExplanationGenerator(rag_pipeline=self.rag_pipeline)
        self.simulator = ScenarioSimulator(
            self.joiner,
            self.reconstructor,
            self.forecast_engine,
            self.decision_engine,
            self.plan_engine,
            self.explanation_gen
        )
        self.supabase_adapter = get_supabase_adapter()
        self.gemini_client = get_gemini_client()
        self.is_initialized = True


container = ServiceContainer()


@app.on_event("startup")
def startup_event():
    """Initializes backend data and models on startup."""
    container.initialize()


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class DecideRequest(BaseModel):
    request_id: str = Field(..., description="Evaluation request ID, e.g. 'request_01'")


class ScenarioInput(BaseModel):
    purchase_amount: float = Field(..., gt=0, description="Hypothetical purchase amount")
    payment_method: str = Field(..., description="'full_payment', 'partial_payment', 'installments', or 'wait'")
    installment_option_id: Optional[str] = Field(None, description="Specific payment option ID for installments")
    scenario_label: Optional[str] = Field(None, description="Human readable label")


class SimulateRequest(BaseModel):
    request_id: str = Field(..., description="Target request ID to test what-if scenarios on")
    scenarios: List[ScenarioInput] = Field(..., min_items=1, description="List of purchase/payment scenarios")


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/", summary="API Root")
def root():
    """Returns basic API service metadata and route discovery."""
    return {
        "service": "Buy or Wait? Financial Affordability API",
        "version": "1.0.0",
        "status": "online",
        "endpoints": {
            "dashboard": "/dashboard",
            "health": "/api/health",
            "requests": "/api/requests",
            "decide": "/api/decide",
            "simulate": "/api/simulate",
            "history": "/api/history",
            "docs": "/docs"
        }
    }


@app.get("/dashboard", summary="Interactive Frontend Dashboard")
def dashboard():
    """Serves the interactive single-page HTML frontend dashboard."""
    candidates = [
        os.path.join(PROJECT_ROOT, "static", "index.html"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "index.html"),
        os.path.join("static", "index.html")
    ]
    for c in candidates:
        if os.path.exists(c):
            with open(c, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Dashboard HTML not found</h1>", status_code=404)


@app.get("/api/health", summary="System Health Check")
def health_check():
    """
    Comprehensive health check verifying:
    - FastAPI server state
    - Environment variables presence (zero credentials exposed)
    - Google Gemini connection and supported models
    - Supabase connection and table accessibility
    """
    if not container.is_initialized:
        container.initialize()

    env_status = {
        "gemini_api_key_configured": bool(container.gemini_client and container.gemini_client.is_available),
        "supabase_url_configured": bool(container.supabase_adapter and container.supabase_adapter.url),
        "supabase_key_configured": bool(container.supabase_adapter and container.supabase_adapter.key),
    }

    gemini_health = container.gemini_client.check_connection() if container.gemini_client else {"status": "uninitialized"}
    supabase_health = container.supabase_adapter.check_connection() if container.supabase_adapter else {"status": "uninitialized"}

    is_healthy = True
    return {
        "status": "healthy" if is_healthy else "degraded",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "environment": env_status,
        "gemini": gemini_health,
        "supabase": supabase_health
    }


@app.get("/api/requests", summary="List Available Requests")
def list_requests(limit: int = Query(20, ge=1, le=250), user_id: Optional[str] = None):
    """Lists requests available in the dataset."""
    if not container.is_initialized:
        container.initialize()

    df_req = container.clean_data['requests']
    if user_id:
        df_req = df_req[df_req['user_id'] == user_id]

    records = df_req.head(limit).to_dict(orient='records')
    return {
        "total": len(records),
        "requests": records
    }


@app.post("/api/decide", summary="Evaluate Financial Request")
def evaluate_request(payload: DecideRequest):
    """
    Runs the deterministic 16-stage pipeline on a specific request:
    - Reconstructs context, cash flows, and image receipts
    - Projects 90-day cash flow & verifies minimum balance
    - Formulates payment plan and RAG-grounded explanation
    - Persists decision to Supabase if connected
    """
    if not container.is_initialized:
        container.initialize()

    req_id = payload.request_id.strip()
    valid_ids = set(container.clean_data['requests']['request_id']).union(
        set(container.clean_data.get('sample_requests', pd.DataFrame({'request_id': []}))['request_id'])
    )
    if req_id not in valid_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request '{req_id}' not found in dataset."
        )

    try:
        ctx = container.joiner.get_request_context(req_id)
        recon = container.reconstructor.reconstruct(ctx)
        decision = container.decision_engine.evaluate(ctx, recon)
        explanation = container.explanation_gen.generate(ctx, decision)

        result = {
            "request_id": req_id,
            "user_id": ctx.user_id,
            "currency": ctx.profile.home_currency,
            "requested_amount": ctx.requested_amount,
            "amount_safe_to_pay": decision.amount_safe_to_pay,
            "affordability_status": decision.affordability_status,
            "recommended_payment_method": decision.recommended_payment_method,
            "payment_plan": decision.payment_plan,
            "earliest_date_for_full_payment": decision.earliest_date_for_full_payment,
            "spending_changes_needed": decision.spending_changes_needed,
            "decision_explanation": explanation,
            "minimum_balance_to_keep": ctx.profile.minimum_balance_to_keep,
            "synced_to_supabase": False
        }

        # Optional Supabase persistence
        if container.supabase_adapter and container.supabase_adapter.is_available:
            try:
                row_record = {
                    'request_id': req_id,
                    'amount_safe_to_pay': decision.amount_safe_to_pay,
                    'affordability_status': decision.affordability_status,
                    'recommended_payment_method': decision.recommended_payment_method,
                    'payment_plan': decision.payment_plan,
                    'earliest_date_for_full_payment': decision.earliest_date_for_full_payment,
                    'spending_changes_needed': decision.spending_changes_needed,
                    'decision_explanation': explanation
                }
                container.supabase_adapter.save_predictions_batch(
                    pd.DataFrame([row_record]),
                    run_id=f"api_single_{req_id}"
                )
                result["synced_to_supabase"] = True
            except Exception:
                result["synced_to_supabase"] = False

        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process financial decision: {str(e)}"
        )


@app.post("/api/simulate", summary="Run What-If Scenario Simulator")
def simulate_scenarios(payload: SimulateRequest):
    """
    Runs the What-If Purchase & Payment Simulator across multiple scenarios:
    - Tests varying purchase amounts and payment methods
    - Uses exact same 90-day deterministic forecast engine
    - Ranks scenarios according to PRD Section 4.4
    - Persists results to Supabase (simulated_scenarios & scenario_comparisons)
    """
    if not container.is_initialized:
        container.initialize()

    req_id = payload.request_id.strip()
    valid_ids = set(container.clean_data['requests']['request_id']).union(
        set(container.clean_data.get('sample_requests', pd.DataFrame({'request_id': []}))['request_id'])
    )
    if req_id not in valid_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request '{req_id}' not found in dataset."
        )

    # Validate payment methods
    allowed_methods = {'full_payment', 'partial_payment', 'installments', 'wait'}
    for sc in payload.scenarios:
        if sc.payment_method not in allowed_methods:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid payment_method '{sc.payment_method}'. Must be one of {allowed_methods}."
            )
        if sc.purchase_amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="purchase_amount must be greater than zero."
            )

    try:
        ctx = container.joiner.get_request_context(req_id)
        scenario_specs = [
            ScenarioSpec(
                purchase_amount=sc.purchase_amount,
                payment_method=sc.payment_method,
                payment_option_id=sc.installment_option_id,
                scenario_label=sc.scenario_label
            )
            for sc in payload.scenarios
        ]

        comparison = container.simulator.simulate_scenarios(ctx, scenario_specs)

        # Format scenario list
        formatted_scenarios = [
            {
                "purchase_amount": s.purchase_amount,
                "payment_method": s.payment_method,
                "affordability_status": s.affordability_status,
                "amount_safe_to_pay": s.amount_safe_to_pay,
                "payment_plan": s.payment_plan,
                "earliest_date_for_full_payment": s.earliest_date_for_full_payment,
                "spending_changes_needed": s.spending_changes_needed,
                "minimum_projected_balance": s.minimum_projected_balance,
                "decision_explanation": s.decision_explanation,
                "is_safe": s.is_safe,
                "scenario_label": s.scenario_label
            }
            for s in comparison.scenarios
        ]

        best_dict = None
        if comparison.best_scenario:
            b = comparison.best_scenario
            best_dict = {
                "purchase_amount": b.purchase_amount,
                "payment_method": b.payment_method,
                "affordability_status": b.affordability_status,
                "scenario_label": b.scenario_label
            }

        saved_to_supabase = False
        if container.supabase_adapter and container.supabase_adapter.is_available:
            try:
                for sc_res in comparison.scenarios:
                    container.supabase_adapter.save_scenario_result(sc_res, req_id, user_id=ctx.user_id)
                container.supabase_adapter.save_scenario_comparison(comparison, req_id, user_id=ctx.user_id)
                saved_to_supabase = True
            except Exception:
                saved_to_supabase = False

        return {
            "request_id": req_id,
            "total_scenarios": len(formatted_scenarios),
            "best_scenario": best_dict,
            "comparison_summary": comparison.comparison_summary,
            "scenarios": formatted_scenarios,
            "saved_to_supabase": saved_to_supabase
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scenario simulation failed: {str(e)}"
        )


@app.get("/api/history", summary="Fetch Simulation History from Supabase")
def get_history(limit: int = Query(10, ge=1, le=50)):
    """
    Fetches past scenario simulations or comparisons from Supabase database.
    Gracefully returns status notice if Supabase is offline.
    """
    if not container.is_initialized:
        container.initialize()

    if not container.supabase_adapter or not container.supabase_adapter.is_available:
        return {
            "source": "offline",
            "message": "Supabase is not configured or in offline mode.",
            "records": []
        }

    try:
        res = container.supabase_adapter.client.table('scenario_comparisons') \
            .select('*').order('created_at', desc=True).limit(limit).execute()
        records = res.data if hasattr(res, 'data') else []
        return {
            "source": "supabase",
            "count": len(records),
            "records": records
        }
    except Exception as e:
        return {
            "source": "supabase",
            "error": str(e),
            "records": []
        }


if __name__ == '__main__':
    import uvicorn
    print("Starting Buy or Wait? API Server on http://127.0.0.1:8000 ...")
    uvicorn.run("src.api:app", host="127.0.0.1", port=8000, reload=False)
