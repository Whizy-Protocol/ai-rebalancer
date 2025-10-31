import orjson
import requests
from web3 import Web3
from eth_account import Account
from utils import get_env_variable


def _load_existing_data():
    with open("data/wallet.json", "rb") as file:
        return orjson.loads(file.read())


def fetch_data(user_address):
    existing_data = _load_existing_data()

    for entry in existing_data:
        if entry["user_address"] == user_address:
            wallet_data = entry["data"]
            account = Account.from_key(wallet_data["private_key"])
            return account


def get_data_staked(user_address):
    account = fetch_data(user_address)
    address = account.address

    rpc_url = get_env_variable("RPC_URL", "https://testnet.hashio.io/api")
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    selector_address = get_env_variable(
        "PROTOCOL_SELECTOR_ADDRESS", "0x0371aB2d90A436C8E5c5B6aF8835F46A6Ce884Ba"
    )

    with open("abi/ProtocolSelector.json", "r") as file:
        selector_abi = orjson.loads(file.read())

    usdc_address = "0x8bc6E87bE188B7964E48f37d7A2c144416a995eE"

    result_amount = []
    try:
        contract = w3.eth.contract(address=selector_address, abi=selector_abi)
        balance = contract.functions.getTotalBalance(address, usdc_address).call()
        readable_balance = balance / (10**6)

        if int(readable_balance) > 0:
            result_amount.append(
                {
                    "token": "USDC",
                    "token_address": usdc_address,
                    "amount": readable_balance,
                }
            )
    except Exception as e:
        print(f"Error retrieving balance: {e}")

    return result_amount


def get_risk(user_address):
    wallet_data = _load_existing_data()
    for entry in wallet_data:
        if entry["user_address"] == user_address:
            return entry["risk_profile"]


if __name__ == "__main__":
    user_wallet = "0x0000000000000000000000000000000000000003"
    user_risk = get_risk(user_wallet)
    result = get_data_staked(user_wallet)
    print(result)
