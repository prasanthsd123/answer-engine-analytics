# Answer Engine Analytics - Project Reference

## Quick Links

| Environment | URL |
|-------------|-----|
| **Frontend (Vercel)** | https://frontend-bice-phi-50.vercel.app |
| **Backend (AWS ECS)** | http://answer-engine-alb-157996493.us-east-1.elb.amazonaws.com |
| **GitHub Repo** | https://github.com/prasanthsd123/answer-engine-analytics |

---

## Project Structure

```
answer-engine-analytics/
├── backend/                    # FastAPI Python Backend
│   ├── src/
│   │   ├── adapters/          # AI Platform Adapters
│   │   │   ├── base.py        # BaseAIAdapter class
│   │   │   ├── chatgpt.py     # OpenAI ChatGPT
│   │   │   ├── claude.py      # Anthropic Claude
│   │   │   ├── perplexity.py  # Perplexity AI (sonar-pro)
│   │   │   └── gemini.py      # Google Gemini
│   │   ├── api/routes/        # API Endpoints
│   │   │   ├── auth.py        # /api/auth/*
│   │   │   ├── brands.py      # /api/brands/*
│   │   │   ├── questions.py   # /api/questions/*
│   │   │   ├── analysis.py    # /api/analysis/*
│   │   │   └── reports.py     # /api/reports/*
│   │   ├── models/            # SQLAlchemy Models
│   │   ├── nlp/               # NLP Processing
│   │   │   ├── entity_extraction.py
│   │   │   ├── sentiment.py
│   │   │   └── citation_parser.py
│   │   ├── services/          # Business Logic
│   │   │   ├── analysis_runner.py
│   │   │   ├── smart_question_generator.py
│   │   │   └── website_crawler.py
│   │   └── core/              # Config, DB, Auth
│   └── requirements.txt
│
├── frontend/                   # Next.js React Frontend
│   ├── src/
│   │   ├── app/(dashboard)/   # Dashboard Pages
│   │   │   ├── dashboard/
│   │   │   ├── brands/
│   │   │   ├── questions/
│   │   │   ├── analysis/
│   │   │   ├── reports/
│   │   │   └── settings/
│   │   ├── components/        # React Components
│   │   └── lib/
│   │       ├── api.ts         # API Client
│   │       └── auth.ts        # Auth Context
│   └── next.config.js         # API Rewrites
│
└── .github/workflows/         # CI/CD
    ├── ci.yml                 # Tests + Deploy
    └── deploy-backend.yml     # AWS ECS Deploy
```

---

## Backend API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, returns JWT |
| GET | `/api/auth/me` | Get current user |

### Brands
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/brands` | List user's brands |
| POST | `/api/brands` | Create new brand |
| GET | `/api/brands/{id}` | Get brand details |
| PUT | `/api/brands/{id}` | Update brand |
| DELETE | `/api/brands/{id}` | Delete brand |

### Questions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/questions/brand/{id}` | List questions for brand |
| POST | `/api/questions/brand/{id}` | Create question manually |
| POST | `/api/questions/brand/{id}/generate-smart` | **AI-generate questions** |
| DELETE | `/api/questions/{id}` | Delete question |

**Smart Generation Request:**
```json
{
  "num_questions": 20,
  "research_website": true,
  "focus_intents": ["discovery", "comparison"],
  "additional_urls": ["/pricing", "/features", "https://example.com/docs"]
}
```

### Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analysis/run` | Run analysis for brand |
| GET | `/api/analysis/brand/{id}/results` | Get analysis results |
| GET | `/api/analysis/brand/{id}/metrics` | Get daily metrics |
| GET | `/api/analysis/brand/{id}/citations` | Get citation analytics |

**Run Analysis Request:**
```json
{
  "brand_id": "uuid",
  "platforms": ["chatgpt", "claude", "perplexity", "gemini"],
  "max_questions": 50
}
```

### Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/reports/brand/{id}` | List reports |
| POST | `/api/reports/brand/{id}/generate` | Generate new report |
| GET | `/api/reports/{id}/download` | Download PDF |

---

## Frontend Pages

