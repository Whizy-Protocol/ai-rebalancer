from typing import Optional
from pydantic import BaseModel


class QueryRequestClassifier(BaseModel):
    data: str
    user_address: str


class QueryRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None


class QueryResponse(BaseModel):
    response: str
    thread_id: str
    processing_time: float


class QueryUserWallet(BaseModel):
    user_address: str


class QueryMint(BaseModel):
    user_address: str
    amount: str


class QueryTransfer(BaseModel):
    user_address: str
    contract_address: str
    to: str
    amount: str


class QueryDepositAndEnable(BaseModel):
    user_address: str
    amount: str
    risk_profile: int  # 1=low, 2=medium, 3=high


class QueryEnableAutoRebalance(BaseModel):
    user_address: str
    risk_profile: int  # 1=low, 2=medium, 3=high


class QueryDisableAutoRebalance(BaseModel):
    user_address: str


class QueryWithdrawDelegation(BaseModel):
    user_address: str
    amount: str  # 0 = withdraw all
