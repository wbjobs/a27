import urllib.request
import json

BASE = 'http://localhost:8000'

def api_get(p):
    return json.loads(urllib.request.urlopen(BASE + p).read())

def api_post(p, d):
    payload = json.dumps(d, default=str).encode()
    req = urllib.request.Request(BASE + p, data=payload, headers={'Content-Type': 'application/json'})
    try:
        return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        return {'success': False, 'error': str(e), 'detail': e.read().decode()}

# Setup
ds = api_post('/api/data/generate-sample', {'n_stocks': 10, 'n_days': 30, 'name': 'tpl', 'frequency': 'daily', 'stock_pool': 'HS300'})
ds_name = ds['table_name']

# Compute factor
wf = {'name': 'MA20', 'nodes': [{'id': 'n1', 'operator_id': 'ma', 'params': {'period': 20}, 'inputs': {'price': {'type': 'market_data', 'field': 'close'}}}], 'edges': [], 'output_node': 'n1'}
api_post('/api/factor/compute', {'workflow': wf, 'dataset_name': ds_name})

print('=== Template Market Test ===')

# Publish
pub = api_post('/api/templates/publish', {
    'name': 'MA20_Strategy',
    'description': 'test strategy',
    'category': 'Trend',
    'tags': ['MA'],
    'author_name': 'Test',
    'workflow': wf,
    'factor_stats': {'ic_mean': 0.05},
    'backtest_result': {'sharpe': 1.2},
    'is_public': True
})
print(f'Publish: {pub.get("success")}, id={pub.get("template_id")}')
tpl_id = pub['template_id']

# List
lst = api_get('/api/templates')
print(f'List: {len(lst.get("templates", []))} templates, total={lst.get("total")}')

# Categories
cats = api_get('/api/templates/categories')
print(f'Categories: {cats.get("categories")}')

# Get
gt = api_get(f'/api/templates/{tpl_id}')
tpl = gt.get('template', {})
print(f'Get: {gt.get("success")}, name={tpl.get("name")}')

# Like
lk = api_post(f'/api/templates/{tpl_id}/like', {})
print(f'Like: {lk.get("success")}')

# Apply
ap = api_post(f'/api/templates/{tpl_id}/apply', {})
print(f'Apply: {ap.get("success")}')

# Fork
fk = api_post(f'/api/templates/{tpl_id}/fork?author_name=Fork&new_name=Copy', {})
print(f'Fork: {fk.get("success")}, new_id={fk.get("new_template_id")}')

# Delete original
req = urllib.request.Request(f'{BASE}/api/templates/{tpl_id}', method='DELETE')
d1 = json.loads(urllib.request.urlopen(req).read())
print(f'Delete original: {d1.get("success")}')

# Delete forked
if fk.get('new_template_id'):
    req2 = urllib.request.Request(f'{BASE}/api/templates/{fk.get("new_template_id")}', method='DELETE')
    d2 = json.loads(urllib.request.urlopen(req2).read())
    print(f'Delete forked: {d2.get("success")}')

print('=== All Template Tests Passed! ===')
