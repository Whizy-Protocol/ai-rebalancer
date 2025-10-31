import pytest
import json
import orjson
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from src.agent import KnowledgeAgent, RiskClassifierAgent


@pytest.fixture
def knowledge_agent():
    """Fixture to create KnowledgeAgent instance with mock URL"""
    return KnowledgeAgent(url="https://api.whizy.fun/api/protocols")


@pytest.fixture
def risk_classifier_agent():
    """Fixture to create RiskClassifierAgent instance"""
    return RiskClassifierAgent()


@pytest.mark.asyncio
async def test_knowledge_agent_load_prompts(knowledge_agent):
    """Test that risk prompts are loaded correctly"""
    assert isinstance(knowledge_agent.risk_prompts, list)
    assert len(knowledge_agent.risk_prompts) > 0
    
    # Check structure of loaded prompts
    for prompt in knowledge_agent.risk_prompts:
        assert "risk" in prompt
        assert "description" in prompt
        assert "prompt" in prompt
        assert prompt["risk"] in ["low", "medium", "high"]


@pytest.mark.asyncio
async def test_knowledge_agent_fetch_knowledge(knowledge_agent):
    """Test fetching knowledge from API"""
    mock_data = [
        {
            "idProtocol": "aave-v3",
            "chain": "ethereum",
            "nameToken": "USDC",
            "tvl": 1000000000,
            "apy": 12.4,
            "stablecoin": True
        }
    ]
    
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_data)
        mock_get.return_value.__aenter__.return_value = mock_response
        
        await knowledge_agent.fetch_knowledge()
        
        assert knowledge_agent.knowledge_data == mock_data
        assert len(knowledge_agent.knowledge_data) == 1


@pytest.mark.asyncio
async def test_knowledge_agent_create_retriever(knowledge_agent):
    """Test creating FAISS retriever from knowledge data"""
    knowledge_agent.knowledge_data = [
        {
            "idProtocol": "aave-v3",
            "chain": "ethereum",
            "nameToken": "USDC",
            "tvl": 1000000000,
            "apy": 12.4,
            "stablecoin": True
        },
        {
            "idProtocol": "compound-v3",
            "chain": "ethereum",
            "nameToken": "USDC",
            "tvl": 500000000,
            "apy": 4.8,
            "stablecoin": True
        }
    ]
    
    # Mock both FAISS and OpenAIEmbeddings to avoid API key requirement
    with patch("src.agent.OpenAIEmbeddings") as mock_embeddings:
        with patch("src.agent.FAISS.from_documents") as mock_faiss:
            mock_retriever = Mock()
            mock_faiss.return_value.as_retriever.return_value = mock_retriever
            
            retriever = await knowledge_agent.create_retriever()
            
            assert retriever is not None
            mock_faiss.assert_called_once()
            mock_embeddings.assert_called_once()


@pytest.mark.asyncio
async def test_risk_classifier_low_risk():
    """Test risk classifier with low risk user responses"""
    agent = RiskClassifierAgent()
    
    # Mock the agent executor
    mock_response = '{"risk": "low"}'
    
    with patch.object(agent, 'agent_executor') as mock_executor:
        mock_message = Mock()
        mock_message.content = mock_response
        mock_executor.invoke.return_value = {"messages": [mock_message]}
        
        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            mock_file.read.return_value = b'[{"user_address": "0x123", "risk_profile": ""}]'
            
            response = await agent.process_query(
                query="I prefer stable returns with no volatility. Safety is my priority.",
                user_address="0x123"
            )
            
            result = json.loads(response)
            assert result["risk"] == "low"


@pytest.mark.asyncio
async def test_risk_classifier_medium_risk():
    """Test risk classifier with medium risk user responses"""
    agent = RiskClassifierAgent()
    
    mock_response = '{"risk": "medium"}'
    
    with patch.object(agent, 'agent_executor') as mock_executor:
        mock_message = Mock()
        mock_message.content = mock_response
        mock_executor.invoke.return_value = {"messages": [mock_message]}
        
        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            mock_file.read.return_value = b'[{"user_address": "0x456", "risk_profile": ""}]'
            
            response = await agent.process_query(
                query="I want good returns and can handle some volatility. I invest in BTC and ETH.",
                user_address="0x456"
            )
            
            result = json.loads(response)
            assert result["risk"] == "medium"


@pytest.mark.asyncio
async def test_risk_classifier_high_risk():
    """Test risk classifier with high risk user responses"""
    agent = RiskClassifierAgent()
    
    mock_response = '{"risk": "high"}'
    
    with patch.object(agent, 'agent_executor') as mock_executor:
        mock_message = Mock()
        mock_message.content = mock_response
        mock_executor.invoke.return_value = {"messages": [mock_message]}
        
        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            mock_file.read.return_value = b'[{"user_address": "0x789", "risk_profile": ""}]'
            
            response = await agent.process_query(
                query="Maximum yield! I'm experienced in DeFi and comfortable with high risk.",
                user_address="0x789"
            )
            
            result = json.loads(response)
            assert result["risk"] == "high"


@pytest.mark.asyncio
async def test_risk_classifier_parse_risk():
    """Test risk parsing from JSON response"""
    agent = RiskClassifierAgent()
    
    # Test valid JSON
    assert agent._parse_risk('{"risk": "low"}') == "low"
    assert agent._parse_risk('{"risk": "medium"}') == "medium"
    assert agent._parse_risk('{"risk": "high"}') == "high"


