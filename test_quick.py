import urllib.request
import json

BASE = 'http://localhost:8000'

def api_get(path):
    req = urllib.request.Request(f'{BASE}{path}')
    return json.loads(urllib.request.urlopen(req).read())

def api_post(path, data):
    payload = json.dumps(data, default=str).encode()
    req = urllib.request.Request(f'{BASE}{path}', data=payload, headers={'Content-Type': 'application/json'})
    try:
        return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        return {'success': False, 'error': str(e), 'detail': e.read().decode()[:500]}

print("=" * 80)
print("QUICK TEST - Portfolio & SHAP")
print("=" * 80)

# Setup
print("\n[Setup] Generate data and compute factors...")
ds_res = api_post('/api/data/generate-sample', {
    'n_stocks': 15, 'n_days': 40, 'name': 'quick_test',
    'frequency': 'daily', 'stock_pool': 'HS300'
})
ds_name = ds_res['table_name']
print(f"  Dataset: {ds_name}")

factors = []
for op_id, name, params in [
    ('ma', 'MA10', {'period': 10}),
    ('rsi', 'RSI14', {'period': 14}),
    ('momentum', 'MOM20', {'period': 20, 'method': 'ratio'})
]:
    wf = {
        'name': name,
        'nodes': [{'id': 'n1', 'operator_id': op_id, 'params': params, 'inputs': {'price': {'type': 'market_data', 'field': 'close'}}}],
        'edges': [], 'output_node': 'n1'
    }
    res = api_post('/api/factor/compute', {'workflow': wf, 'dataset_name': ds_name})
    factors.append({'name': name, 'factor_values': res.get('factor_values', [])})
    print(f"  {name}: {len(res.get('factor_values', []))} rows")

# Portfolio optimization - all 5 models
print("\n[1] Portfolio Optimization (5 models)...")
for model in ['mean_variance', 'equal_weight', 'risk_parity', 'min_variance', 'max_sharpe']:
    opt_res = api_post('/api/portfolio/optimize', {
        'dataset_name': ds_name,
        'factors': factors,
        'model': model,
        'risk_free_rate': 0.03,
        'min_weight': 0.0,
        'max_weight': 1.0
    })
    if opt_res.get('success'):
        w = opt_res.get('weights', {})
        print(f"  OK {model}: weights={w}")
        er = opt_res.get('expected_return', opt_res.get('expected_return'))
        ev = opt_res.get('expected_volatility', opt_res.get('expected_risk'))
        sr = opt_res.get('sharpe_ratio')
        er_str = f"{er:.4f}" if er is not None else "N/A"
        ev_str = f"{ev:.4f}" if ev is not None else "N/A"
        sr_str = f"{sr:.3f}" if sr is not None else "N/A"
        print(f"     return={er_str}, risk={ev_str}, sharpe={sr_str}")
        if 'efficient_frontier' in opt_res:
            print(f"     frontier: {len(opt_res.get('efficient_frontier', []))} points")
        if 'monte_carlo_points' in opt_res:
            print(f"     monte carlo: {len(opt_res.get('monte_carlo_points', []))} points")
    else:
        print(f"  FAIL {model}: {opt_res.get('message')}")

# Factor correlation
print("\n[2] Factor Correlation...")
corr_factors = [{'name': f['name'], 'values': f['factor_values']} for f in factors]
corr_res = api_post('/api/factor/correlation', {
    'factor_values_list': corr_factors,
    'dataset_name': ds_name,
    'vif_threshold': 10.0,
    'corr_threshold': 0.7
})
if corr_res.get('success'):
    print(f"  OK Correlation pairs: {len(corr_res.get('collinear_pairs', []))}")
    if corr_res.get('vif_values'):
        for v in corr_res['vif_values']:
            print(f"     VIF({v['name']}): {v['vif']:.2f}")
    print(f"  Removed: {corr_res.get('removed_factors')}, Kept: {corr_res.get('kept_factors')}")
else:
    print(f"  FAIL {corr_res.get('message')}")

# SHAP analysis
print("\n[3] SHAP Analysis...")
shap_res = api_post('/api/shap/analyze', {
    'dataset_name': ds_name,
    'factor_name': factors[0]['name'],
    'factor_values': factors[0]['factor_values'],
    'n_samples': 30,
    'target_period': 3
})
if shap_res.get('success'):
    contribs = shap_res.get('feature_contributions', [])
    print(f"  OK Features: {len(contribs)}")
    if contribs:
        imp = contribs[0].get('importance')
        imp_str = f"{imp:.4f}" if imp is not None else "N/A"
        print(f"     Top: {contribs[0].get('feature')} ({imp_str})")
    bv = shap_res.get('base_value')
    print(f"     Base value: {bv:.4f}" if bv is not None else "     Base value: N/A")
    print(f"     SHAP records: {len(shap_res.get('shap_values', []))}")
    if 'force_plot_data' in shap_res:
        print(f"     Force plot data: available")
else:
    print(f"  WARN {shap_res.get('message')}")

# List models
print("\n[4] Portfolio models list...")
models = api_get('/api/portfolio/models')
print(f"  OK Available: {len(models.get('models', []))} models")

# Forward validation
print("\n[5] Forward validation...")
fv_wf = {
    'name': 'MA20+RSI',
    'nodes': [
        {'id': 'n1', 'operator_id': 'ma', 'params': {'period': 20}, 'inputs': {'price': {'type': 'market_data', 'field': 'close'}}},
        {'id': 'n2', 'operator_id': 'rsi', 'params': {'period': 14}, 'inputs': {'price': {'type': 'market_data', 'field': 'close'}}},
        {'id': 'n3', 'operator_id': 'arithmetic', 'params': {'op': 'add'}, 'inputs': {
            'left': {'type': 'node_output', 'node_id': 'n1', 'output_id': 'ma'},
            'right': {'type': 'node_output', 'node_id': 'n2', 'output_id': 'rsi'}
        }}
    ],
    'edges': [], 'output_node': 'n3'
}
fv_res = api_post('/api/factor/compute', {
    'workflow': fv_wf,
    'dataset_name': ds_name,
    'forward_validation': True
})
if fv_res.get('success'):
    fv_info = fv_res.get('forward_validation') or {}
    print(f"  OK Normal records: {len(fv_res.get('factor_values', []))}")
    print(f"     Warmup: {fv_info.get('warmup_dates')}, Eval: {fv_info.get('eval_dates')}")
    print(f"     Chain lookback: {fv_info.get('output_chain_lookback')}")
else:
    print(f"  FAIL {fv_res.get('message')}")

print("\n" + "=" * 80)
print("QUICK TEST COMPLETE!")
print("=" * 80)
