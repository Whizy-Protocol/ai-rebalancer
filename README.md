# Whizy Protocol - AI Rebalancer Backend

Backend service for Whizy Protocol that provides AI-powered risk assessment, knowledge base queries, and automated market vault yield optimization on the Hedera network.

## Overview

The Whizy Rebalancer is a FastAPI-based backend that:
- 🤖 Assesses user risk profiles using OpenAI GPT-4o-mini
- 📚 Provides protocol knowledge and AI-powered recommendations using RAG (Retrieval-Augmented Generation)
- 💼 Manages non-custodial user wallets (users control their own keys)
- 🔄 Executes automated market vault rebalancing to optimal yield protocols
- 📊 Optimizes yields for all users betting in active markets
- ⛓️ Integrates with smart contracts on Hedera network
- 🧪 Comprehensive test suite with unit and integration tests

## Architecture

### Core Components

#### 1. AI Agents (`src/agent.py`)

**RiskClassifierAgent**
- Analyzes user responses using OpenAI GPT-4o-mini (temperature: 0.1 for consistency)
- Classifies users into risk profiles: low/medium/high
- Updates risk profile in wallet data automatically
- Uses structured JSON output for reliable parsing
- Risk classification framework:
  - **Low**: Conservative, stablecoins only, 2-8% APY target, max 5% drawdown
  - **Medium**: Balanced, major crypto + stablecoins, 4-12% APY target, max 10-20% drawdown
  - **High**: Aggressive, any asset, 8-20%+ APY target, max 30%+ drawdown

**KnowledgeAgent**
- RAG-based system using FAISS vector store with OpenAI embeddings
- Fetches real-time protocol data from knowledge API
- Provides context-aware answers based on user's risk profile
- Uses RetrievalQA chain for accurate information retrieval
- Risk-specific prompts from `models/prompt.json`
- Returns strategy recommendations with expected APY ranges and risk factors

#### 2. Wallet Management (`src/wallet.py`)
- Reads on-chain data for user wallets
- Users manage their own wallets (MetaMask, WalletConnect, etc.)
- All transactions are signed on the frontend
- Backend functions:
  - Query user configuration from delegation contract
  - Get user USDC balance

#### 3. Automated Market Vault Rebalancing (`src/rules.py`)
- **AgentWalletSync**: Synchronous wallet operations for scheduled tasks
- **Operator-based rebalancing**: Backend calls `rebalanceMarketVault(marketId)` on prediction market contract
- Periodic runner checks all active markets and rebalances their vaults to optimal yield protocols
- Benefits ALL users with bets in those markets automatically
- **Manual rebalancing**: Users can also trigger rebalancing via frontend for immediate optimization

#### 4. Smart Contract Integration
- **WhizyPredictionMarket**: Market creation and vault rebalancing
- **MarketVault**: Individual market vaults (ERC4626) that hold bet funds and generate yield
- **ProtocolSelector**: Automatic best-yield protocol selection
- **RebalancerDelegation**: Optional user delegation for separate deposits (not used for market funds)
- **USDC Token**: Stablecoin for bets and operations

### Market Vault Rebalancing Architecture

```
User Wallet (MetaMask/WalletConnect)
    ↓ placeBet() on market
WhizyPredictionMarket Contract
    ↓ creates/uses MarketVault (ERC4626)
MarketVault Contract
    ↓ auto-deposits to best protocol
ProtocolSelector Contract
    ↓ selects optimal protocol
Yield Protocols (Aave, Morpho, Compound)
    ↓ generates yield for ALL market participants
    ↑ (Backend OR User) rebalanceMarketVault(marketId)
Backend Operator Wallet / User Wallet
```

**Key Points:**
- Users place bets on markets, funds go to market vault
- Market vaults automatically earn yield on all deposited funds
- **Automated rebalancing**: Backend operator rebalances market vaults hourly
- **Manual rebalancing**: Any user can trigger rebalancing via frontend
- Operator can only rebalance vaults, not withdraw funds
- Yield benefits ALL users with positions in that market
- Winners claim: principal + winnings + their share of yield
- Losers claim: their share of yield (lose principal to winners)
- Fully transparent on-chain operations

## Installation

### Prerequisites

```bash
# Python 3.10+
python3 --version

# Install dependencies
pip install -r requirements.txt
```

### Environment Setup

Create `.env` file:

