import urllib.request
import urllib.error
import json

BASE = 'http://localhost:8000'

def api_post(path, data):
    payload = json.dumps(data, default=str).encode()
    req = urllib.request.Request(f'{BASE}{path}', data=payload, headers={'Content-Type': 'application/json'})
    try:
        return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        return {'success': False, 'error': str(e), 'detail': e.read().decode(), 'code': e.code}

# Setup
print("Setup...")
ds_res = api_post('/api/data/generate-sample', {
    'n_stocks': 10, 'n_days': 30, 'name': 'shap_test',
    'frequency': 'daily', 'stock_pool': 'HS300'
})
ds_name = ds_res['table_name']
print(f"  Dataset: {ds_name}")

# Compute one factor
print("\nCompute MA10...")
wf = {
    'name': 'MA10',
    'nodes': [{'id': 'n1', 'operator_id': 'ma', 'params': {'period': 10}, 'inputs': {'price': {'type': 'market_data', 'field': 'close'}}}],
    'edges': [], 'output_node': 'n1'
}
res = api_post('/api/factor/compute', {'workflow': wf, 'dataset_name': ds_name})
factor_values = res.get('factor_values', [])
print(f"  {len(factor_values)} rows")
print(f"  Sample row: {json.dumps(factor_values[0], indent=2) if factor_values else 'None'}")

# Try SHAP
print("\nSHAP analyze...")
shap_res = api_post('/api/shap/analyze', {
    'dataset_name': ds_name,
    'factor_name': 'MA10',
    'factor_values': factor_values,
    'n_samples': 20,
    'target_period': 3
})
print(json.dumps(shap_res, indent=2, default=str)[:2000])
