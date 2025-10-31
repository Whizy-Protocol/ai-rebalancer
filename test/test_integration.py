"""
Integration tests with real API calls.
These tests require environment variables to be set:
- OPENAI_API_KEY
- URL_KNOWLEDGE

Run with: pytest test/test_integration.py -v
"""

import json
import os
from unittest.mock import MagicMock, patch

import orjson
import pytest

from src.agent import KnowledgeAgent, RiskClassifierAgent


@pytest.fixture
def knowledge_agent():
    """Fixture to create KnowledgeAgent instance with real URL from environment"""
    url = os.getenv("URL_KNOWLEDGE")
    if not url:
        pytest.skip("URL_KNOWLEDGE environment variable not set")
    return KnowledgeAgent(url=url)


@pytest.fixture
def risk_classifier_agent():
    """Fixture to create RiskClassifierAgent instance"""
    return RiskClassifierAgent()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_knowledge_agent_fetch(knowledge_agent):
    """Test fetching real data from the API"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY environment variable not set")

    await knowledge_agent.fetch_knowledge()

    assert len(knowledge_agent.knowledge_data) > 0

    first_item = knowledge_agent.knowledge_data[0]
    assert "idProtocol" in first_item
    assert "chain" in first_item
    assert "nameToken" in first_item
    assert "apy" in first_item


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_knowledge_agent_query(knowledge_agent):
    """Test real query to knowledge agent with OpenAI"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY environment variable not set")

    await knowledge_agent.fetch_knowledge()

    response = await knowledge_agent.process_query(
        query="What are the top 3 protocols with highest APY for stablecoins?", risk_level="low"
    )

    assert response is not None
    assert len(response) > 0
    print(f"\nKnowledge Agent Response:\n{response}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_risk_classifier_low_risk(risk_classifier_agent):
    """Test real risk classification with OpenAI for low risk profile"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY environment variable not set")

    await risk_classifier_agent.initialize()

    mock_read_file = MagicMock()
    mock_write_file = MagicMock()
    mock_data = [{"user_address": "0xtest123", "risk_profile": ""}]
    mock_read_file.read.return_value = orjson.dumps(mock_data)

    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__.side_effect = [mock_read_file, mock_write_file]

        response = await risk_classifier_agent.process_query(
            query="I prefer stable returns with no volatility. Safety is my top priority. I only want stablecoins.",
            user_address="0xtest123",
        )

        assert response is not None
        result = json.loads(response)
        assert "risk" in result
        assert result["risk"] == "low"
        print(f"\nRisk Classification Response (Low): {response}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_risk_classifier_medium_risk(risk_classifier_agent):
    """Test real risk classification with OpenAI for medium risk profile"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY environment variable not set")

    await risk_classifier_agent.initialize()

    mock_read_file = MagicMock()
    mock_write_file = MagicMock()
    mock_data = [{"user_address": "0xtest456", "risk_profile": ""}]
    mock_read_file.read.return_value = orjson.dumps(mock_data)

    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__.side_effect = [mock_read_file, mock_write_file]

        response = await risk_classifier_agent.process_query(
            query="I want good returns and can handle some volatility. I invest in BTC and ETH. I'm comfortable with 10-15% drawdown.",
            user_address="0xtest456",
        )

        assert response is not None
        result = json.loads(response)
        assert "risk" in result
        assert result["risk"] == "medium"
        print(f"\nRisk Classification Response (Medium): {response}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_risk_classifier_high_risk(risk_classifier_agent):
    """Test real risk classification with OpenAI for high risk profile"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY environment variable not set")

    await risk_classifier_agent.initialize()

    mock_read_file = MagicMock()
    mock_write_file = MagicMock()
    mock_data = [{"user_address": "0xtest789", "risk_profile": ""}]
    mock_read_file.read.return_value = orjson.dumps(mock_data)

    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__.side_effect = [mock_read_file, mock_write_file]

        response = await risk_classifier_agent.process_query(
            query="Maximum yield! I'm experienced in DeFi and comfortable with high risk. I can tolerate 30%+ drawdowns. Give me the highest APY possible.",
            user_address="0xtest789",
        )

        assert response is not None
        result = json.loads(response)
        assert "risk" in result
        assert result["risk"] == "high"
        print(f"\nRisk Classification Response (High): {response}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_strategy_recommendation(knowledge_agent):
    """Test getting real strategy recommendation based on risk level"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY environment variable not set")

    await knowledge_agent.fetch_knowledge()

    response = await knowledge_agent.get_strategy_recommendation("low")

    assert response is not None
    assert len(response) > 0
    print(f"\nStrategy Recommendation (Low Risk):\n{response}")
