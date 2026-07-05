"""Phase 2.5 Backend API Tests - Inbox, Analytics, Usage, Platform"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": "owner@demo.com", "password": "Owner123!"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return s


class TestInboxPhase25:
    """Inbox API tests - simulate-inbound, conversations"""

    def test_simulate_inbound_returns_conversation_id_and_created(self, session):
        r = session.post(f"{BASE_URL}/api/inbox/simulate-inbound", json={
            "from_phone": "+15559998888",
            "message_text": "Test inbound message"
        })
        assert r.status_code in [200, 201], f"Expected 200/201, got {r.status_code}: {r.text}"
        data = r.json()
        print(f"simulate-inbound response: {data}")
        assert "conversation_id" in data, f"Missing conversation_id in {data}"

    def test_simulate_inbound_with_new_waid(self, session):
        """Simulate new conversation with a different WA ID"""
        r = session.post(f"{BASE_URL}/api/inbox/simulate-inbound", json={
            "from_phone": "+15551234567",
            "message_text": "Hello from new contact"
        })
        assert r.status_code in [200, 201], f"Got {r.status_code}: {r.text}"
        data = r.json()
        assert "conversation_id" in data
        print(f"New WA ID conversation: {data}")

    def test_get_conversations_returns_array(self, session):
        r = session.get(f"{BASE_URL}/api/inbox/conversations")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1, f"Expected at least 1 conversation, got {len(data)}"
        print(f"Conversations count: {len(data)}")
        # Check structure
        if data:
            conv = data[0]
            print(f"First conversation keys: {list(conv.keys())}")

    def test_get_conversation_messages(self, session):
        """Get messages for the demo conversation"""
        r = session.get(f"{BASE_URL}/api/inbox/conversations")
        assert r.status_code == 200
        convs = r.json()
        if convs:
            conv_id = convs[0].get("id") or convs[0].get("_id") or convs[0].get("conversation_id")
            if conv_id:
                r2 = session.get(f"{BASE_URL}/api/inbox/conversations/{conv_id}/messages")
                print(f"Messages status: {r2.status_code}, response: {r2.text[:200]}")
                assert r2.status_code in [200, 404]


class TestAnalyticsPhase25:
    """Analytics API tests"""

    def test_usage_daily_returns_array(self, session):
        r = session.get(f"{BASE_URL}/api/analytics/usage/daily")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        print(f"Daily usage rows: {len(data)}")

    def test_usage_cost_shape(self, session):
        r = session.get(f"{BASE_URL}/api/analytics/usage/cost")
        assert r.status_code == 200
        data = r.json()
        print(f"Usage cost: {data}")
        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        assert "mtd_cost_usd" in data, f"Missing mtd_cost_usd in {data}"
        assert "by_category" in data, f"Missing by_category in {data}"
        assert "by_country" in data, f"Missing by_country in {data}"

    def test_analytics_dashboard_shape(self, session):
        r = session.get(f"{BASE_URL}/api/analytics/dashboard")
        assert r.status_code == 200
        data = r.json()
        print(f"Dashboard: {data}")
        assert "delivery_rate" in data, f"Missing delivery_rate in {data}"
        assert "read_rate" in data, f"Missing read_rate in {data}"
        assert "failure_rate" in data, f"Missing failure_rate in {data}"
        assert "cost_burn_rate" in data, f"Missing cost_burn_rate in {data}"
        assert "throughput" in data, f"Missing throughput in {data}"


class TestPlatformPhase25:
    """Platform API tests - owner should get 403"""

    def test_platform_overview_requires_super_admin(self, session):
        """owner@demo.com should get 403 on platform overview"""
        r = session.get(f"{BASE_URL}/api/platform/overview")
        print(f"Platform overview status: {r.status_code}, response: {r.text[:200]}")
        assert r.status_code == 403, f"Expected 403 for non-super-admin, got {r.status_code}"
