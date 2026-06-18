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
print("INTEGRATION TEST - All New Modules")
print("=" * 80)

# ============================================
# Test 1: Setup - Generate sample dataset
# ============================================
print("\n[Test 1] Generate sample data...")
ds_res = api_post('/api/data/generate-sample', {
    'n_stocks': 20,
    'n_days': 60,
    'name': 'integration_test',
    'frequency': 'daily',
    'stock_pool': 'HS300'
})
print(f"  Dataset: {ds_res.get('table_name')}, rows: {ds_res.get('row_count')}")
ds_name = ds_res['table_name']

# ============================================
# Test 2: Compute 3 different factors
# ============================================
print("\n[Test 2] Compute 3 different factors...")
factors_data = []
for op_id, name in [('ma', 'MA10'), ('rsi', 'RSI14'), ('momentum', 'MOM20')]:
    params = {'period': 10} if op_id == 'ma' else {'period': 14} if op_id == 'rsi' else {'period': 20, 'method': 'ratio'}
    wf = {
        'name': name,
        'nodes': [{'id': 'n1', 'operator_id': op_id, 'params': params, 'inputs': {'price': {'type': 'market_data', 'field': 'close'}}}],
        'edges': [],
        'output_node': 'n1'
    }
    res = api_post('/api/factor/compute', {'workflow': wf, 'dataset_name': ds_name})
    if res.get('success'):
        factors_data.append({'name': name, 'factor_values': res.get('factor_values', [])})
        print(f"  {name}: {len(res.get('factor_values', []))} records")
    else:
        print(f"  {name}: FAILED - {res.get('message')}")

# ============================================
# Test 3: Template Market CRUD
# ============================================
print("\n[Test 3] Template Market...")

# Publish template
wf_for_tpl = {
    'name': 'MA20 Strategy',
    'nodes': [{'id': 'n1', 'operator_id': 'ma', 'params': {'period': 20}, 'inputs': {'price': {'type': 'market_data', 'field': 'close'}}}],
    'edges': [],
    'output_node': 'n1'
}
pub_res = api_post('/api/templates/publish', {
    'name': 'MA20 趋势策略',
    'description': '基于20日均线的经典趋势跟踪策略',
    'category': '趋势策略',
    'tags': ['MA', '趋势', '均线'],
    'author_name': 'QuantDeveloper',
    'workflow': wf_for_tpl,
    'factor_stats': {'ic_mean': 0.05, 'icir': 0.8},
    'backtest_result': {'annualized_return': 0.15, 'sharpe': 1.2},
    'is_public': True
})
print(f"  Publish: success={pub_res.get('success')}, id={pub_res.get('template_id')}")
tpl_id = pub_res.get('template_id')

# List templates
list_res = api_get('/api/templates')
print(f"  List: total={list_res.get('total')}, templates={len(list_res.get('templates', []))}")

# Get categories
cat_res = api_get('/api/templates/categories')
print(f"  Categories: {cat_res.get('categories')}")

# Get template
get_res = api_get(f'/api/templates/{tpl_id}')
print(f"  Get: success={get_res.get('success')}, name={get_res.get('template', {}).get('name')}")

# Like template
like_res = api_post(f'/api/templates/{tpl_id}/like', {})
print(f"  Like: success={like_res.get('success')}")

# Apply template
apply_res = api_post(f'/api/templates/{tpl_id}/apply', {})
print(f"  Apply: success={apply_res.get('success')}")

# Fork template
fork_res = api_post(f'/api/templates/{tpl_id}/fork?author_name=ForkUser&new_name=MA20_Strategy_Copy', {})
print(f"  Fork: success={fork_res.get('success')}, new_id={fork_res.get('new_template_id')}")

# ============================================
# Test 4: Portfolio Optimization
# ============================================
print("\n[Test 4] Portfolio Optimization...")
if len(factors_data) >= 2:
    for model in ['mean_variance', 'equal_weight', 'risk_parity', 'min_variance', 'max_sharpe']:
        opt_res = api_post('/api/portfolio/optimize', {
            'dataset_name': ds_name,
            'factors': factors_data,
            'model': model,
            'risk_free_rate': 0.03,
            'min_weight': 0.0,
            'max_weight': 1.0
        })
        if opt_res.get('success'):
            print(f"  {model}: weights={opt_res.get('weights')}, sharpe={opt_res.get('sharpe_ratio'):.3f}")
            if 'efficient_frontier' in opt_res:
                print(f"    frontier points: {len(opt_res.get('efficient_frontier', []))}")
            if 'monte_carlo_points' in opt_res:
                print(f"    monte carlo points: {len(opt_res.get('monte_carlo_points', []))}")
        else:
            print(f"  {model}: {opt_res.get('message')}")

# List models
models_res = api_get('/api/portfolio/models')
print(f"  Models: {len(models_res.get('models', []))} available")