```bash
# OpenAI API for AI agents
OPENAI_API_KEY=your_openai_api_key_here

# Protocol data source (API endpoint that returns protocol data)
URL_KNOWLEDGE=https://your-api-endpoint.com/protocols

# DeFiLlama API (for scraping yield data - optional)
DEFILLAMA_API=https://yields.llama.fi/pools

# Hedera Network
RPC_URL=https://testnet.hashio.io/api

# Database URL (for tracking active markets)
DATABASE_URL=postgresql://user:pass@localhost:5432/your_db

# Smart Contracts
PROTOCOL_SELECTOR_ADDRESS=0x097c8868c58194125025804Df54ecFc3a9a73985
MARKET_ADDRESS=0x0f881762d0fd0E226fe00f2CE5801980EB046902
ACCESS_CONTROL_ADDRESS=0xbac99b7FF3624d6Add9884cE51a993ceA1f99C9a
REBALANCER_DELEGATION_ADDRESS=0xA5d395776429C06C01B5983B32e36Bf578c655a9
USDC_ADDRESS=0x5f2faF6b0B0F79fbD1B70e0ff244Da92C614e44a

# Operator Wallet (for automated rebalancing)
OPERATOR_PRIVATE_KEY=your_operator_private_key
```

## API Endpoints

### AI & Knowledge

#### `POST /generate-risk-profile`
Assess user risk profile based on questionnaire responses.

**Request:**
```json
{
  "user_address": "0x123...",
  "data": "User's responses to risk questions"
}
```

**Response:**
```json
{
  "risk_level": "low|medium|high",
  "confidence": 0.95
}
```

#### `POST /query`
Query knowledge agent about protocols and strategies.

**Request:**
```json
{
  "query": "What is the best protocol for stablecoins?",
  "thread_id": "optional-thread-id"
}
```

**Response:**
```json
{
  "response": [{"id_project": "protocol-id"}],
  "thread_id": "thread-id",
  "processing_time": 0.5
}
```

### Wallet Queries

#### `POST /action/get-user-balance`
Get user's USDC balance.

**Request:**
```json
{
  "user_address": "0x123..."
}
```

**Response:**
```json
{
  "balance": 1000.0
}
```

#### `POST /action/get-user-config`
Get user's delegation configuration.

**Request:**
```json
{
  "user_address": "0x123..."
}
```

**Response:**
```json
{
  "enabled": true,
  "risk_profile": 1,
  "deposited_amount": 1000.0
}
```

### Frontend Integration

**All delegation transactions must be signed on the frontend using the user's wallet (MetaMask, WalletConnect, etc.)**

**Contract Addresses:**
- WhizyPredictionMarket: `0x0f881762d0fd0E226fe00f2CE5801980EB046902`
- USDC: `0x5f2faF6b0B0F79fbD1B70e0ff244Da92C614e44a`

**Market Betting (Frontend):**

```javascript
// 1. Place a bet on a market
await predictionMarket.placeBet(marketId, isYes, amount);
// isYes: true for YES, false for NO
// Funds automatically go to market vault and earn yield

// 2. Manually trigger market vault rebalancing
await predictionMarket.rebalanceMarketVault(marketId);
// Any user can call this to optimize vault yields immediately

// 3. Claim winnings after market resolves
await predictionMarket.claimWinnings(marketId);
// Winners get: principal + winnings + yield share
// Losers get: yield share only

// 4. Check market info (read-only)
const info = await predictionMarket.getMarketInfo(marketId);
// Returns: market data, total assets, current yield, yield withdrawn

// 5. Check potential payout (read-only)
const payout = await predictionMarket.getPotentialPayout(marketId, userAddress);
// Returns: yesPayoutIfWin, noPayoutIfWin, currentYield
```

**Backend provides:**
- Risk assessment via AI
- Protocol knowledge queries
- User balance queries
- Automated market vault rebalancing (runs hourly)

### Health Check

#### `GET /health`
Check API health status.

## Running the Service

### Development

```bash
# Start the API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production

```bash
# Using gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Scheduled Market Vault Rebalancing

The automated rebalancer runs hourly via `scheduler.py`:

```bash
# Start scheduler (runs in background)
python scheduler.py
```

**How it works:**
1. Scheduler calls `runner()` from `src/rules.py` every hour
2. Queries database for all active markets (not resolved, end time in future)
3. For each active market, operator wallet calls `rebalanceMarketVault(marketId)` on prediction market contract
4. Market vault withdraws all funds from current yield protocol
5. Market vault deposits all funds to optimal yield protocol (via ProtocolSelector)
6. All users with bets in that market benefit from better yields