@pytest.mark.asyncio
async def test_knowledge_agent_get_strategy_low_risk(knowledge_agent):
    """Test getting strategy recommendation for low risk user"""
    mock_strategy = json.dumps({
        "recommended_protocols": ["aave-v3"],
        "expected_apy_range": "10-13%",
        "risk_factors": ["smart contract risk", "protocol risk"],
        "rebalancing_threshold": 2.0,
        "rationale": "Aave offers best stablecoin yields with strong security"
    })
    
    with patch.object(knowledge_agent, 'process_query', return_value=mock_strategy):
        result = await knowledge_agent.get_strategy_recommendation("low")
        
        assert result is not None
        # Should contain strategy information


@pytest.mark.asyncio
async def test_knowledge_agent_get_strategy_invalid_risk(knowledge_agent):
    """Test getting strategy with invalid risk level"""
    result = await knowledge_agent.get_strategy_recommendation("invalid")
    
    assert "error" in result
    assert "Invalid risk level" in result["error"]


@pytest.mark.asyncio
async def test_knowledge_agent_process_query_with_risk(knowledge_agent):
    """Test processing query with risk level context"""
    knowledge_agent.risk_prompts = [
        {
            "risk": "low",
            "prompt": "Test prompt for low risk users"
        }
    ]
    
    with patch.object(knowledge_agent, 'initialize', return_value=None):
        with patch.object(knowledge_agent, 'agent_executor') as mock_executor:
            mock_message = Mock()
            mock_message.content = "Test response"
            mock_executor.invoke.return_value = {"messages": [mock_message]}
            
            response = await knowledge_agent.process_query(
                query="What's the best protocol?",
                risk_level="low"
            )
            
            assert response == "Test response"
            # Verify that the query was enhanced with risk context
            mock_executor.invoke.assert_called_once()


@pytest.mark.asyncio
async def test_risk_classifier_not_initialized():
    """Test error when agent not initialized"""
    agent = RiskClassifierAgent()
    agent.agent_executor = None
    
    with pytest.raises(RuntimeError, match="Agent not initialized"):
        await agent.process_query("test query", "0x123")


@pytest.mark.asyncio
async def test_knowledge_agent_temperature_setting(knowledge_agent):
    """Test that knowledge agent uses correct temperature for consistency"""
    with patch("src.agent.ChatOpenAI") as mock_chatgpt:
        with patch("src.agent.RetrievalQA.from_chain_type"):
            with patch("src.agent.create_react_agent"):
                knowledge_agent._sync_initialize_agent(Mock())
                
                # Verify temperature is set to 0.2 for consistency
                call_args = mock_chatgpt.call_args
                assert call_args[1]["temperature"] == 0.2


@pytest.mark.asyncio
async def test_risk_classifier_temperature_setting():
    """Test that risk classifier uses correct temperature for consistency"""
    agent = RiskClassifierAgent()
    
    with patch("src.agent.ChatOpenAI") as mock_chatgpt:
        with patch("src.agent.create_react_agent"):
            agent._sync_initialize_agent()
            
            # Verify temperature is set to 0.1 for high consistency
            call_args = mock_chatgpt.call_args
            assert call_args[1]["temperature"] == 0.1


def test_prompt_json_structure():
    """Test that prompt.json has correct structure"""
    import os
    import orjson
    
    prompt_path = "./models/prompt.json"
    assert os.path.exists(prompt_path), "prompt.json file should exist"
    
    with open(prompt_path, "r") as f:
        prompts = orjson.loads(f.read())
    
    assert isinstance(prompts, list)
    assert len(prompts) == 3  # low, medium, high
    
    required_fields = ["risk", "description", "target_apy", "asset_preference", 
                       "max_drawdown_tolerance", "rebalancing_strategy", "prompt"]
    
    for prompt in prompts:
        for field in required_fields:
            assert field in prompt, f"Missing field: {field}"
        
        assert prompt["risk"] in ["low", "medium", "high"]
        assert len(prompt["prompt"]) > 100  # Should have detailed prompt


@pytest.mark.asyncio
async def test_knowledge_agent_handles_empty_knowledge_data(knowledge_agent):
    """Test agent behavior with empty knowledge data"""
    knowledge_agent.knowledge_data = []
    
    # Should still be able to create retriever without errors
    # Mock both FAISS and OpenAIEmbeddings to avoid API key requirement
    with patch("src.agent.OpenAIEmbeddings") as mock_embeddings:
        with patch("src.agent.FAISS.from_documents") as mock_faiss:
            mock_retriever = Mock()
            mock_faiss.return_value.as_retriever.return_value = mock_retriever
            
            retriever = await knowledge_agent.create_retriever()
            
            # Should handle empty data gracefully
            assert retriever is not None


@pytest.mark.asyncio
async def test_risk_update_in_wallet_file():
    """Test that risk profile is updated in wallet.json"""
    agent = RiskClassifierAgent()
    agent.file_path = "./data/wallet.json"
    
    mock_data = [
        {"user_address": "0x123", "risk_profile": ""},
        {"user_address": "0x456", "risk_profile": "low"}
    ]
    
    with patch("builtins.open", create=True) as mock_open:
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_file.read.return_value = orjson.dumps(mock_data)
        
        with patch("orjson.dumps", return_value=b"{}") as mock_dumps:
            agent._update_risk_profile("medium", "0x123")
            
            # Verify file was written
            mock_file.write.assert_called_once()
