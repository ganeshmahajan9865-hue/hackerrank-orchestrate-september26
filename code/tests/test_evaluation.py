"""
Unit Tests for Evaluation Workflow — Buy or Wait?
"""

import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from evaluation.evaluate_samples import SampleEvaluator


def test_evaluator_initialization():
    """Verifies that SampleEvaluator initializes and finds dataset."""
    evaluator = SampleEvaluator(data_dir='dataset', use_rag=False)
    assert os.path.exists(evaluator.samples_path)


def test_sample_evaluation_execution():
    """Verifies that running sample evaluation produces valid metrics dictionary."""
    evaluator = SampleEvaluator(data_dir='dataset', use_rag=False)
    metrics = evaluator.run_evaluation(verbose=False)
    
    assert 'total_samples' in metrics
    assert metrics['total_samples'] == 25
    assert 'status_accuracy' in metrics
    assert 'method_accuracy' in metrics
    assert 'safe_amount_mae' in metrics
    assert 'results' in metrics
    assert len(metrics['results']) == 25
