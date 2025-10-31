import orjson
from eth_account import Account
from web3 import Web3

from src.checker import get_data_staked, get_risk
from src.utils import get_env_variable


class AgentWalletSync:
    def __init__(self):
        self.rpc_url = get_env_variable("RPC_URL", "https://testnet.hashio.io/api")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.chain_id = 296
        self.rebalancer_delegation = get_env_variable(
            "REBALANCER_DELEGATION_ADDRESS", "0x6D5f91cA52bdD5d3DAAb52D91fBfd7e7D253d64A"
        )
        self.operator_private_key = get_env_variable("OPERATOR_PRIVATE_KEY", "")

    def _get_operator_account(self):
        """Get operator account from private key"""
        if not self.operator_private_key:
            raise ValueError("OPERATOR_PRIVATE_KEY not set in .env")
        return Account.from_key(self.operator_private_key)

    def rebalance_user(self, user_address):
        """
        Operator rebalances user's funds via RebalancerDelegation contract
        user_address is the actual wallet address (e.g., from MetaMask)
        """
        operator_account = self._get_operator_account()
        delegation_abi = self._read_abi("./abi/RebalancerDelegation.json")

        return self._send_contract_tx(
            operator_account,
            self.rebalancer_delegation,
            delegation_abi,
            "rebalance",
            user_address,
        )

    def get_users_with_auto_rebalance(self):
        """
        Get all users who have auto-rebalance enabled from the delegation contract
        This queries events or iterates through known users
        """
        # TODO: Implement event listening or maintain a database of users
        return []

    def _send_contract_tx(self, account, contract_address, abi, method_name, *args):
        """Helper method to send contract transactions"""
        contract = self.w3.eth.contract(address=contract_address, abi=abi)
        method = getattr(contract.functions, method_name)

        nonce = self.w3.eth.get_transaction_count(account.address)

        tx = method(*args).build_transaction(
            {
                "from": account.address,
                "nonce": nonce,
                "gas": 500000,
                "gasPrice": self.w3.eth.gas_price,
                "chainId": self.chain_id,
            }
        )

        signed_tx = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return receipt["transactionHash"].hex()

    def _read_abi(self, abi_path):
        with open(abi_path) as file:
            return orjson.loads(file.read())


def handle_user(user_address: str):
    user_risk = get_risk(user_address)
    user_staked = get_data_staked(user_address)

    match user_risk:
        case "low":
            handle_low_risk(user_address, user_staked)
        case "medium":
            handle_high_risk(user_address, user_staked)
        case "high":
            handle_high_risk(user_address, user_staked)


def handle_low_risk(user_address, user_staked):
    """Handle low risk users - rebalance via delegation contract"""
    try:
        agent = AgentWalletSync()
        agent.rebalance_user(user_address)
        print(f"Successfully rebalanced low-risk user: {user_address}")
    except Exception as e:
        print(f"Error rebalancing user {user_address}: {e}")


def handle_high_risk(user_address, user_staked):
    """Handle high/medium risk users - rebalance via delegation contract"""
    try:
        agent = AgentWalletSync()
        agent.rebalance_user(user_address)
        print(f"Successfully rebalanced high-risk user: {user_address}")
    except Exception as e:
        print(f"Error rebalancing user {user_address}: {e}")


def runner():
    """
    Runner for automated rebalancing.
    Note: This requires a database or event listening to track user addresses.
    Currently returns early as no user tracking is implemented.
    """
    agent = AgentWalletSync()
    user_addresses = agent.get_users_with_auto_rebalance()

    if not user_addresses:
        print("No users with auto-rebalance enabled (tracking not implemented yet)")
        return

    for address in user_addresses:
        handle_user(address)
