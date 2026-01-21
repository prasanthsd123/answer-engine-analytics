# Answer Engine Analytics - Architecture & Flow

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER BROWSER                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js on Vercel)                         │
│  https://frontend-bice-phi-50.vercel.app                                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  Dashboard  │ │  Analysis   │ │   Brands    │ │  Questions  │           │
│  │    Page     │ │    Page     │ │    CRUD     │ │   Manager   │           │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Next.js Rewrites (/api/* → backend)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI on AWS ECS)                            │
│  answer-engine-alb-157996493.us-east-1.elb.amazonaws.com                    │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         API ROUTES                                    │   │
│  │  /api/auth/*  │  /api/brands/*  │  /api/questions/*  │  /api/analysis/*│  │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      SERVICES LAYER                                   │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐       │   │
│  │  │AnalysisRunner   │  │QuestionGenerator│  │ ReportService   │       │   │
│  │  │(Orchestrator)   │  │(AI-powered)     │  │(CSV/JSON export)│       │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      AI ADAPTERS                                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐              │   │
│  │  │ ChatGPT  │  │  Claude  │  │Perplexity│  │  Gemini  │              │   │
│  │  │ (OpenAI) │  │(Anthropic)│ │   API    │  │ (Google) │              │   │
│  │  │    ✓     │  │    ✗     │  │    ✓     │  │    ✗     │              │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      NLP PROCESSING                                   │   │
│  │  ┌─────────────────┐  ┌─────────────────┐                            │   │
│  │  │SentimentAnalyzer│  │ CitationParser  │                            │   │
│  │  │(Brand mentions) │  │ (URL extraction)│                            │   │
│  │  └─────────────────┘  └─────────────────┘                            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER (AWS RDS)                                 │
│  PostgreSQL Database                                                         │
│  ┌─────────┐ ┌─────────┐ ┌───────────┐ ┌────────────┐ ┌──────────────┐     │
│  │  Users  │ │ Brands  │ │ Questions │ │ Executions │ │AnalysisResults│     │
│  └─────────┘ └─────────┘ └───────────┘ └────────────┘ └──────────────┘     │
│                                        ┌──────────────┐                      │
│                                        │ DailyMetrics │                      │
│                                        └──────────────┘                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Analysis Flow (When You Click "Run Analysis")

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: User Triggers Analysis                                               │
│ ────────────────────────────────────────────────────────────────────────────│
│  Frontend: POST /api/analysis/brand/{id}/run?platforms=chatgpt&platforms=perplexity
│  Backend: Returns 202 Accepted immediately, spawns background task           │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 2: AnalysisRunner Initializes                                           │
│ ────────────────────────────────────────────────────────────────────────────│
│  • Loads API keys from environment                                           │
│  • Initializes adapters: ChatGPT ✓, Perplexity ✓                            │
│  • Fetches brand's active questions from database                            │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 3: Query AI Platforms (Per Question, Per Platform)                      │
│ ────────────────────────────────────────────────────────────────────────────│
│                                                                              │
│  Question: "What is the best CRM software in 2025?"                         │
│                                                                              │
│  ┌─────────────────┐              ┌─────────────────┐                       │
│  │    ChatGPT      │              │   Perplexity    │                       │
│  │   (gpt-4o)      │              │ (sonar-pro)     │                       │
│  └────────┬────────┘              └────────┬────────┘                       │
│           │                                │                                 │
│           ▼                                ▼                                 │
│  "The best CRM software        "Top CRM solutions include                   │
│   includes Salesforce,          Salesforce, HubSpot, and                    │
│   HubSpot, Zoho..."            Zoho. [Source: G2.com]..."                   │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 4: Store Query Execution                                                │
│ ────────────────────────────────────────────────────────────────────────────│
│  QueryExecution record:                                                      │
│  • question_id: UUID                                                         │
│  • platform: "chatgpt" / "perplexity"                                       │
│  • raw_response: Full AI response text                                       │
│  • response_time_ms: 1234                                                    │
│  • status: "completed"                                                       │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 5: Analyze Response                                                     │
│ ────────────────────────────────────────────────────────────────────────────│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Brand Mention Detection                                              │    │
│  │ ─────────────────────────────────────────────────────────────────── │    │
│  │ Search for: "YourBrand" (case-insensitive)                          │    │
│  │ Result: brand_mentioned = true/false, mention_count = N             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Sentiment Analysis                                                   │    │
│  │ ─────────────────────────────────────────────────────────────────── │    │
│  │ Extract context around brand mention                                 │    │
│  │ Analyze: positive (+1) / neutral (0) / negative (-1)                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Position Detection                                                   │    │
│  │ ─────────────────────────────────────────────────────────────────── │    │
│  │ Look for: "1. YourBrand", "#2: YourBrand", etc.                     │    │
│  │ Result: position = 1, 2, 3... or null                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ Citation Extraction                                                  │    │
│  │ ─────────────────────────────────────────────────────────────────── │    │
│  │ Extract URLs from response (especially Perplexity)                  │    │
│  │ Result: ["https://g2.com/...", "https://forbes.com/..."]           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 6: Store Analysis Result                                                │
│ ────────────────────────────────────────────────────────────────────────────│
│  AnalysisResult record:                                                      │
│  • execution_id: UUID (links to QueryExecution)                             │
│  • brand_mentioned: true                                                     │
│  • mention_count: 2                                                          │
│  • sentiment: "positive"                                                     │
│  • sentiment_score: 0.85                                                     │
│  • position: 3                                                               │
│  • citations: ["https://..."]                                               │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 7: Update Daily Metrics                                                 │
│ ────────────────────────────────────────────────────────────────────────────│
│  DailyMetrics (aggregated for dashboard):                                    │
│  • visibility_score: 0-100 (based on mentions + sentiment)                  │
│  • sentiment_avg: -1 to +1                                                   │
│  • mention_count: Total mentions today                                       │
│  • platform_breakdown: { "chatgpt": {...}, "perplexity": {...} }            │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    Users    │       │   Brands    │       │ Competitors │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │──┐    │ id (PK)     │──┐    │ id (PK)     │
│ email       │  │    │ user_id(FK) │◄─┘    │ brand_id(FK)│
│ password    │  │    │ name        │◄──────│ name        │
│ full_name   │  └───►│ domain      │       │ domain      │
│ created_at  │       │ keywords    │       └─────────────┘
└─────────────┘       │ industry    │
                      └─────────────┘
                            │
                            ▼
                      ┌─────────────┐
                      │  Questions  │
                      ├─────────────┤
                      │ id (PK)     │
                      │ brand_id(FK)│
                      │ question_txt│
                      │ category    │
                      │ is_active   │
                      └─────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │QueryExecutions│
                    ├───────────────┤
                    │ id (PK)       │
                    │ question_id   │
                    │ platform      │──────► "chatgpt" | "perplexity"
                    │ raw_response  │
                    │ response_time │
                    │ status        │
                    │ executed_at   │
                    └───────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │AnalysisResults│
                    ├───────────────┤
                    │ id (PK)       │
                    │ execution_id  │
                    │brand_mentioned│──────► true/false
                    │ mention_count │
                    │ sentiment     │──────► positive/neutral/negative
                    │sentiment_score│──────► -1.0 to +1.0
                    │ position      │──────► 1, 2, 3... (rank in list)
                    │ citations     │──────► ["url1", "url2"]
                    └───────────────┘

                      ┌─────────────┐
                      │DailyMetrics │  (Aggregated for Dashboard)
                      ├─────────────┤
                      │ id (PK)     │
                      │ brand_id    │
                      │ date        │
                      │visibility_sc│──────► 0-100 score
                      │sentiment_avg│
                      │mention_count│
                      │share_of_voic│
                      │platform_brkd│──────► JSON per-platform stats
                      └─────────────┘
```

---

## CI/CD Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          DEVELOPER WORKFLOW                                 │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  git push origin master                                                     │
│  (changes in backend/ folder)                                              │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                    GITHUB ACTIONS TRIGGERED                                 │
│  .github/workflows/deploy-backend.yml                                      │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │ 1. Checkout code                                                      │ │
│  │ 2. Configure AWS credentials (from GitHub Secrets)                   │ │
│  │ 3. Login to Amazon ECR                                               │ │
│  │ 4. Build Docker image (cd backend && docker build)                   │ │
│  │ 5. Tag and push to ECR                                               │ │
│  │ 6. Update ECS service (force new deployment)                         │ │
│  │ 7. Wait for ECS to stabilize                                         │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         AWS INFRASTRUCTURE                                  │
│                                                                            │
│  ECR Repository                    ECS Cluster                             │
│  ┌─────────────────┐              ┌─────────────────┐                     │
│  │ answer-engine/  │─────────────►│ answer-engine-  │                     │
│  │ backend:latest  │   (pull)     │ backend service │                     │
│  └─────────────────┘              └────────┬────────┘                     │
│                                            │                               │
│                                            ▼                               │
│                                   ┌─────────────────┐                     │
│                                   │   Fargate Task  │                     │
│                                   │ (Docker container)                    │
│                                   └────────┬────────┘                     │
│                                            │                               │
│                                            ▼                               │
│                                   ┌─────────────────┐                     │
│                                   │      ALB        │                     │
│                                   │ (Load Balancer) │                     │
│                                   └─────────────────┘                     │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Metrics Calculated

| Metric | Formula | Range |
|--------|---------|-------|
| **Visibility Score** | `mention_rate × 50 + (sentiment + 1) × 25` | 0-100 |
| **Sentiment Score** | Average of all sentiment_scores | -1 to +1 |
| **Mention Rate** | `mentions / total_queries` | 0-1 |
| **Position** | Rank in AI's recommendation list | 1, 2, 3... |

---

## Technology Stack Summary

| Layer | Technology | Hosting |
|-------|------------|---------|
| Frontend | Next.js 14 + React + TailwindCSS | Vercel |
| Backend | Python 3.11 + FastAPI | AWS ECS Fargate |
| Database | PostgreSQL + SQLAlchemy | AWS RDS |
| Auth | JWT tokens | - |
| AI Platforms | OpenAI (ChatGPT), Perplexity | External APIs |
| CI/CD | GitHub Actions | GitHub |
| Container Registry | Amazon ECR | AWS |
| Load Balancer | Application Load Balancer | AWS |

---

## Project Structure

```
answer-engine-analytics/
├── .github/
│   └── workflows/
│       └── deploy-backend.yml      # CI/CD for backend
│
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── auth.py         # Authentication endpoints
│   │   │   │   ├── brands.py       # Brand CRUD
│   │   │   │   ├── questions.py    # Question management
│   │   │   │   ├── analysis.py     # Analysis triggers & metrics
│   │   │   │   └── reports.py      # Export endpoints
│   │   │   └── deps.py             # Dependencies (auth, db)
│   │   │
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── brand.py
│   │   │   ├── question.py
│   │   │   ├── execution.py
│   │   │   └── analysis.py
│   │   │
│   │   ├── services/
│   │   │   ├── analysis_runner.py  # Main orchestrator
│   │   │   └── question_generator.py
│   │   │
│   │   ├── adapters/
│   │   │   ├── base.py             # Abstract base adapter
│   │   │   ├── chatgpt.py          # OpenAI integration
│   │   │   ├── claude.py           # Anthropic integration
│   │   │   ├── perplexity.py       # Perplexity integration
│   │   │   └── gemini.py           # Google AI integration
│   │   │
│   │   ├── nlp/
│   │   │   ├── sentiment.py        # Sentiment analysis
│   │   │   └── citation_parser.py  # URL extraction
│   │   │
│   │   ├── config.py               # Environment settings
│   │   ├── database.py             # DB connection
│   │   └── main.py                 # FastAPI app
│   │
│   ├── Dockerfile
│   ├── requirements.txt
│   └── buildspec.yml               # AWS CodeBuild (legacy)
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── (dashboard)/
│   │   │   │   ├── page.tsx        # Dashboard
│   │   │   │   ├── analysis/       # Analysis page
│   │   │   │   ├── brands/         # Brand management
│   │   │   │   └── questions/      # Question management
│   │   │   └── layout.tsx
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                 # Reusable UI components
│   │   │   └── charts/             # Chart components
│   │   │
│   │   └── lib/
│   │       ├── api.ts              # API client
│   │       └── utils.ts
│   │
│   ├── next.config.js              # API rewrites
│   └── package.json
│
├── architecture.md                  # This file
└── README.md
```

---

## Environment Variables

### Backend (ECS Task Definition)

```
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
SECRET_KEY=your-jwt-secret
OPENAI_API_KEY=sk-...
PERPLEXITY_API_KEY=pplx-...
ANTHROPIC_API_KEY=sk-ant-...      # Optional
GOOGLE_AI_API_KEY=...             # Optional
```

### Frontend (Vercel)

```
# API calls go through Next.js rewrites to backend ALB
# No direct backend URL needed in frontend
```

### GitHub Secrets (CI/CD)

```
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

---

## URLs

| Service | URL |
|---------|-----|
| Frontend (Vercel) | https://frontend-bice-phi-50.vercel.app |
| Backend (AWS ALB) | http://answer-engine-alb-157996493.us-east-1.elb.amazonaws.com |
| GitHub Actions | https://github.com/prasanthsd123/answer-engine-analytics/actions |
| AWS ECR | 211125724509.dkr.ecr.us-east-1.amazonaws.com/answer-engine/backend |