| Route | Page | Description |
|-------|------|-------------|
| `/login` | Login | User authentication |
| `/dashboard` | Dashboard | Overview metrics, charts |
| `/brands` | Brands | Manage brands |
| `/brands/[id]` | Brand Detail | Single brand view |
| `/questions` | Questions | Manage & generate questions |
| `/analysis` | Analysis | Run analysis, view results |
| `/reports` | Reports | Generate & download reports |
| `/settings` | Settings | User settings, API keys |

---

## 4-Phase Analysis Engine

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI Response Input                             │
│            (ChatGPT / Claude / Perplexity / Gemini)             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│  PHASE 1: BASIC ANALYSIS                                        │
│  ├── Brand mention extraction & counting                        │
│  ├── Sentiment analysis (positive/neutral/negative)             │
│  ├── Position in recommendation lists (1st, 2nd, 3rd)          │
│  └── Competitor mention tracking                                │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│  PHASE 2: ENHANCED CITATION ANALYSIS                            │
│  ├── Source attribution (brand-attributed vs general)           │
│  ├── Source type (review_site, news, blog, community)          │
│  └── Authority scoring (G2: 0.95, Forbes: 0.90, Reddit: 0.50)  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│  PHASE 3: CONTEXTUAL MENTION ANALYSIS                           │
│  ├── Mention type (recommendation/criticism/comparison)         │
│  ├── Comparison target detection (Brand vs Competitor)          │
│  ├── Win/Loss tracking in comparisons                          │
│  └── Aspect tracking (pricing, features, support, etc.)        │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│  PHASE 4: ASPECT-BASED SENTIMENT                                │
│  ├── Sentiment per aspect (pricing: -0.3, features: +0.7)      │
│  ├── Evidence snippets for each aspect                          │
│  └── Dominant aspect identification                             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ AnalysisResult  │
                    │   (Database)    │
                    └─────────────────┘
```

### Key Files
- **Orchestrator:** `backend/src/services/analysis_runner.py`
- **Entity Extraction:** `backend/src/nlp/entity_extraction.py`
- **Sentiment:** `backend/src/nlp/sentiment.py`
- **Citations:** `backend/src/nlp/citation_parser.py`

### Mention Types
| Type | Pattern Example |
|------|-----------------|
| `recommendation` | "I recommend Brand", "Brand is the best" |
| `criticism` | "avoid Brand", "Brand is expensive" |
| `comparison` | "Brand vs Competitor", "better than" |
| `feature_highlight` | "Brand offers X feature" |
| `neutral` | Factual mention without sentiment |

### 7 Tracked Aspects
1. **pricing** - cost, price, plans, subscription
2. **features** - capabilities, functionality
3. **support** - customer service, help, documentation
4. **ease_of_use** - UI, UX, learning curve
5. **performance** - speed, reliability, uptime
6. **integration** - API, plugins, compatibility
7. **security** - privacy, encryption, compliance

### Authority Scores
| Domain | Score |
|--------|-------|
| G2, Gartner, Forrester | 0.95 |
| Capterra, TechCrunch, Forbes | 0.90 |
| Trustpilot, The Verge | 0.85 |
| Wikipedia | 0.80 |
| News sites (default) | 0.75 |
| Reddit, Stack Overflow | 0.50 |
| Blogs | 0.45 |

---

## Smart Question Generation

### Distribution (Current)
| Intent | Percentage | Example |
|--------|------------|---------|
| Discovery | **40%** | "best CRM software 2024" |
| Comparison | 15% | "HubSpot vs Salesforce" |
| Evaluation | 12% | "is Brand worth it" |
| Feature | 12% | "Brand integrations" |
| Problem-solving | 8% | "how to automate sales" |
| Industry | 8% | "CRM for healthcare" |
| Pricing | 5% | "Brand pricing plans" |

### Smart Crawling Flow
```
1. Fetch sitemap.xml → Extract URLs
2. Parse navigation links → Discover pages
3. Add user-provided URLs → /pricing, /features
4. Crawl pages → Extract content
5. GPT-4o analyzes → Generates questions
```

**File:** `backend/src/services/smart_question_generator.py`

---

## AI Platform Adapters

### Supported Platforms
| Platform | Model | Rate Limit |
|----------|-------|------------|
| ChatGPT | gpt-4o | 60 RPM |
| Claude | claude-3-5-sonnet | 50 RPM |
| Perplexity | sonar-pro | 20 RPM |
| Gemini | gemini-1.5-pro | 60 RPM |

### Perplexity API (Latest)
```python
payload = {
    "model": "sonar-pro",
    "messages": [...],
    "return_related_questions": True,
    "web_search_options": {
        "search_recency_filter": "month"
    }
}

