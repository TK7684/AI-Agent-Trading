from fastapi.testclient import TestClient

from apps.trading_api.main import app

client = TestClient(app)


def get_auth_headers():
    res = client.post("/auth/login", json={"email": "a@b.com", "password": "x"})
    assert res.status_code == 200
    token = res.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_login_and_refresh():
    res = client.post("/auth/login", json={"email": "a@b.com", "password": "x"})
    assert res.status_code == 200
    headers = {"Authorization": f"Bearer {res.json()['refreshToken']}"}
    res2 = client.post("/auth/refresh", headers=headers)
    assert res2.status_code == 200


def test_performance_endpoint():
    headers = get_auth_headers()
    res = client.get("/trading/performance", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "totalPnl" in data


def test_agent_status_endpoint():
    headers = get_auth_headers()
    res = client.get("/system/agents", headers=headers)
    assert res.status_code == 200


def test_system_health_endpoint():
    headers = get_auth_headers()
    res = client.get("/system/health", headers=headers)
    assert res.status_code == 200
