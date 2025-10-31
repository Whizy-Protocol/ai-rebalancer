import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from main import app


@pytest.fixture
def client():
    """Fixture to create FastAPI test client"""
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "thread_pool_info" in data


@pytest.mark.asyncio
async def test_get_user_balance(client):
    """Test get user balance endpoint"""
    with patch("main.agent_wallet.get_user_balance", new_callable=AsyncMock) as mock_balance:
        mock_balance.return_value = 1000.0
        
        response = client.post(
            "/action/get-user-balance",
            json={"user_address": "0x123..."}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["balance"] == 1000.0


@pytest.mark.asyncio
async def test_get_user_config(client):
    """Test get user config endpoint"""
    with patch("main.agent_wallet.get_user_config", new_callable=AsyncMock) as mock_config:
        mock_config.return_value = {
            "enabled": True,
            "risk_profile": 2,
            "deposited_amount": 500.0
        }
        
        response = client.post(
            "/action/get-user-config",
            json={"user_address": "0x456..."}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] == True
        assert data["risk_profile"] == 2
        assert data["deposited_amount"] == 500.0


@pytest.mark.asyncio
async def test_generate_risk_profile(client):
    """Test risk profile generation endpoint"""
    with patch("main.risk_classifier_agent.process_query", new_callable=AsyncMock) as mock_classify:
        mock_classify.return_value = '{"risk_level": "medium", "confidence": 0.85}'
        
        response = client.post(
            "/generate-risk-profile",
            json={
                "user_address": "0x789...",
                "data": "I prefer balanced investments with moderate returns"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] == "medium"
        assert data["confidence"] == 0.85


@pytest.mark.asyncio
async def test_query_knowledge_agent(client):
    """Test knowledge agent query endpoint"""
    with patch("main.knowledge_agent.process_query", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = '{"id_project": "aave-v3"}'
        
        response = client.post(
            "/query",
            json={
                "query": "What is Aave?",
                "thread_id": "test-thread"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert data["response"][0]["id_project"] == "aave-v3"
        assert data["thread_id"] == "test-thread"


def test_invalid_endpoint(client):
    """Test calling invalid endpoint"""
    response = client.get("/invalid-endpoint")
    assert response.status_code == 404