# Response includes:
# - search_results: [{url, title, date}]
# - citations: [url1, url2]  (legacy fallback)
```

**File:** `backend/src/adapters/perplexity.py`

---

## Database Models

### Core Tables
| Table | Description |
|-------|-------------|
| `users` | User accounts |
| `brands` | Brand configurations |
| `questions` | Generated/manual questions |
| `query_executions` | Individual query runs |
| `analysis_results` | Per-query analysis (all 4 phases) |
| `daily_metrics` | Aggregated daily stats |
| `reports` | Generated PDF reports |

### Key Relationships
```
User (1) ──► (N) Brand
Brand (1) ──► (N) Question
Brand (1) ──► (N) QueryExecution
QueryExecution (1) ──► (1) AnalysisResult
Brand (1) ──► (N) DailyMetrics
```

---

## Environment Variables

### Backend (.env)
```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
SECRET_KEY=your-secret-key

# AI API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
PERPLEXITY_API_KEY=pplx-...
GOOGLE_API_KEY=...
```

### Frontend (.env.production)
```env
NEXT_PUBLIC_API_URL=http://answer-engine-alb-157996493.us-east-1.elb.amazonaws.com
BACKEND_URL=http://answer-engine-alb-157996493.us-east-1.elb.amazonaws.com
```

---

## Deployment

### GitHub Actions (Auto-Deploy)
- **Push to master** triggers:
  - `deploy-backend.yml` → AWS ECS
  - `ci.yml` → Tests + Build

### Manual Vercel Deploy
```bash
cd frontend
npx vercel --prod
```

### AWS Architecture
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Route 53  │────►│     ALB     │────►│  ECS Fargate│
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                    ┌─────────────┬───────────┴───────────┐
                    │             │                       │
              ┌─────▼─────┐ ┌─────▼─────┐          ┌─────▼─────┐
              │  Backend  │ │ Frontend  │          │    RDS    │
              │ Container │ │ Container │          │ PostgreSQL│
              └───────────┘ └───────────┘          └───────────┘
```

---

## Common Commands

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev          # Development
npm run build        # Production build
npm run type-check   # TypeScript check
```

### Database
```bash
# Clear all data (use with caution)
cd backend
python scripts/clear_database.py

# Run migrations
alembic upgrade head
```

### Git
```bash
git add .
git commit -m "message"
git push origin master  # Triggers auto-deploy
```

---

## Troubleshooting

### Backend not responding
1. Check AWS ECS service status
2. Check CloudWatch logs
3. Verify environment variables in ECS task definition

### Frontend API errors
1. Check `next.config.js` rewrites
2. Verify BACKEND_URL in Vercel environment
3. Check browser network tab for CORS issues

### Analysis not running
1. Verify API keys are set (OpenAI, Anthropic, etc.)
2. Check rate limits (especially Perplexity: 20 RPM)
3. Look at backend logs for adapter errors

---

## Key Metrics Calculated

| Metric | Formula |
|--------|---------|
| **Visibility Score** | (mention_rate × 40) + (avg_position_score × 30) + (sentiment × 30) |
| **Share of Voice** | brand_mentions / (brand_mentions + competitor_mentions) × 100 |
| **Citation Quality** | avg(authority_scores) across all citations |
| **Sentiment Score** | Range: -1.0 (negative) to +1.0 (positive) |

---

## Contact & Resources

- **GitHub Issues:** https://github.com/prasanthsd123/answer-engine-analytics/issues
- **Vercel Dashboard:** https://vercel.com/dashboard
- **AWS Console:** https://console.aws.amazon.com
