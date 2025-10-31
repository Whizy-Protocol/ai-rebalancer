import orjson
from web3 import Web3

from src.utils import get_env_variable


class AgentWallet:
    """
    AgentWallet for reading on-chain data.
    Users manage their own wallets (MetaMask, WalletConnect, etc.).
    All transactions are signed on the frontend.
    Backend only reads contract state.
    """

    def __init__(self):
        self.rpc_url = get_env_variable("RPC_URL", "https://testnet.hashio.io/api")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.chain_id = 296
        self.usdc_address = "0x8bc6E87bE188B7964E48f37d7A2c144416a995eE"
        self.rebalancer_delegation = get_env_variable(
            "REBALANCER_DELEGATION_ADDRESS", "0x6D5f91cA52bdD5d3DAAb52D91fBfd7e7D253d64A"
        )

    async def get_user_config(self, user_address):
        """
        Get user's delegation configuration from on-chain
        User address is the actual wallet address (e.g., from MetaMask)

        Returns:
            enabled: bool - Whether auto-rebalancing is enabled
            risk_profile: int - Risk profile (1=low, 2=medium, 3=high)
            deposited_amount: float - Amount deposited in USDC
        """
        delegation_abi = await self._read_abi("./abi/RebalancerDelegation.json")
        contract = self.w3.eth.contract(address=self.rebalancer_delegation, abi=delegation_abi)

        config = contract.functions.userConfigs(user_address).call()

        return {
            "enabled": config[0],
            "risk_profile": config[1],
            "deposited_amount": config[2] / (10**6),
        }

    async def get_user_balance(self, user_address):
        """
        Get user's USDC balance
        """
        erc20_abi = await self._read_abi("./abi/erc20.json")
        contract = self.w3.eth.contract(address=self.usdc_address, abi=erc20_abi)

        balance = contract.functions.balanceOf(user_address).call()
        return balance / (10**6)

    async def _read_abi(self, abi_path):
        with open(abi_path) as file:
            return orjson.loads(file.read())
