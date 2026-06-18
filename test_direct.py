import sys
sys.path.insert(0, 'backend')

from app.core.portfolio_engine import portfolio_optimizer
from app.core.shap_engine import shap_analyzer
from app.core.duckdb_engine import DuckDBEngine
import json

db = DuckDBEngine()

# Generate test data
print("Generating test data...")
from app.core.data_generator import generate_sample_data
ds = generate_sample_data(n_stocks=10, n_days=30)
print(f"Dataset: {len(ds)} rows")

# Compute 3 simple factors
def compute_factor(op_id, params):
    from app.core.factor_engine import factor_engine
    from app.models.schemas import WorkflowDefinition, WorkflowNode
    
    wf = WorkflowDefinition(
        name="test",
        nodes=[WorkflowNode(id='n1', operator_id=op_id, params=params, inputs={'price': {'type': 'market_data', 'field': 'close'}})],
        edges=[],
        output_node='n1'
    )
    res = factor_engine.compute_factor(wf, 'sample_data_50stocks_252days')
    return res.get('factor_values', [])

factors = []
for op_id, name, params in [
    ('ma', 'MA10', {'period': 10}),
    ('rsi', 'RSI14', {'period': 14}),
    ('momentum', 'MOM20', {'period': 20, 'method': 'ratio'})
]:
    vals = compute_factor(op_id, params)
    factors.append({'name': name, 'factor_values': vals})
    print(f"  {name}: {len(vals)} rows")

# Test portfolio
print("\n--- Testing Portfolio ---")
try:
    result = portfolio_optimizer.optimize({
        "dataset_name": "sample_data_50stocks_252days",
        "factors": factors,
        "model": "equal_weight",
        "risk_free_rate": 0.03,
        "min_weight": 0.0,
        "max_weight": 1.0
    })
    print(f"Success! result keys: {list(result.keys())}")
    print(f"Weights: {result.get('weights')}")
except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()

# Test SHAP
print("\n--- Testing SHAP ---")
try:
    result = shap_analyzer.compute_shap(
        factor_name=factors[0]['name'],
        factor_values=factors[0]['factor_values'],
        dataset_name="sample_data_50stocks_252days",
        n_samples=20,
        target_period=3
    )
    print(f"Success! result keys: {list(result.keys())}")
except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
