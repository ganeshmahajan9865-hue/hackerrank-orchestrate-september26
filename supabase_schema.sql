-- Supabase Schema for Buy or Wait? Financial Affordability System
-- Run this script in the Supabase SQL Editor if you wish to enable cloud persistence.

-- 1. Simulated Scenarios Table (What-If Simulator)
CREATE TABLE IF NOT EXISTS simulated_scenarios (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    request_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    purchase_amount NUMERIC(12, 2) NOT NULL,
    payment_method TEXT NOT NULL,
    affordability_status TEXT NOT NULL,
    amount_safe_to_pay NUMERIC(12, 2) NOT NULL,
    payment_plan TEXT NOT NULL,
    earliest_date_for_full_payment DATE,
    spending_changes_needed TEXT,
    minimum_projected_balance NUMERIC(12, 2),
    decision_explanation TEXT,
    is_safe BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Scenario Comparisons Table
CREATE TABLE IF NOT EXISTS scenario_comparisons (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    request_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    scenarios_count INT NOT NULL,
    best_scenario_label TEXT,
    best_payment_method TEXT,
    best_affordability_status TEXT,
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Evaluation Predictions Table (output.csv sync)
CREATE TABLE IF NOT EXISTS evaluation_predictions (
    request_id TEXT PRIMARY KEY,
    amount_safe_to_pay NUMERIC(12, 2) NOT NULL,
    affordability_status TEXT NOT NULL,
    recommended_payment_method TEXT NOT NULL,
    payment_plan TEXT NOT NULL,
    earliest_date_for_full_payment DATE,
    spending_changes_needed TEXT,
    decision_explanation TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Pipeline Run History Table
CREATE TABLE IF NOT EXISTS run_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_name TEXT NOT NULL,
    total_requests INT NOT NULL,
    metrics JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast querying
CREATE INDEX IF NOT EXISTS idx_sim_request_id ON simulated_scenarios(request_id);
CREATE INDEX IF NOT EXISTS idx_sim_user_id ON simulated_scenarios(user_id);
CREATE INDEX IF NOT EXISTS idx_comp_request_id ON scenario_comparisons(request_id);

-- 5. Row-Level Security (RLS) Permissions
-- Enable anon insert/read permissions for the tables:
ALTER TABLE simulated_scenarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE scenario_comparisons ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluation_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE run_history ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow anon all on simulated_scenarios" ON simulated_scenarios;
CREATE POLICY "Allow anon all on simulated_scenarios" ON simulated_scenarios FOR ALL TO anon USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow anon all on scenario_comparisons" ON scenario_comparisons;
CREATE POLICY "Allow anon all on scenario_comparisons" ON scenario_comparisons FOR ALL TO anon USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow anon all on evaluation_predictions" ON evaluation_predictions;
CREATE POLICY "Allow anon all on evaluation_predictions" ON evaluation_predictions FOR ALL TO anon USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow anon all on run_history" ON run_history;
CREATE POLICY "Allow anon all on run_history" ON run_history FOR ALL TO anon USING (true) WITH CHECK (true);

