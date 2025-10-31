import orjson
from eth_account import Account
from web3 import Web3

from src.utils import get_env_variable


class AgentWalletSync:
    def __init__(self):
        self.rpc_url = get_env_variable("RPC_URL", "https://testnet.hashio.io/api")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.chain_id = 296
        self.market_address = get_env_variable(
            "MARKET_ADDRESS", "0x0f881762d0fd0E226fe00f2CE5801980EB046902"
        )
        self.operator_private_key = get_env_variable("OPERATOR_PRIVATE_KEY", "")

    def _get_operator_account(self):
        """Get operator account from private key"""
        if not self.operator_private_key:
            raise ValueError("OPERATOR_PRIVATE_KEY not set in .env")
        return Account.from_key(self.operator_private_key)

    def rebalance_market_vault(self, market_id):
        """
        Operator rebalances a market vault to optimal yield protocol
        market_id is the numeric ID of the prediction market
        """
        operator_account = self._get_operator_account()
        market_abi = self._read_abi("./abi/WhizyPredictionMarket.json")

        return self._send_contract_tx(
            operator_account,
            self.market_address,
            market_abi,
            "rebalanceMarketVault",
            market_id,
        )

    def get_active_markets(self):
        """
        Get all active markets that need rebalancing from indexer database.
        Returns list of market IDs with Active status.
        """
        try:
            from src.db_connector import get_db

            db = get_db()

            markets = db.get_active_markets()
            return [market["market_id"] for market in markets]
        except Exception as e:
            print(f"Error fetching markets from database: {e}")
            print("Make sure DATABASE_URL is set in .env and indexer is running")
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


def handle_market(market_id: int):
    """
    Rebalance a market's vault to optimal yield protocol
    """
    try:
        agent = AgentWalletSync()
        tx_hash = agent.rebalance_market_vault(market_id)
        print(f"Successfully rebalanced market {market_id}: {tx_hash}")
        return tx_hash
    except Exception as e:
        print(f"Error rebalancing market {market_id}: {e}")
        return None


def runner():
    """
    Runner for automated market vault rebalancing.
    Rebalances all active markets to optimal yield protocols.
    """
    print("Starting market vault rebalancing...")
    agent = AgentWalletSync()
    market_ids = agent.get_active_markets()

    if not market_ids:
        print("No active markets found to rebalance")
        return

    print(f"Found {len(market_ids)} active markets to rebalance")
    success_count = 0

    for market_id in market_ids:
        print(f"Rebalancing market {market_id}...")
        tx_hash = handle_market(market_id)
        if tx_hash:
            success_count += 1

    print(
        f"Rebalancing complete: {success_count}/{len(market_ids)} markets rebalanced successfully"
    )
