import asyncio
from concurrent.futures import ThreadPoolExecutor

import aiohttp
import orjson
import pandas as pd
from fastapi import HTTPException
from langchain.chains import RetrievalQA
from langchain.docstore.document import Document
from langchain.tools import Tool
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent


class KnowledgeAgent:
    def __init__(self, url: str, max_workers: int = 3):
        self.url = url
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.agent_executor = None
        self._lock = asyncio.Lock()
        self.knowledge_data = []
        self.risk_prompts = self._load_risk_prompts()

    def _load_risk_prompts(self):
        """Load risk-based prompts from JSON file"""
        try:
            with open("./models/prompt.json") as f:
                return orjson.loads(f.read())
        except Exception as e:
            print(f"Warning: Could not load risk prompts: {e}")
            return []

    async def fetch_knowledge(self):
        async with aiohttp.ClientSession() as session, session.get(self.url) as response:
            if response.status == 200:
                self.knowledge_data = await response.json()
            else:
                raise HTTPException(
                    status_code=response.status,
                    detail=f"Failed to fetch {self.url}",
                )

    async def initialize(self):
        async with self._lock:
            await self.fetch_knowledge()
            retriever = await self.create_retriever()
            self.agent_executor = await asyncio.get_event_loop().run_in_executor(
                self.thread_pool, self._sync_initialize_agent, retriever
            )

    async def create_retriever(self):
        df = pd.DataFrame(self.knowledge_data)
        docs = [
            Document(
                page_content=f"Protocol ID: {row['id']}, Name: {row['name']}, Base APY: {row['baseApy']}, Active: {row['isActive']}",
                metadata={"protocol_id": row["id"], "name": row["name"], "apy": row["baseApy"]},
            )
            for _, row in df.iterrows()
        ]

        return await asyncio.get_event_loop().run_in_executor(
            self.thread_pool,
            lambda: FAISS.from_documents(docs, OpenAIEmbeddings()).as_retriever(),
        )

    def _sync_initialize_agent(self, retriever):
        llm = ChatOpenAI(model="gpt-4o-mini-2024-07-18", temperature=0.2)
        qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
        qa_tool = Tool(
            name="KnowledgeBaseQA",
            func=lambda query: qa_chain.invoke({"query": query})["result"],
            description="Search DeFi protocols for TVL, APY, risk levels, and token information. Returns data about Aave, Compound, Morpho and other protocols.",
        )

        tools = [qa_tool]

        system_prompt = (
            "You are a DeFi yield optimization assistant for Whizy Protocol. "
            "You help users find the best yield opportunities based on their risk profile. \n"
            "Available protocols: Aave (12.4% APY), Compound (4.8% APY), Morpho (6.2% APY). \n"
            "The ProtocolSelector smart contract automatically chooses the best protocol using: \n"
            "- 50% weight on APY (higher yields preferred) \n"
            "- 30% weight on TVL (higher liquidity preferred) \n"
            "- 20% weight on Risk Level (matches user's risk tolerance) \n\n"
            "RebalancerDelegation contract handles automatic rebalancing when APY improvements >2% are detected. \n"
            "Always provide actionable, accurate information based on the knowledge base."
        )

        return create_react_agent(llm, tools=tools, state_modifier=system_prompt)

    async def process_query(
        self, query: str, thread_id: str | None = None, risk_level: str | None = None
    ):
        """Process query with optional risk-based context"""
        await self.initialize()

        # Enhance query with risk-based context if provided
        enhanced_query = query
        if risk_level and self.risk_prompts:
            risk_prompt = next((p for p in self.risk_prompts if p["risk"] == risk_level), None)
            if risk_prompt:
                enhanced_query = f"{risk_prompt['prompt']}\n\nUser query: {query}"

        config = {"configurable": {"thread_id": thread_id or "Knowledge Agent API"}}
        return await asyncio.get_event_loop().run_in_executor(
            self.thread_pool,
            lambda: self.agent_executor.invoke(
                {"messages": [HumanMessage(content=enhanced_query)]}, config=config
            )["messages"][-1].content,
        )

    async def get_strategy_recommendation(self, risk_level: str):
        """Get yield strategy recommendation based on risk level"""
        risk_prompt = next((p for p in self.risk_prompts if p["risk"] == risk_level), None)
        if not risk_prompt:
            return {"error": f"Invalid risk level: {risk_level}"}

        # Query knowledge base with risk-specific prompt
        query = f"""Based on current protocol data, recommend the optimal yield strategy.
        Risk Profile: {risk_level.upper()}
        Strategy: {risk_prompt["rebalancing_strategy"]}

        Analyze the knowledge base and return a JSON response with:
        1. recommended_protocols: List of suitable protocols
        2. expected_apy_range: Expected APY range
        3. risk_factors: Key risk considerations
        4. rebalancing_threshold: Minimum APY improvement to trigger rebalance

        Return ONLY valid JSON, no additional text."""

        response = await self.process_query(query)
        return response


