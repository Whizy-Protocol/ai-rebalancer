from unittest.mock import Mock, patch

import pytest

from src.rules import AgentWalletSync, handle_market, runner


@pytest.fixture
def agent_wallet_sync():
    """Fixture to create AgentWalletSync instance"""
    with patch("src.rules.get_env_variable") as mock_env:
        mock_env.side_effect = lambda key, default: {
            "RPC_URL": "https://testnet.hashio.io/api",
            "MARKET_ADDRESS": "0x0f881762d0fd0E226fe00f2CE5801980EB046902",
            "OPERATOR_PRIVATE_KEY": "0x1234567890abcdef",
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
            "MARKET_ADDRESS": "0x0f881762d0fd0E226fe00f2CE5801980EB046902",
            "OPERATOR_PRIVATE_KEY": "",
        }.get(key, default)

        agent = AgentWalletSync()

        with pytest.raises(ValueError, match="OPERATOR_PRIVATE_KEY not set"):
            agent._get_operator_account()


def test_rebalance_market_vault(agent_wallet_sync):
    """Test rebalancing a market vault"""
    market_id = 1

    with (
        patch.object(agent_wallet_sync, "_get_operator_account") as mock_operator,
        patch.object(agent_wallet_sync, "_read_abi") as mock_abi,
        patch.object(agent_wallet_sync, "_send_contract_tx") as mock_tx,
    ):
        mock_operator.return_value = Mock(address="0xOperator")
        mock_abi.return_value = []
        mock_tx.return_value = "0xtxhash"

        result = agent_wallet_sync.rebalance_market_vault(market_id)

        assert result == "0xtxhash"
        mock_tx.assert_called_once_with(
            mock_operator.return_value,
            agent_wallet_sync.market_address,
            [],
            "rebalanceMarketVault",
            market_id,
        )


def test_get_active_markets(agent_wallet_sync):
    """Test getting active markets"""
    markets = agent_wallet_sync.get_active_markets()

    # Currently returns empty list if db not available
    assert isinstance(markets, list)


def test_handle_market():
    """Test handling market vault rebalancing"""
    with patch("src.rules.AgentWalletSync") as mock_agent_class:
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent
        mock_agent.rebalance_market_vault.return_value = "0xtxhash"

        result = handle_market(1)

        assert result == "0xtxhash"
        mock_agent.rebalance_market_vault.assert_called_once_with(1)


def test_handle_market_error():
    """Test error handling in market vault rebalancing"""
    with patch("src.rules.AgentWalletSync") as mock_agent_class:
        mock_agent = Mock()
        mock_agent.rebalance_market_vault.side_effect = Exception("Rebalance failed")
        mock_agent_class.return_value = mock_agent

        # Should not raise, just print error and return None
        result = handle_market(1)

        assert result is None
        mock_agent.rebalance_market_vault.assert_called_once()


def test_runner_no_markets():
    """Test runner with no active markets"""
    with patch("src.rules.AgentWalletSync") as mock_agent_class:
        mock_agent = Mock()
        mock_agent.get_active_markets.return_value = []
        mock_agent_class.return_value = mock_agent

        runner()

        # Should return early when no markets
        mock_agent.get_active_markets.assert_called_once()


def test_runner_with_markets():
    """Test runner with active markets"""
    with (
        patch("src.rules.AgentWalletSync") as mock_agent_class,
        patch("src.rules.handle_market") as mock_handle,
    ):
        mock_agent = Mock()
        mock_agent.get_active_markets.return_value = [1, 2, 3]
        mock_agent_class.return_value = mock_agent
        mock_handle.return_value = "0xtxhash"

        runner()

        # Should call handle_market for each market
        assert mock_handle.call_count == 3
        mock_handle.assert_any_call(1)
        mock_handle.assert_any_call(2)
        mock_handle.assert_any_call(3)