**Manual Rebalancing:**
Users can also trigger rebalancing from the frontend anytime:
```javascript
// Frontend calls this directly
await predictionMarket.rebalanceMarketVault(marketId);
```
This immediately optimizes the market vault without waiting for the hourly scheduler.

## Data Storage

### User Tracking

**Note:** The backend does NOT store user wallet data. Users control their own wallets.

For automated rebalancing, you need to track which users have enabled auto-rebalancing:

**Option 1: Database**
```sql
CREATE TABLE users (
  wallet_address VARCHAR(42) PRIMARY KEY,
  auto_rebalance_enabled BOOLEAN,
  risk_profile INT,
  created_at TIMESTAMP
);
```

**Option 2: Event Listening**
Listen to delegation contract events:
- `AutoRebalanceEnabled(address user, uint8 riskProfile)`
- `AutoRebalanceDisabled(address user)`
- Track users who enable/disable via events

**Current Implementation:**
- `runner()` function needs user tracking implementation
- Currently returns early as no tracking is implemented
- Frontend should notify backend when users enable auto-rebalancing

## Smart Contract Integration

### Smart Contracts Used

1. **WhizyPredictionMarket** (`0x0f881762d0fd0E226fe00f2CE5801980EB046902`)
   - Market creation and resolution
   - Bet placement and claiming
   - Market vault rebalancing
   - Operator management

2. **MarketVault** (Created per market, ERC4626)
   - Holds all funds for a specific market
   - Auto-deposits to yield protocols
   - Tracks shares for each position
   - Generates yield for all participants

3. **ProtocolSelector** (`0x097c8868c58194125025804Df54ecFc3a9a73985`)
   - Automatic protocol selection
   - Routes funds to best-yielding protocol
   - Handles deposits/withdrawals across protocols

4. **RebalancerDelegation** (`0xA5d395776429C06C01B5983B32e36Bf578c655a9`) (Optional)
   - For separate user deposits outside of markets
   - Not used for market betting

5. **USDC Token** (`0x5f2faF6b0B0F79fbD1B70e0ff244Da92C614e44a`)
   - Stablecoin for bets
   - ERC20 standard

### ABI Files

Required ABI files in `abi/` directory:
- `WhizyPredictionMarket.json`
- `MarketVault.json`
- `ProtocolSelector.json`
- `RebalancerDelegation.json` (optional)
- `erc20.json`

## User Flow

### 1. Onboarding
```
User connects wallet (MetaMask/WalletConnect)
    → Frontend checks user has HBAR (for gas)
    → Frontend checks user has USDC
```

### 2. Risk Assessment (Optional - for AI recommendations)
```
User answers questions
    → POST /generate-risk-profile
    → Returns risk level (low/medium/high)
    → GET /get-strategy-recommendation
    → Returns optimal strategy
```

### 3. Place Bet (Frontend Transaction)
```
User selects market and position (YES/NO)
    → Frontend calls placeBet(marketId, isYes, amount)
    → User signs transaction in wallet
    → USDC transferred to prediction market contract
    → Funds deposited to MarketVault
    → MarketVault auto-deploys funds to best yield protocol
    → User's position recorded with shares
```

### 4. Automated Yield Optimization
```
Scheduler runs hourly
    → Queries all active markets from database
    → For each market: operator calls rebalanceMarketVault(marketId)
    → Market vault moves funds to optimal protocol
    → All users in that market earn better yields

OR

User manually triggers rebalancing
    → Frontend calls rebalanceMarketVault(marketId)
    → Immediate optimization without waiting
```

### 5. Claim Winnings (Frontend Transaction)
```
Market resolves → User clicks claim
    → Backend GET /getPotentialPayout (check winnings + yield)
    → Frontend calls claimWinnings(marketId)
    → User signs transaction in wallet
    → Winners receive: principal + winnings + yield share
    → Losers receive: yield share only
```

## Security Considerations

### Non-Custodial Architecture
- ✅ Users control their own wallets (MetaMask, WalletConnect, etc.)
- ✅ Backend never has access to user private keys
- ✅ Backend cannot withdraw user funds from delegation contract
- ✅ Users can withdraw anytime via frontend
- ✅ All operations are transparent on-chain
- ✅ Backend only reads data and executes operator rebalancing

### Operator Permissions
- ✅ Operator can only call `rebalance()` function
- ✅ Cannot withdraw or transfer user funds
- ✅ Can be removed by contract owner if compromised

