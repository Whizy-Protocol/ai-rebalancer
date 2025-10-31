# Whizy Protocol - AI Rebalancer Backend

Backend service for Whizy Protocol that provides AI-powered risk assessment, knowledge base queries, and automated yield optimization through delegated rebalancing on the Hedera network.

## Overview

The Whizy Rebalancer is a FastAPI-based backend that:
- 🤖 Assesses user risk profiles using OpenAI GPT-4o-mini
- 📚 Provides protocol knowledge and AI-powered recommendations using RAG (Retrieval-Augmented Generation)
- 💼 Manages non-custodial user wallets (users control their own keys)
- 🔄 Executes automated rebalancing via operator delegation
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

#### 3. Automated Rebalancing (`src/rules.py`)
- **AgentWalletSync**: Synchronous wallet operations for scheduled tasks
- **Operator-based rebalancing**: Backend calls `rebalance()` on delegation contract
- Periodic runner checks all users and rebalances based on risk profiles

#### 4. Smart Contract Integration
- **RebalancerDelegation**: Non-custodial delegation for auto-rebalancing
- **ProtocolSelector**: Automatic best-yield protocol selection
- **USDC Token**: Stablecoin for deposits and operations

### Non-Custodial Architecture

```
User Wallet (MetaMask/WalletConnect)
    ↓ (Frontend) depositAndEnable()
RebalancerDelegation Contract
    ↓ holds user funds
    ↓ autoDeposit()
ProtocolSelector Contract
    ↓ selects best protocol
Yield Protocols (Aave, Morpho, Compound)
    ↓ generates yield
    ↑ (Backend) operator.rebalance(user)
Backend Operator Wallet
```

**Key Points:**
- Users control their own wallets (MetaMask, WalletConnect, etc.)
- All user transactions signed on frontend
- Backend only reads on-chain data and executes rebalancing
- Backend operator can only rebalance, not withdraw user funds
- Users can withdraw anytime via frontend
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

# Smart Contracts
PROTOCOL_SELECTOR_ADDRESS=0x0371aB2d90A436C8E5c5B6aF8835F46A6Ce884Ba
REBALANCER_DELEGATION_ADDRESS=0x6D5f91cA52bdD5d3DAAb52D91fBfd7e7D253d64A
USDC_ADDRESS=0x8bc6E87bE188B7964E48f37d7A2c144416a995eE

# Operator Wallet (for rebalancing)
OPERATOR_PRIVATE_KEY=
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
- RebalancerDelegation: `0x6D5f91cA52bdD5d3DAAb52D91fBfd7e7D253d64A`
- USDC: `0x8bc6E87bE188B7964E48f37d7A2c144416a995eE`

**Available Functions (Frontend calls these directly):**

```javascript
// 1. Deposit and enable auto-rebalancing
await rebalancerDelegation.depositAndEnable(amount, riskProfile);
// Risk profiles: 1=low, 2=medium, 3=high

// 2. Withdraw funds
await rebalancerDelegation.withdraw(amount);
// amount=0 for full withdrawal

// 3. Enable auto-rebalancing
await rebalancerDelegation.enableAutoRebalance(riskProfile);

// 4. Disable auto-rebalancing (funds remain deposited)
await rebalancerDelegation.disableAutoRebalance();

// 5. Check configuration (read-only)
const config = await rebalancerDelegation.userConfigs(userAddress);
// Returns: [enabled, riskProfile, depositedAmount]
```

**Backend only provides:**
- Risk assessment via AI
- Protocol knowledge queries
- User balance/config queries
- Automated rebalancing (operator-only)

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

### Scheduled Rebalancing

The automated rebalancer runs periodically via `scheduler.py`:

```bash
# Start scheduler (runs in background)
python scheduler.py
```

**How it works:**
1. Scheduler calls `runner()` from `src/rules.py`
2. Loads all users from `data/wallet.json`
3. Checks each user's risk profile and deposited funds
4. Operator wallet calls `rebalance(user)` on delegation contract
5. Delegation contract withdraws from current protocol and deposits to best protocol
6. ProtocolSelector automatically selects optimal protocol based on APY

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

### Contracts Used

1. **RebalancerDelegation** (`0x6D5f91cA52bdD5d3DAAb52D91fBfd7e7D253d64A`)
   - Non-custodial delegation contract
   - Users deposit and enable auto-rebalancing
   - Operators rebalance on behalf of users

2. **ProtocolSelector** (`0x0371aB2d90A436C8E5c5B6aF8835F46A6Ce884Ba`)
   - Automatic protocol selection
   - Routes funds to best-yielding protocol
   - Handles deposits/withdrawals across protocols

3. **USDC Token** (`0x8bc6E87bE188B7964E48f37d7A2c144416a995eE`)
   - Stablecoin for deposits
   - ERC20 standard

### ABI Files

Required ABI files in `abi/` directory:
- `RebalancerDelegation.json`
- `ProtocolSelector.json`
- `erc20.json`

## User Flow

### 1. Onboarding
```
User connects wallet (MetaMask/WalletConnect)
    → Frontend checks user has HBAR (for gas)
    → Frontend checks user has USDC
```

### 2. Risk Assessment
```
User answers questions
    → POST /generate-risk-profile
    → Returns risk level (low/medium/high)
```

### 3. Deposit & Enable (Frontend Transaction)
```
User → Frontend calls depositAndEnable() on delegation contract
    → User signs transaction in wallet
    → USDC deposited to RebalancerDelegation
    → Auto-rebalancing enabled with risk profile
    → Funds deployed to best protocol
```

### 4. Automated Rebalancing
```
Scheduler runs periodically
    → Checks all users with auto-rebalance enabled
    → Operator calls rebalance(user) for each user
    → Funds moved to optimal protocol
    → User earns best yields automatically
```

### 5. Withdrawal (Frontend Transaction)
```
User → Backend GET /action/get-user-config (check balance)
    → Frontend calls withdraw() on delegation contract
    → User signs transaction in wallet
    → Funds returned to user wallet
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
