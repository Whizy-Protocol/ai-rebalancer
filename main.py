import time
import json

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import asyncio
from src.agent import KnowledgeAgent, RiskClassifierAgent
from src.wallet import AgentWallet
from src.utils import get_env_variable
from models.schemas import *

load_dotenv()

app = FastAPI(
    title="Agent API",
    description="API for interacting with Agent with Knowledge Hedera",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

URL_KNOWLEDGE = get_env_variable("URL_KNOWLEDGE", "")

risk_classifier_agent = RiskClassifierAgent()
knowledge_agent = KnowledgeAgent(url=URL_KNOWLEDGE)
agent_wallet = AgentWallet()


@app.on_event("startup")
async def startup_event():
    """Initialize agent when the API starts."""
    await risk_classifier_agent.initialize()
    await knowledge_agent.initialize()


@app.post("/generate-risk-profile")
async def assess_risk(request: QueryRequestClassifier):
    """
    Endpoint to assess risk profile based on user responses.
    Returns a JSON with risk assessment level.
    """
    try:
        response = await risk_classifier_agent.process_query(
            query=request.data, user_address=request.user_address
        )
        parsed_response = json.loads(response)

        return JSONResponse(content=parsed_response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
async def query_agent_sync(request: QueryRequest):
    """
    Synchronous endpoint to query the knowledge agent
    """
    try:
        start_time = time.time()

        response = await asyncio.wait_for(
            knowledge_agent.process_query(
                query=request.query, thread_id=request.thread_id
            ),
            timeout=30.0,
        )

        parsed_response = (
            json.loads(response) if isinstance(response, str) else response
        )
        formatted_response = {"id_project": str(parsed_response.get("id_project", ""))}
        processing_time = time.time() - start_time

        response_json = {
            "response": [formatted_response],
            "thread_id": request.thread_id or "Knowledge Agent API",
            "processing_time": processing_time,
        }

        return JSONResponse(content=response_json)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Query processing failed: {str(e)}"
        )


@app.post("/action/get-user-balance")
async def get_user_balance(request: QueryUserWallet):
    """Get user's USDC balance"""
    response = {"balance": await agent_wallet.get_user_balance(request.user_address)}
    return JSONResponse(content=response)


@app.post("/action/get-user-config")
async def get_user_config(request: QueryUserWallet):
    """Get user's delegation configuration"""
    response = await agent_wallet.get_user_config(request.user_address)
    return JSONResponse(content=response)


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "thread_pool_info": {
            "max_workers": knowledge_agent.thread_pool._max_workers,
            "active_threads": knowledge_agent.thread_pool._work_queue.qsize(),
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