### Private Key Management
- ✅ Users manage their own private keys via wallet apps
- 🔒 Operator key stored in secure environment variable
- 🔒 Production: Store operator key in HSM, KMS, or secure vault

### Smart Contract Security
- ✅ ReentrancyGuard on all functions
- ✅ Access control for operator and owner functions
- ✅ Users can disable auto-rebalancing anytime

## Testing

The project includes comprehensive test coverage with unit tests and integration tests.

### Test Structure

```
test/
├── test_agents.py         # AI agent tests (mocked)
├── test_api.py            # API endpoint tests
├── test_rules.py          # Rebalancing logic tests
├── test_wallet.py         # Wallet operations tests
├── test_scrape.py         # Data scraping tests
├── test_integration.py    # Real API integration tests
└── README_INTEGRATION.md  # Integration test documentation
```

### Running Tests

```bash
# Run unit tests only (fast, mocked)
make test

# Run integration tests (requires API keys)
make test-integration

# Run all tests
make test-all

# Run with coverage report
make test-coverage

# Clean cache files
make clean
```

### Code Quality

```bash
# Run linter
make lint

# Auto-fix linting issues
make lint-fix

# Format code
make format

# Run both linter and formatter
make check
```

### Integration Tests

Integration tests require real API keys and make actual API calls:

```bash
# Set environment variables
export OPENAI_API_KEY="your-key"
export URL_KNOWLEDGE="your-api-url"

# Run integration tests
make test-integration
```

**Integration tests include:**
- Real OpenAI API calls for risk classification
- Real knowledge agent queries with RAG
- Strategy recommendation generation
- Data fetching from external APIs

### API Testing

```bash
# Health check
curl http://localhost:8000/health

# Risk profile assessment
curl -X POST http://localhost:8000/generate-risk-profile \
  -H "Content-Type: application/json" \
  -d '{
    "user_address": "0x123...",
    "data": "I prefer stable returns with no volatility"
  }'

# Get strategy recommendation
curl -X POST http://localhost:8000/get-strategy-recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "user_address": "0x123...",
    "data": "I want maximum yield"
  }'

# Query knowledge agent
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the best stablecoin protocols?",
    "thread_id": "optional-thread-id"
  }'

# Get user balance
curl -X POST http://localhost:8000/action/get-user-balance \
  -H "Content-Type: application/json" \
  -d '{"user_address": "0x123..."}'

# Get user config
curl -X POST http://localhost:8000/action/get-user-config \
  -H "Content-Type: application/json" \
  -d '{"user_address": "0x123..."}'
```

## Monitoring & Logging

The service logs all operations:
- User wallet creation
- Deposit/withdrawal transactions
- Rebalancing operations
- Errors and exceptions

## Troubleshooting

### Common Issues

**"No users with auto-rebalance enabled (tracking not implemented yet)"**
- User tracking needs to be implemented via database or event listening
- See "Data Storage > User Tracking" section for implementation options

**"OPERATOR_PRIVATE_KEY not set in .env"**
- Add operator private key to `.env` file

**"InsufficientBalance" on withdrawal**
- Check user's actual deposited amount via `/action/get-user-config`
- Use the `deposited_amount` value for withdrawal

**Transaction fails with "AutoRebalanceNotEnabled"**
- User has disabled auto-rebalancing
- User needs to call `/action/enable-auto-rebalance` first

**Transaction fails with "NotOperator"**
- Operator wallet address not authorized
- Contract owner needs to call `addOperator(address)`

## Development Roadmap

### Current Features
- ✅ AI-powered risk assessment using OpenAI GPT-4o-mini
- ✅ RAG-based knowledge agent with FAISS vector store
- ✅ Risk-specific strategy recommendations
- ✅ Delegated auto-rebalancing (non-custodial)
- ✅ Multi-protocol support (Aave, Morpho, Compound)
- ✅ RESTful API with FastAPI
- ✅ Comprehensive test suite (unit + integration)
- ✅ Code quality tools (Ruff linting + formatting)
- ✅ Automated testing with Make commands

### Future Enhancements
- 🔄 WebSocket support for real-time updates
- 🔄 Event listening for on-chain auto-rebalance triggers
- 🔄 Database integration for user tracking (currently not implemented)
- 🔄 Advanced risk models with ML
- 🔄 Multi-token support (beyond USDC)
- 🔄 Historical performance analytics
- 🔄 Gas optimization strategies
- 🔄 Frontend dashboard
- 🔄 Multi-chain support
- 🔄 More DeFi protocol integrations

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - see LICENSE file for details.
