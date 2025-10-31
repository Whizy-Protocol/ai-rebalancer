import pytest
from unittest.mock import Mock, patch, MagicMock
from src.rules import AgentWalletSync, handle_low_risk, handle_high_risk, runner


@pytest.fixture
def agent_wallet_sync():
    """Fixture to create AgentWalletSync instance"""
    with patch("src.rules.get_env_variable") as mock_env:
        mock_env.side_effect = lambda key, default: {
            "RPC_URL": "https://testnet.hashio.io/api",
            "REBALANCER_DELEGATION_ADDRESS": "0x6D5f91cA52bdD5d3DAAb52D91fBfd7e7D253d64A",
            "OPERATOR_PRIVATE_KEY": "0x1234567890abcdef"
        }.get(key, default)
        return AgentWalletSync()


def test_get_operator_account(agent_wallet_sync):
    """Test getting operator account from private key"""
    with patch("src.rules.Account") as mock_account:
        mock_account.from_key.return_value = Mock(address="0xOperator")
        
        operator = agent_wallet_sync._get_operator_account()
        
        mock_account.from_key.assert_called_once()
        assert operator.address == "0xOperator"


def test_get_operator_account_no_key():
    """Test error when operator private key is not set"""
    with patch("src.rules.get_env_variable") as mock_env:
        mock_env.side_effect = lambda key, default: {
            "RPC_URL": "https://testnet.hashio.io/api",
            "REBALANCER_DELEGATION_ADDRESS": "0x6D5f91cA52bdD5d3DAAb52D91fBfd7e7D253d64A",
            "OPERATOR_PRIVATE_KEY": ""
        }.get(key, default)
        
        agent = AgentWalletSync()
        
        with pytest.raises(ValueError, match="OPERATOR_PRIVATE_KEY not set"):
            agent._get_operator_account()


def test_rebalance_user(agent_wallet_sync):
    """Test rebalancing a user"""
    user_address = "0x123..."
    
    with patch.object(agent_wallet_sync, '_get_operator_account') as mock_operator:
        with patch.object(agent_wallet_sync, '_read_abi') as mock_abi:
            with patch.object(agent_wallet_sync, '_send_contract_tx') as mock_tx:
                mock_operator.return_value = Mock(address="0xOperator")
                mock_abi.return_value = []
                mock_tx.return_value = "0xtxhash"
                
                result = agent_wallet_sync.rebalance_user(user_address)
                
                assert result == "0xtxhash"
                mock_tx.assert_called_once()


def test_get_users_with_auto_rebalance(agent_wallet_sync):
    """Test getting users with auto-rebalance enabled"""
    users = agent_wallet_sync.get_users_with_auto_rebalance()
    
    # Currently returns empty list - placeholder
    assert users == []


def test_handle_low_risk():
    """Test handling low risk users"""
    with patch("src.rules.AgentWalletSync") as mock_agent_class:
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent
        
        handle_low_risk("0x123...", [])
        
        mock_agent.rebalance_user.assert_called_once_with("0x123...")


def test_handle_high_risk():
    """Test handling high/medium risk users"""
    with patch("src.rules.AgentWalletSync") as mock_agent_class:
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent
        
        handle_high_risk("0x456...", [])
        
        mock_agent.rebalance_user.assert_called_once_with("0x456...")


def test_handle_low_risk_error():
    """Test error handling in low risk rebalancing"""
    with patch("src.rules.AgentWalletSync") as mock_agent_class:
        mock_agent = Mock()
        mock_agent.rebalance_user.side_effect = Exception("Rebalance failed")
        mock_agent_class.return_value = mock_agent
        
        # Should not raise, just print error
        handle_low_risk("0x789...", [])
        
        mock_agent.rebalance_user.assert_called_once()


def test_runner_no_users():
    """Test runner with no users"""
    with patch("src.rules.AgentWalletSync") as mock_agent_class:
        mock_agent = Mock()
        mock_agent.get_users_with_auto_rebalance.return_value = []
        mock_agent_class.return_value = mock_agent
        
        runner()
        
        # Should return early when no users
        mock_agent.get_users_with_auto_rebalance.assert_called_once()


def test_runner_with_users():
    """Test runner with users"""
    with patch("src.rules.AgentWalletSync") as mock_agent_class:
        with patch("src.rules.handle_user") as mock_handle:
            mock_agent = Mock()
            mock_agent.get_users_with_auto_rebalance.return_value = ["0x123...", "0x456..."]
            mock_agent_class.return_value = mock_agent
            
            runner()
            
            # Should call handle_user for each user
            assert mock_handle.call_count == 2
