import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.wallet import AgentWallet


@pytest.fixture
def agent_wallet():
    """Fixture to create AgentWallet instance"""
    return AgentWallet()


@pytest.mark.asyncio
async def test_get_user_config(agent_wallet):
    """Test getting user configuration from delegation contract"""
    mock_config = (True, 1, 1000000000)  # enabled, risk_profile=1, 1000 USDC
    
    with patch.object(agent_wallet, '_read_abi', new_callable=AsyncMock) as mock_read_abi:
        with patch.object(agent_wallet.w3.eth, 'contract') as mock_contract:
            mock_read_abi.return_value = []
            mock_contract.return_value.functions.userConfigs.return_value.call.return_value = mock_config
            
            result = await agent_wallet.get_user_config("0x123...")
            
            assert result["enabled"] == True
            assert result["risk_profile"] == 1
            assert result["deposited_amount"] == 1000.0


@pytest.mark.asyncio
async def test_get_user_balance(agent_wallet):
    """Test getting user USDC balance"""
    mock_balance = 5000000000  # 5000 USDC in base units
    
    with patch.object(agent_wallet, '_read_abi', new_callable=AsyncMock) as mock_read_abi:
        with patch.object(agent_wallet.w3.eth, 'contract') as mock_contract:
            mock_read_abi.return_value = []
            mock_contract.return_value.functions.balanceOf.return_value.call.return_value = mock_balance
            
            result = await agent_wallet.get_user_balance("0x123...")
            
            assert result == 5000.0


@pytest.mark.asyncio
async def test_get_user_config_disabled(agent_wallet):
    """Test getting user config when auto-rebalance is disabled"""
    mock_config = (False, 2, 500000000)  # disabled, risk_profile=2, 500 USDC
    
    with patch.object(agent_wallet, '_read_abi', new_callable=AsyncMock) as mock_read_abi:
        with patch.object(agent_wallet.w3.eth, 'contract') as mock_contract:
            mock_read_abi.return_value = []
            mock_contract.return_value.functions.userConfigs.return_value.call.return_value = mock_config
            
            result = await agent_wallet.get_user_config("0x456...")
            
            assert result["enabled"] == False
            assert result["risk_profile"] == 2
            assert result["deposited_amount"] == 500.0


@pytest.mark.asyncio
async def test_get_user_balance_zero(agent_wallet):
    """Test getting user balance when balance is zero"""
    mock_balance = 0
    
    with patch.object(agent_wallet, '_read_abi', new_callable=AsyncMock) as mock_read_abi:
        with patch.object(agent_wallet.w3.eth, 'contract') as mock_contract:
            mock_read_abi.return_value = []
            mock_contract.return_value.functions.balanceOf.return_value.call.return_value = mock_balance
            
            result = await agent_wallet.get_user_balance("0x789...")
            
            assert result == 0.0