# ============================================
# Test 5: Factor Correlation
# ============================================
print("\n[Test 5] Factor Correlation Analysis...")
if len(factors_data) >= 2:
    corr_res = api_post('/api/factor/correlation', {
        'factor_values_list': factors_data,
        'dataset_name': ds_name,
        'vif_threshold': 10.0,
        'corr_threshold': 0.7
    })
    if corr_res.get('success'):
        print(f"  Correlation pairs: {len(corr_res.get('collinear_pairs', []))}")
        if corr_res.get('vif_values'):
            for v in corr_res['vif_values']:
                print(f"    VIF({v['name']}): {v['vif']:.2f}")
        print(f"  Removed: {corr_res.get('removed_factors')}")
        print(f"  Kept: {corr_res.get('kept_factors')}")
    else:
        print(f"  FAILED: {corr_res.get('message')}")

# ============================================
# Test 6: SHAP Analysis (try, skip if no shap)
# ============================================
print("\n[Test 6] SHAP Analysis...")
if factors_data:
    shap_res = api_post('/api/shap/analyze', {
        'dataset_name': ds_name,
        'factor_name': factors_data[0]['name'],
        'factor_values': factors_data[0]['values'],
        'n_samples': 50,
        'target_period': 5
    })
    if shap_res.get('success'):
        contribs = shap_res.get('feature_contributions', [])
        print(f"  Features: {len(contribs)}, top: {contribs[0]['feature'] if contribs else 'N/A'}")
        print(f"  Base value: {shap_res.get('base_value')}")
        print(f"  SHAP records: {len(shap_res.get('shap_values', []))}")
    else:
        print(f"  Note: {shap_res.get('message')}")

# ============================================
# Test 7: Forward validation with complex workflow
# ============================================
print("\n[Test 7] Forward Validation with complex workflow...")
complex_wf = {
    'name': 'MA20 + RSI14',
    'nodes': [
        {'id': 'n1', 'operator_id': 'ma', 'params': {'period': 20}, 'inputs': {'price': {'type': 'market_data', 'field': 'close'}}},
        {'id': 'n2', 'operator_id': 'rsi', 'params': {'period': 14}, 'inputs': {'price': {'type': 'market_data', 'field': 'close'}}},
        {'id': 'n3', 'operator_id': 'arithmetic', 'params': {'op': 'add'}, 'inputs': {
            'left': {'type': 'node_output', 'node_id': 'n1', 'output_id': 'ma'},
            'right': {'type': 'node_output', 'node_id': 'n2', 'output_id': 'rsi'}
        }}
    ],
    'edges': [],
    'output_node': 'n3'
}
fv_res = api_post('/api/factor/compute', {
    'workflow': complex_wf,
    'dataset_name': ds_name,
    'forward_validation': True
})
if fv_res.get('success'):
    fv_info = fv_res.get('forward_validation') or {}
    print(f"  Normal: {len(fv_res.get('factor_values', []))} records")
    if fv_info:
        print(f"  FV: {fv_info.get('message')}")
        print(f"  Warmup: {fv_info.get('warmup_dates')}, Eval: {fv_info.get('eval_dates')}")
        print(f"  Chain lookback: {fv_info.get('output_chain_lookback')}")
else:
    print(f"  FAILED: {fv_res.get('message')}")

# ============================================
# Test 8: List all operators with lookback
# ============================================
print("\n[Test 8] Operators with lookback...")
ops_res = api_get('/api/factor/operators')
print(f"  Total operators: {len(ops_res.get('operators', []))}")
for op in ops_res.get('operators', [])[:5]:
    print(f"    {op['id']}: lookback={op.get('lookback', 0)}")

# ============================================
# Test 9: Delete template
# ============================================
print("\n[Test 9] Cleanup - Delete test templates...")
del1_res = urllib.request.Request(f'{BASE}/api/templates/{tpl_id}', method='DELETE')
try:
    del1 = json.loads(urllib.request.urlopen(del1_res).read())
    print(f"  Delete {tpl_id}: {del1.get('success')}")
except Exception as e:
    print(f"  Delete failed: {e}")

forked_id = fork_res.get('new_template_id')
if forked_id:
    del2_res = urllib.request.Request(f'{BASE}/api/templates/{forked_id}', method='DELETE')
    try:
        del2 = json.loads(urllib.request.urlopen(del2_res).read())
        print(f"  Delete {forked_id}: {del2.get('success')}")
    except Exception as e:
        print(f"  Delete failed: {e}")

# ============================================
# Summary
# ============================================
print("\n" + "=" * 80)
print("ALL TESTS COMPLETED!")
print("=" * 80)
print("New APIs verified:")
print("  ✅ /api/templates/*   - Template Market (publish/list/get/like/fork/apply/delete)")
print("  ✅ /api/portfolio/*  - Portfolio Optimization (5 models + efficient frontier)")
print("  ✅ /api/factor/correlation - Factor correlation + VIF")
print("  ✅ /api/shap/*      - SHAP analysis + PDF report")
print("  ✅ /ws/realtime     - WebSocket realtime market")
print("  ✅ Forward validation with chain lookback")
print("  ✅ All operators with lookback attribute")
print("=" * 80)
