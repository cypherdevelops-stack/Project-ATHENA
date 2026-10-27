# 🧠 PROJECT A.T.H.E.N.A.

### **Algorithmic Trading & High-Execution Network for Assets**

<p align="center">
  <strong>An intelligent, governed algorithmic trading architecture for market analysis, strategy orchestration, risk governance, execution, memory, and machine learning.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Project-ATHENA-0f172a?style=for-the-badge" alt="Project ATHENA">
  <img src="https://img.shields.io/badge/Status-Active%20Development-f59e0b?style=for-the-badge" alt="Status">
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/PostgreSQL-Supabase-3ECF8E?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Frontend-TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Trading-MT5-0B5CAD?style=flat-square" alt="MetaTrader 5">
  <img src="https://img.shields.io/badge/Architecture-Modular-06B6D4?style=flat-square" alt="Modular Architecture">
  <img src="https://img.shields.io/badge/AI%20%2F%20ML-In%20Development-8B5CF6?style=flat-square" alt="AI ML">
  <img src="https://img.shields.io/badge/License-Private-111827?style=flat-square" alt="License">
</p>

---

## 📖 Table of Contents

- [About ATHENA](#-about-athena)
- [Creator & Ownership](#-creator--ownership)
- [Vision](#-vision)
- [Core Philosophy](#-core-philosophy)
- [Architecture](#-architecture)
- [Core Systems](#-core-systems)
  - [Market Data](#1-market-data-layer)
  - [Market Intelligence](#2-market-intelligence)
  - [News & Sentiment](#3-news--sentiment-intelligence)
  - [Strategy Engines](#4-strategy-engines)
  - [Strategy Orchestrator](#5-strategy-orchestrator)
  - [Risk & Portfolio Governance](#6-risk--portfolio-governance)
  - [Executioner](#7-executioner)
  - [AMEF](#8-amef--memory--experience-fabric)
  - [Machine Learning](#9-machine-learning)
  - [Backtesting](#10-backtesting)
  - [Journal](#11-trading-journal)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Data Flow](#-end-to-end-decision-flow)
- [UI & Screenshots](#-ui--screenshots)
- [Getting Started](#-getting-started)
- [Environment Configuration](#-environment-configuration)
- [Development Commands](#-development-commands)
- [Testing](#-testing)
- [Git Workflow](#-git-workflow)
- [Development Roadmap](#-development-roadmap)
- [Security](#-security)
- [Risk Disclaimer](#-risk-disclaimer)
- [Contributing](#-contributing)
- [Developer](#-developer)
- [License](#-license)

---

# 🧠 About ATHENA

**PROJECT A.T.H.E.N.A.** stands for:

> **Algorithmic Trading & High-Execution Network for Assets**

ATHENA is an advanced algorithmic trading and market-intelligence platform designed to combine:

- Quantitative analysis
- Technical analysis
- Smart Money Concepts / market structure
- News and sentiment intelligence
- Multi-timeframe analysis
- Strategy engines
- Machine learning
- Persistent trading memory
- Portfolio and risk governance
- Strategy orchestration
- Broker execution
- Backtesting
- Trade journaling
- Monitoring and observability

ATHENA is being designed as a **decision and execution ecosystem**, rather than as a conventional trading bot built around a single indicator or strategy.

The core philosophy is:

```text
Market Data
     ↓
Market Understanding
     ↓
Strategy Analysis
     ↓
Decision
     ↓
Risk Governance
     ↓
Execution
     ↓
Observation
     ↓
Memory
     ↓
Learning
     ↺
Future Decisions
```

---

# 👤 Creator & Ownership

## Designed & Created By

### **Cypher**

Under:

### **Cypher Develops — A Software Company**

ATHENA is an original software architecture and development project conceived and developed by **Cypher** under the **Cypher Develops** software company.

---

# 🎯 Vision

The long-term vision of ATHENA is to create a sophisticated algorithmic trading intelligence capable of progressing from:

> **Data → Information → Context → Decision → Governance → Execution → Experience → Memory → Learning**

ATHENA is intended to understand not only what the market is doing, but also:

- Why a setup exists
- Whether multiple evidence sources agree
- Whether the setup is appropriate for the current market regime
- Whether the portfolio can safely accept the trade
- Whether similar situations have occurred before
- What happened in those situations
- Whether the current opportunity resembles historical successes or failures

The goal is **controlled intelligence**, not uncontrolled autonomy.

---

# 🧭 Core Philosophy

ATHENA follows several architectural principles.

### 1. Separation of Concerns

Market analysis, strategies, orchestration, risk, execution, memory, and presentation should remain distinct systems.

### 2. Governance Before Execution

A strategy should identify an opportunity; it should not have unrestricted authority to trade.

### 3. Probabilistic Intelligence + Deterministic Controls

Machine learning and memory may provide probabilities and context, while hard risk and safety rules remain deterministic.

### 4. Observability

Important decisions should be traceable and explainable.

### 5. Persistent Experience

Trading outcomes should become structured experience that can be retrieved later.

### 6. Modular Evolution

New strategies, models, intelligence sources, and broker integrations should be addable without rebuilding the entire system.

---

# 🏗️ Architecture

## High-Level Architecture

```text
                         ┌─────────────────────────┐
                         │       MARKET DATA       │
                         │                         │
                         │ OHLCV • Tick • Sessions │
                         │ News • Account • Events │
                         └────────────┬────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────┐
                  │       MARKET INTELLIGENCE          │
                  │                                    │
                  │ • Market Structure / SMC           │
                  │ • EMA / MACD / RSI                 │
                  │ • Momentum / Volatility             │
                  │ • Multi-Timeframe Analysis          │
                  │ • Correlation                       │
                  │ • News & Sentiment                  │
                  │ • Market Regime                     │
                  └──────────────────┬─────────────────┘
                                     │
                                     ▼
                  ┌────────────────────────────────────┐
                  │          STRATEGY ENGINES           │
                  │                                    │
                  │       Scalping • Day Trading       │
                  │       Future Strategies             │
                  └──────────────────┬─────────────────┘
                                     │
                                     ▼
                  ┌────────────────────────────────────┐
                  │       STRATEGY ORCHESTRATOR         │
                  │                                    │
                  │ • Strategy Coordination             │
                  │ • Opportunity Ranking               │
                  │ • Conflict Detection                │
                  │ • Portfolio Awareness               │
                  │ • Risk Governance                   │
                  └──────────────────┬─────────────────┘
                                     │
                                     ▼
                  ┌────────────────────────────────────┐
                  │          DECISION LAYER             │
                  │                                    │
                  │ • ML Probability                    │
                  │ • AMEF Memory                       │
                  │ • Confidence                        │
                  │ • Market Context                    │
                  │ • Risk Assessment                   │
                  └──────────────────┬─────────────────┘
                                     │
                                     ▼
                  ┌────────────────────────────────────┐
                  │             EXECUTIONER             │
                  │                                    │
                  │ • Order Validation                  │
                  │ • Broker Communication               │
                  │ • SL / TP                           │
                  │ • Breakeven                         │
                  │ • Position Management                │
                  └──────────────────┬─────────────────┘
                                     │
                                     ▼
                         ┌─────────────────────────┐
                         │     TRADE OUTCOME      │
                         │                         │
                         │ Profit/Loss • Execution │
                         │ Quality • Context       │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │          AMEF           │
                         │                         │
                         │ Episodic • Structural   │
                         │ Counterfactual • Failure│
                         └────────────┬────────────┘
                                      │
                                      └──────► Future Decisions
```

---

# 🔄 End-to-End Decision Flow

A simplified ATHENA decision cycle looks like this:

```text
                    MARKET EVENT
                         │
                         ▼
                  DATA COLLECTION
                         │
                         ▼
                FEATURE GENERATION
                         │
                         ▼
             ┌───────────────────────┐
             │ MARKET CONTEXT        │
             │                       │
             │ HTF Bias              │
             │ LTF Structure         │
             │ Regime                │
             │ News                  │
             │ Momentum              │
             └───────────┬───────────┘
                         │
                         ▼
                STRATEGY EVALUATION
                         │
                         ▼
                 OPPORTUNITY SCORE
                         │
                         ▼
              STRATEGY ORCHESTRATOR
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
         Risk Accepted          Risk Rejected
              │                     │
              ▼                     └──► LOG / MONITOR
       GOVERNED DECISION
              │
              ▼
         EXECUTIONER
              │
              ▼
          BROKER / MT5
              │
              ▼
       POSITION MONITORING
              │
              ▼
         TRADE OUTCOME
              │
              ▼
         AMEF / JOURNAL
              │
              ▼
       FUTURE CONTEXT
```

---

# 🧩 Core Systems

## 1. Market Data Layer

ATHENA consumes the market and account information required by downstream intelligence.

Potential data includes:

- OHLCV
- Tick/price information
- Multiple timeframes
- Market sessions
- Account state
- Open positions
- Historical trades
- Economic events
- Financial news

Supported development timeframes include:

```text
M1
M5
M15
H1
H4
```

---

## 2. Market Intelligence

ATHENA combines multiple forms of market evidence.

### Technical Analysis

- EMA
- MACD
- RSI
- Momentum
- Volatility
- Price action

### Market Structure

- Break of Structure (BOS)
- Change of Character (CHOCH)
- Order Blocks
- Points of Interest (POIs)
- Liquidity
- Fair Value Gaps
- Premium / Discount
- Multi-timeframe bias

Indicators are treated as **evidence**, not independent trade authorities.

---

## 3. News & Sentiment Intelligence

ATHENA includes a dedicated news and sentiment intelligence layer.

It is designed to evaluate:

- Financial news
- Economic events
- Asset-specific news
- Market-moving events
- Bullish/bearish sentiment
- Sentiment strength
- News relevance
- Potential market impact

News intelligence may influence:

- Higher-timeframe bias
- Trade confidence
- Risk assessment
- Trade eligibility
- Position management

The objective is to prevent technically attractive setups from being evaluated without fundamental context.

---

## 4. Strategy Engines

ATHENA separates individual trading strategies from the central orchestration system.

### Scalping Engine

Designed around short-term opportunities and lower-timeframe execution.

### Day Trading Engine

Designed around intraday opportunities using higher-timeframe context and lower-timeframe confirmation.

The architecture is designed to support future strategy engines without coupling them directly to broker execution.

---

## 5. Strategy Orchestrator

The **Strategy Orchestrator** is the central coordinator between strategy engines and the execution system.

It answers:

> **Which strategy should be allowed to act, under what conditions, and with what level of risk?**

Responsibilities include:

- Strategy coordination
- Opportunity ranking
- Strategy prioritization
- Portfolio awareness
- Position conflict detection
- Strategy conflict resolution
- Exposure management
- Risk governance
- Session management
- Alerts
- Orchestration monitoring

The orchestrator prevents independent strategies from blindly competing for the same account.

---

## 6. Risk & Portfolio Governance

Risk management is a first-class architectural component.

ATHENA is designed to evaluate:

- Risk per trade
- Position sizing
- Account exposure
- Existing positions
- Correlated positions
- Maximum exposure
- Strategy-level risk
- Volatility
- Market conditions
- Trade quality
- Execution constraints

A technically valid setup can still be rejected if the portfolio-level risk is unacceptable.

---

## 7. Executioner

The **Executioner** is the controlled execution and position-management layer.

Its responsibility begins after a decision passes the required governance checks.

It handles:

- Order preparation
- Order validation
- Broker communication
- Order submission
- Stop-loss
- Take-profit
- Position monitoring
- Dynamic stop management
- Breakeven
- Execution status
- Error handling
- Execution logging

The intended boundary is:

```text
Strategy
   ↓
Analysis
   ↓
Orchestrator
   ↓
Risk Governance
   ↓
Executioner
   ↓
Broker
```

Strategies should not directly bypass the governance and execution layers.

---

# 🧠 8. AMEF — Memory & Experience Fabric

## ATHENA Memory & Experience Fabric

**AMEF** is ATHENA's architectural framework for persistent trading memory.

Its purpose is to allow ATHENA to move beyond:

> "What is happening now?"

toward:

> "Have I encountered a similar situation before, and what happened?"

AMEF is designed around four major memory domains.

### Episodic Memory

Individual trading experiences:

- Entry
- Exit
- Market conditions
- Strategy
- Result
- Context
- Execution quality

### Structural Memory

Recurring market structures:

- Order Block behavior
- POI behavior
- Regimes
- Market structures
- Multi-timeframe relationships

### Counterfactual Memory

Situations where an alternative decision could have been made:

- Rejected trade that later succeeded
- Trade that should have been avoided
- Alternative entry
- Alternative exit

### Failure Memory

Recurring conditions associated with poor decisions:

- Failed setups
- Bad market regimes
- Poor entry conditions
- Repeated strategy weaknesses

AMEF is intended to make historical experience available to future decision-making.

---

# 🤖 9. Machine Learning

Machine Learning is intended to **augment**, rather than replace, ATHENA's governed architecture.

Potential ML responsibilities include:

- Trade probability estimation
- Market regime classification
- Pattern recognition
- Opportunity scoring
- Feature relationship discovery
- Risk estimation
- Outcome prediction
- Market-context classification

The architectural distinction is:

```text
Deterministic Logic
        │
        ├── Hard Rules
        ├── Risk Controls
        └── Governance
                 │
                 ▼
Machine Learning ──────► Probabilistic Evidence
                 │
                 ▼
AMEF ──────────────────► Historical Context
                 │
                 ▼
           Decision Layer
```

Future ML development is expected to include:

- Dataset construction
- Feature engineering
- Training pipelines
- Validation
- Model versioning
- Calibration
- Inference
- Drift detection
- Performance monitoring

---

# 📊 10. Backtesting

ATHENA includes a dedicated backtesting architecture.

Backtesting is intended to evaluate:

- Strategy performance
- Win rate
- Profit factor
- Drawdown
- Risk-adjusted performance
- Trade frequency
- Strategy conflicts
- Portfolio behavior
- Decision quality
- Execution assumptions

The long-term objective is to make backtesting representative of the same decision architecture used by live ATHENA.

---

# 📓 11. Trading Journal

The journal records trade decisions and outcomes with contextual information.

Potential journal fields include:

- Higher-timeframe trend
- Lower-timeframe structure
- POI
- Entry
- Stop-loss
- Take-profit
- Strategy
- Risk
- News conditions
- Decision context
- Trade outcome

Journal data can subsequently contribute to the AMEF experience layer.

---

# 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python |
| Web Backend | Django |
| Frontend | TypeScript / modern web UI |
| Styling | Tailwind CSS |
| Database | PostgreSQL |
| Database Platform | Supabase |
| Broker Interface | MetaTrader 5 during development |
| ML | Python ML ecosystem |
| Testing | Python testing ecosystem |
| Version Control | Git / GitHub |
| Deployment Target | Linux-compatible environment |
| Development OS | Windows |

### Stack Badges

<p>
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Django-092E20?style=flat-square&logo=django&logoColor=white" alt="Django">
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white" alt="Tailwind CSS">
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Supabase-3ECF8E?style=flat-square&logo=supabase&logoColor=white" alt="Supabase">
  <img src="https://img.shields.io/badge/Git-F05032?style=flat-square&logo=git&logoColor=white" alt="Git">
  <img src="https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub">
</p>

---

# 📁 Project Structure

The exact repository structure may evolve, but ATHENA is conceptually organized around:

```text
ATHENA/
│
├── backend/
│   ├── authentication/
│   ├── strategies/
│   ├── orchestration/
│   ├── execution/
│   ├── risk/
│   ├── intelligence/
│   ├── ml/
│   ├── memory/
│   ├── news/
│   ├── backtesting/
│   └── database/
│
├── frontend/
│   ├── dashboard/
│   ├── orchestration/
│   ├── executioner/
│   ├── backtesting/
│   ├── journal/
│   └── settings/
│
├── docs/
│
├── tests/
│
├── scripts/
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

> **Important:** The repository itself remains the source of truth. This conceptual structure should be updated as the implementation evolves.

---

# 🖥️ UI & Screenshots

ATHENA follows a **Cybernetic Institutional Obsidian** visual direction.

The UI is intended to provide high information density while maintaining clear visual hierarchy.

### Dashboard

```text
┌──────────────────────────────────────────────────────────────┐
│ ATHENA                                      SYSTEM: ONLINE    │
├─────────────┬────────────────────────────────────────────────┤
│ Dashboard   │  EQUITY        P/L         RISK       MARKET   │
│             │  $XX,XXX       +X.X%       LOW        ACTIVE   │
│ Orchestrator├────────────────────────────────────────────────┤
│ Executioner │  EQUITY CURVE / PERFORMANCE                    │
│ Backtesting │                                                │
│ Journal     │  ───────────────────────────────────────────    │
│ Settings    │                                                │
│             ├────────────────────────────────────────────────┤
│             │  ACTIVE STRATEGIES     SYSTEM ALERTS            │
│             │  SCALPING              ● Normal                 │
│             │  DAY TRADING           ● Monitoring             │
└─────────────┴────────────────────────────────────────────────┘
```

### 📸 Add Actual Screenshots Here

Replace the placeholders below with screenshots as the UI matures.

```text
docs/
└── screenshots/
    ├── dashboard-dark.png
    ├── dashboard-light.png
    ├── orchestrator.png
    ├── executioner.png
    ├── backtesting.png
    └── journal.png
```

Example Markdown:

```markdown
![ATHENA Dashboard](docs/screenshots/dashboard-dark.png)
```

---

# 🚀 Getting Started

## Prerequisites

Before running ATHENA locally, ensure you have:

- Python 3.x
- Node.js / npm
- Git
- PostgreSQL-compatible database access
- Supabase project credentials
- MetaTrader 5 where broker execution is required
- MetaAPI account ID and API token for MetaAPI-backed account validation
- A compatible broker account for live/sandbox testing

> **Important:** MetaTrader 5 integration is environment-dependent. The Python MT5 package is designed around the MetaTrader 5 terminal environment and should not be assumed to work in a Linux-only deployment such as a standard cloud web service.
> MetaAPI connections validate account details during onboarding and store the API token encrypted. Live order execution and ongoing market-data monitoring for MetaAPI accounts are not yet supported.

---

## 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd ATHENA
```

---

## 2. Create a Python Virtual Environment

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. Install Frontend Dependencies

If the frontend contains a Node.js project:

```bash
cd frontend
npm install
cd ..
```

---

## 5. Configure Environment Variables

Copy the example environment file:

### Windows

```powershell
Copy-Item .env.example .env
```

### Linux / macOS

```bash
cp .env.example .env
```

Then populate the required values.

---

# 🔐 Environment Configuration

**Never commit `.env` to GitHub.**

A conceptual `.env.example` may look like:

```env
# -------------------------------------------------
# ATHENA Environment
# -------------------------------------------------

APP_ENV=development
DEBUG=True
SECRET_KEY=change-me

# -------------------------------------------------
# Database / Neon projects

The Django backend reads four Neon PostgreSQL URLs: `ATHENA_CORE_PROD_DATABASE_URL`,
`ATHENA_MARKET_INTELLIGENCE_DATABASE_URL`, `ATHENA_BACKTESTING_LAB_DATABASE_URL`, and
`ATHENA_LEARNING_MEMORY_DATABASE_URL`. Keep these values in the ignored `.env` file.
# -------------------------------------------------

DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE

SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# -------------------------------------------------
# Broker / MT5
# -------------------------------------------------

MT5_LOGIN=your-account-number
MT5_PASSWORD=your-password
MT5_SERVER=your-broker-server

# -------------------------------------------------
# News / Intelligence
# -------------------------------------------------

NEWS_API_KEY=your-news-api-key

# -------------------------------------------------
# ML
# -------------------------------------------------

ML_MODEL_PATH=path/to/model
ML_MODEL_VERSION=development

# -------------------------------------------------
# Application
# -------------------------------------------------

ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

### Security Rules

Do not commit:

```text
.env
broker credentials
database passwords
API keys
private tokens
secret keys
service-role keys
```

Use `.env.example` for documentation and `.env` for local secrets.

---

# ▶️ Development Commands

Because ATHENA contains multiple subsystems, commands may differ as the repository evolves.

## Backend

Example Django development server:

```bash
python manage.py runserver
```

## Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

`python manage.py migrate` applies migrations to all four configured ATHENA databases.
Use `python manage.py migrate --database market_intelligence` to target one database,
or `python manage.py migrate --plan` to preview all four plans. Migration connections
use the direct Neon endpoint when the configured URL uses a `-pooler` host.

User/account/execution and supporting records go to `athena-core-prod`; backtesting
records go to `athena-backtesting-lab`; news snapshots, market samples, and provider
health go to `athena-market-intelligence`; and AMEF records, reaction observations, and
adaptive statistics go to `athena-learning-memory`. Cross-project account/user/news
references are stored as IDs, not database-enforced foreign keys. Migrations do not
copy existing rows between projects; plan a separate data transfer before switching
an existing deployment to this split.

## Frontend

```bash
cd frontend
npm run dev
```

## Production Frontend Build

```bash
npm run build
```

## Render Startup

Set the Render web service's **Start Command** to:

```bash
bash build.sh
```

The script installs Python and frontend dependencies, builds the frontend,
creates and applies Django migrations, collects static files, and starts the
ASGI server. It runs at each service start, so migrations should be committed
to the repository and the Render service should use a persistent production
database. Do not set `bash build.sh` as Render's **Build Command**: it starts
the server, which belongs in the **Start Command**.

## Python Tests

```bash
pytest
```

## Django Tests

```bash
python manage.py test
```

## Code Quality

Where configured:

```bash
ruff check .
```

```bash
black .
```

```bash
mypy .
```

> Use only the commands corresponding to tools actually configured in the repository.

---

# 🧪 Testing

ATHENA should be tested at multiple levels.

```text
                    ┌─────────────────┐
                    │   Unit Tests    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Integration     │
                    │ Tests           │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Backtesting     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Paper / Demo    │
                    │ Trading         │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Controlled Live │
                    │ Testing         │
                    └─────────────────┘
```

No strategy should be considered production-ready solely because it performs well in a limited backtest.

---

# 🌿 Git Workflow

ATHENA follows a feature-oriented development workflow.

Suggested structure:

```text
main
 │
 └── stable / production-ready code

dev
 │
 ├── feature/orchestrator
 ├── feature/executioner
 ├── feature/amef
 ├── feature/ml
 ├── feature/news-sentiment
 └── feature/backtesting
```

Recommended workflow:

```bash
git checkout dev
git pull origin dev

git checkout -b feature/<feature-name>

# Develop and test

git add .
git commit -m "feat: describe the change"

git push origin feature/<feature-name>
```

Features should be reviewed and tested before merging into the stable branch.

---

# 🛣️ Development Roadmap

## Phase I — Foundation

- [x] Core architecture
- [x] Authentication architecture
- [x] PostgreSQL / Supabase integration
- [x] Database foundation
- [x] Market data architecture
- [x] Broker integration foundation

## Phase II — Trading Intelligence

- [x] Technical analysis foundation
- [x] Market structure architecture
- [x] MACD integration architecture
- [x] Multi-timeframe analysis
- [x] News intelligence foundation
- [x] Complete sentiment intelligence pipeline
- [ ] Advanced regime classification

## Phase III — Strategy Layer

- [x] Scalping Engine
- [x] Day Trading Engine
- [x] Strategy abstraction
- [x] Strategy evaluation architecture
- [ ] Expanded strategy library

## Phase IV — Orchestration

- [x] Strategy Orchestrator
- [x] Portfolio governance foundation
- [x] Strategy conflict detection
- [x] Position conflict logging
- [x] Orchestration monitoring
- [ ] Advanced opportunity ranking
- [ ] Advanced portfolio-level optimization

## Phase V — Execution

- [x] Executioner architecture
- [x] Order management foundation
- [x] Position monitoring
- [x] Stop-loss / take-profit handling
- [x] Breakeven management
- [ ] Full production execution hardening
- [ ] Broker abstraction improvements

## Phase VI — Memory

- [x] AMEF architecture
- [ ] Episodic memory implementation
- [ ] Structural memory implementation
- [ ] Counterfactual memory
- [ ] Failure memory
- [ ] Advanced retrieval
- [ ] Memory scoring and decision integration

## Phase VII — Machine Learning

- [ ] Dataset pipeline
- [ ] Feature engineering
- [ ] Model training
- [ ] Model validation
- [ ] Probability calibration
- [ ] Model registry
- [ ] Production inference
- [ ] Drift monitoring
- [ ] Model performance attribution

## Phase VIII — Autonomous Intelligence

- [ ] Context-aware strategy selection
- [ ] Memory-informed decisions
- [ ] Controlled adaptive learning
- [ ] Advanced portfolio intelligence
- [ ] Full end-to-end autonomous decision cycle
- [ ] Production hardening

---

# 📈 Current Development Status

**ATHENA is actively under development.**

The architecture has progressed beyond the initial trading-bot concept into a broader platform containing:

- Strategy engines
- Strategy orchestration
- Portfolio governance
- Execution management
- Backtesting
- News intelligence
- Persistent database architecture
- AMEF design
- ML architecture
- Monitoring and journaling

Several advanced capabilities remain under implementation, particularly:

- Production ML
- Advanced AMEF retrieval
- Regime classification
- Model calibration
- Drift handling
- Full production execution hardening
- Comprehensive end-to-end testing

The README intentionally distinguishes **implemented architecture** from **future/unfinished intelligence**.

---

# 🔐 Security

Security is a core requirement.

### Never commit:

- API keys
- Broker credentials
- Database passwords
- Supabase service-role keys
- Authentication secrets
- Private tokens
- Production `.env` files

### Recommended controls

- Environment variables
- Secret management
- Least-privilege database credentials
- Authentication and authorization
- Input validation
- Audit logging
- Secure production configuration
- Regular dependency updates

---

# ⚠️ Risk Disclaimer

ATHENA is a software development, research, and algorithmic trading project.

**Algorithmic trading involves substantial financial risk.**

ATHENA does not guarantee:

- Profitability
- Consistent returns
- Accurate predictions
- Successful execution
- Protection against market losses

Backtested or simulated results do not guarantee future performance.

ATHENA should be tested progressively:

```text
Development
     ↓
Unit Tests
     ↓
Backtesting
     ↓
Simulation
     ↓
Paper / Demo Trading
     ↓
Controlled Live Testing
```

Live trading should only be performed with appropriate risk controls and capital that the operator can afford to lose.

---

# 🤝 Contributing

ATHENA is currently a privately developed project under **Cypher Develops**.

Contribution access may be restricted while the architecture is under active development.

For authorized contributors:

1. Create a feature branch.
2. Follow the existing architecture.
3. Avoid bypassing governance layers.
4. Add tests for new functionality.
5. Update relevant documentation.
6. Do not commit secrets.
7. Keep commits focused and descriptive.
8. Open a pull request for review.

### Suggested Commit Format

```text
feat: add strategy opportunity scoring
fix: correct execution validation
refactor: separate broker adapter
docs: update AMEF architecture
test: add orchestrator conflict tests
chore: update dependencies
```

---

# 👨‍💻 Developer

## **Cypher Develops**

### Software Architecture • Intelligent Systems • Algorithmic Trading

**Project A.T.H.E.N.A.**

**Algorithmic Trading & High-Execution Network for Assets**

Designed and created by:

### **Cypher**

---

# 📜 License

ATHENA is currently a **private development project**.

Unless explicitly stated otherwise, the source code, architecture, documentation, designs, algorithms, and associated intellectual property are not licensed for:

- Unrestricted redistribution
- Commercial exploitation
- Unauthorized derivative development
- Repackaging
- Resale

A formal software license may be introduced if ATHENA is released publicly or commercially.

---

# 🧠 The ATHENA Principle

ATHENA is not intended to be merely another trading bot.

It is an attempt to build a complete algorithmic trading intelligence architecture.

```text
DATA
  ↓
INFORMATION
  ↓
CONTEXT
  ↓
INTELLIGENCE
  ↓
DECISION
  ↓
GOVERNANCE
  ↓
EXECUTION
  ↓
OBSERVATION
  ↓
EXPERIENCE
  ↓
MEMORY
  ↓
LEARNING
  ↓
BETTER FUTURE DECISIONS
```

### **PROJECT A.T.H.E.N.A.**

> **Algorithmic Trading & High-Execution Network for Assets**

**Designed & Created by Cypher**

**Cypher Develops — A Software Company**

---

<p align="center">
  <strong>© Cypher Develops. All rights reserved.</strong>
</p>

<p align="center">
  Built with Python • PostgreSQL • Supabase • TypeScript • Intelligence • Discipline
</p>