class RiskClassifierAgent:
    def __init__(self, max_workers: int = 3):
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.agent_executor = None
        self._lock = asyncio.Lock()
        self.file_path = "./data/wallet.json"

    async def initialize(self):
        async with self._lock:
            if self.agent_executor is None:
                self.agent_executor = await asyncio.get_event_loop().run_in_executor(
                    self.thread_pool, self._sync_initialize_agent
                )

    def _sync_initialize_agent(self):
        llm = ChatOpenAI(model="gpt-4o-mini-2024-07-18", temperature=0.1)
        memory = MemorySaver()

        system_prompt = (
            "You are an expert risk profile classifier for DeFi yield farming strategies in Whizy Protocol. "
            "Your role is to analyze user responses and classify them into precise risk categories. \n\n"
            "## Risk Classification Framework:\n\n"
            "### LOW RISK (Conservative):\n"
            "- Capital preservation is top priority\n"
            "- Prefers stablecoins only\n"
            "- Cannot tolerate more than 5% drawdown\n"
            "- Seeks steady, predictable returns (2-8% APY)\n"
            "- Short to medium investment horizon (months)\n"
            "- Minimal DeFi experience\n"
            "- High security concerns\n"
            "Example: 'I want stable returns, no price volatility, I panic when I see any losses'\n\n"
            "### MEDIUM RISK (Balanced):\n"
            "- Balance between growth and stability\n"
            "- Open to major cryptocurrencies (BTC, ETH, SOL, BNB)\n"
            "- Can tolerate 10-20% drawdown\n"
            "- Seeks good returns (4-12% APY)\n"
            "- Medium to long-term horizon (6 months - 2 years)\n"
            "- Some DeFi experience\n"
            "- Moderate security awareness\n"
            "Example: 'I want good returns, can handle some volatility, invest in blue-chip crypto'\n\n"
            "### HIGH RISK (Aggressive):\n"
            "- Maximum yield is priority\n"
            "- Open to any asset type\n"
            "- Can tolerate 30%+ drawdown\n"
            "- Seeks highest returns (8-20%+ APY)\n"
            "- Long-term horizon (1+ years)\n"
            "- Experienced in DeFi\n"
            "- Accepts smart contract risks\n"
            "Example: 'Give me maximum yield, I understand risks, experienced trader'\n\n"
            "## Analysis Guidelines:\n"
            "1. Look for keywords indicating risk tolerance: 'stable', 'conservative', 'safe' vs 'aggressive', 'maximum', 'highest'\n"
            "2. Assess time horizon mentions: shorter = lower risk\n"
            "3. Consider loss tolerance: specific percentages mentioned\n"
            "4. Evaluate experience level: beginner = lower risk\n"
            "5. Asset preference: stablecoins only = low, any asset = high\n\n"
            "## Output Format:\n"
            "You MUST respond with ONLY valid JSON in this EXACT format:\n"
            '{"risk": "low"}  OR  {"risk": "medium"}  OR  {"risk": "high"}\n\n'
            "Do NOT include explanations, reasoning, or any text outside the JSON.\n"
            "Do NOT use markdown code blocks.\n"
            "Return ONLY the raw JSON object."
        )

        return create_react_agent(llm, tools=[], checkpointer=memory, state_modifier=system_prompt)

    async def process_query(self, query: str, user_address: str):
        if self.agent_executor is None:
            raise RuntimeError("Agent not initialized. Please call initialize() first.")

        config = {"configurable": {"thread_id": "Risk Assessment API"}}

        response = await asyncio.get_event_loop().run_in_executor(
            self.thread_pool,
            lambda: self.agent_executor.invoke(
                {"messages": [HumanMessage(content=query)]}, config=config
            )["messages"][-1].content,
        )

        self._update_risk_profile(self._parse_risk(response), user_address)

        return response

    def _update_risk_profile(self, risk_profile: str, user_address: str):
        with open(self.file_path, "rb") as file:
            content = file.read()
            if isinstance(content, bytes):
                wallet_data = orjson.loads(content)
            else:
                wallet_data = orjson.loads(content) if content else []

        for entry in wallet_data:
            if entry["user_address"] == user_address:
                entry["risk_profile"] = risk_profile
                with open(self.file_path, "wb") as file:
                    file.write(orjson.dumps(wallet_data, option=orjson.OPT_INDENT_2))

    def _parse_risk(self, response):
        return orjson.loads(response).get("risk")
