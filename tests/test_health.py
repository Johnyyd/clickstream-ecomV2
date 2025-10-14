def test_health(client):
    resp = client.get('/api/health')
    assert resp.status_code == 200
    j = resp.json()
    assert j.get('status') == 'ok'
