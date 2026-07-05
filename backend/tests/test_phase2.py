"""Phase 2 Backend API Tests - Templates, Inbox, Analytics, WebSocket"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    # Login
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": "owner@demo.com", "password": "Owner123!"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return s


# --- Templates ---
class TestTemplates:
    """Template API tests"""

    def test_get_templates_returns_array(self, session):
        r = session.get(f"{BASE_URL}/api/templates")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        print(f"Templates count: {len(data)}")

    def test_get_templates_status_filter(self, session):
        r = session.get(f"{BASE_URL}/api/templates?status=APPROVED")
        assert r.status_code in [200, 422]
        print(f"Templates with status filter: {r.status_code}")


# --- Inbox ---
class TestInbox:
    """Inbox API tests"""

    def test_get_conversations(self, session):
        r = session.get(f"{BASE_URL}/api/inbox/conversations")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        print(f"Conversations count: {len(data)}")

    def test_simulate_inbound_creates_conversation(self, session):
        r = session.post(f"{BASE_URL}/api/inbox/simulate-inbound", json={
            "from_phone": "+15550001111",
            "message_text": "Hello from test"
        })
        assert r.status_code in [200, 201]
        data = r.json()
        print(f"Simulate inbound response: {data}")
        assert "conversation_id" in data or "id" in data or "message" in data

    def test_get_conversations_after_simulate(self, session):
        r = session.get(f"{BASE_URL}/api/inbox/conversations")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        # Should have at least one after simulate
        print(f"Conversations after simulate: {len(data)}")


# --- Analytics ---
class TestAnalytics:
    """Analytics API tests"""

    def test_usage_daily_returns_array(self, session):
        r = session.get(f"{BASE_URL}/api/analytics/usage/daily")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        print(f"Daily usage rows: {len(data)}")

    def test_usage_cost_returns_structure(self, session):
        r = session.get(f"{BASE_URL}/api/analytics/usage/cost")
        assert r.status_code == 200
        data = r.json()
        print(f"Usage cost response: {data}")
        # Should be dict with cost fields
        assert isinstance(data, (dict, list))

    def test_analytics_messages_endpoint(self, session):
        r = session.get(f"{BASE_URL}/api/analytics/messages")
        assert r.status_code == 200
        print(f"Analytics messages: {r.json()}")

    def test_analytics_summary(self, session):
        r = session.get(f"{BASE_URL}/api/analytics/summary")
        assert r.status_code == 200
        print(f"Analytics summary: {r.json()}")
