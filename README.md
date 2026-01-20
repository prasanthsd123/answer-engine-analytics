# Answer Engine Analytics

A comprehensive platform to monitor your brand's visibility across AI search engines (ChatGPT, Claude, Perplexity, Gemini). Generate research questions, analyze AI responses for brand mentions, sentiment, and citations, and track your competitive position.

## Features

- **Brand Monitoring**: Track how AI platforms mention and describe your brand
- **Question Generation**: Automatically generate relevant research questions based on your brand profile
- **Multi-Platform Analysis**: Query ChatGPT, Claude, Perplexity, and Gemini
- **Sentiment Analysis**: Understand how AI perceives your brand (positive/negative/neutral)
- **Citation Tracking**: See which sources AI platforms cite when discussing your brand
- **Competitor Benchmarking**: Compare your visibility against competitors (Share of Voice)
- **Historical Trending**: Track changes in visibility and sentiment over time
- **Automated Reporting**: Generate PDF/CSV reports for stakeholders

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (Next.js)                          │
│   Dashboard │ Reports │ Brand Setup │ Query Builder │ Settings  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   API GATEWAY (FastAPI)                          │
│              Authentication │ Rate Limiting │ Routing            │
└─────────────────────────────────────────────────────────────────┘
                                │
       ┌────────────────────────┼────────────────────────┐
       ▼                        ▼                        ▼
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Brand     │         │   Query     │         │  Analysis   │
│   Service   │         │   Engine    │         │   Service   │
└─────────────┘         └─────────────┘         └─────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI ADAPTERS LAYER                             │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│   │ ChatGPT  │  │  Claude  │  │Perplexity│  │  Gemini  │       │
│   │ (OpenAI) │  │(Anthropic)│ │  (API)   │  │ (Google) │       │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKGROUND WORKERS (Celery)                   │
│        Query Execution │ Analysis Pipeline │ Report Generation  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │
│  │ PostgreSQL│  │   Redis   │  │    S3     │  │ElasticSrch│    │
│  │   (RDS)   │  │(ElastiCch)│  │ (Reports) │  │ (Search)  │    │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

### Backend
- **Framework**: Python 3.11 + FastAPI
- **Database**: PostgreSQL with SQLAlchemy (async)
- **Cache**: Redis
- **Task Queue**: Celery
- **AI/ML**: HuggingFace Transformers, spaCy

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS
- **State**: TanStack Query + Zustand
- **Charts**: Recharts

### Infrastructure
- **Cloud**: AWS (ECS, RDS, ElastiCache, S3)
- **Container**: Docker
- **CI/CD**: GitHub Actions

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Node.js 20+
- Python 3.11+
- API keys for: OpenAI, Anthropic, Perplexity, Google AI

### Quick Start with Docker

1. Clone the repository:
```bash
git clone https://github.com/yourusername/answer-engine-analytics.git
cd answer-engine-analytics
```

2. Copy environment files:
```bash
cp backend/.env.example backend/.env
```

3. Edit `backend/.env` with your API keys:
```env
OPENAI_API_KEY=sk-your-key
ANTHROPIC_API_KEY=sk-ant-your-key
PERPLEXITY_API_KEY=pplx-your-key
GOOGLE_AI_API_KEY=your-key
```

4. Start the services:
```bash
cd backend
docker-compose up -d
```

5. Run database migrations:
```bash
docker-compose exec api alembic upgrade head
```

6. Start the frontend:
```bash
cd frontend
npm install
npm run dev
```

7. Open http://localhost:3000 in your browser

### Manual Setup

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start PostgreSQL and Redis (or use Docker)
# Then run migrations
alembic upgrade head

# Start the API
uvicorn src.main:app --reload

# In another terminal, start Celery worker
celery -A src.workers.celery_app worker --loglevel=info
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | Register new user |
| `/api/auth/login` | POST | Login and get token |
| `/api/brands` | GET/POST | List/create brands |
| `/api/brands/{id}` | GET/PUT/DELETE | Manage brand |
| `/api/questions/brand/{id}` | GET/POST | List/create questions |
| `/api/questions/brand/{id}/generate` | POST | Auto-generate questions |
| `/api/analysis/brand/{id}/overview` | GET | Get visibility overview |
| `/api/analysis/brand/{id}/run` | POST | Trigger analysis |
| `/api/reports/brand/{id}/summary` | GET | Get report summary |

## Project Structure

```
answer-engine-analytics/
├── backend/
│   ├── src/
│   │   ├── api/routes/         # API endpoints
│   │   ├── adapters/           # AI platform integrations
│   │   ├── models/             # Database models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # Business logic
│   │   ├── nlp/                # NLP/analysis services
│   │   ├── workers/            # Celery tasks
│   │   ├── config.py           # Configuration
│   │   ├── database.py         # DB setup
│   │   └── main.py             # FastAPI app
│   ├── alembic/                # DB migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                # Next.js pages
│   │   ├── components/         # React components
│   │   ├── lib/                # Utilities & API client
│   │   └── hooks/              # Custom hooks
│   ├── package.json
│   └── Dockerfile
└── README.md
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `SECRET_KEY` | JWT secret key | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `ANTHROPIC_API_KEY` | Anthropic API key | Yes |
| `PERPLEXITY_API_KEY` | Perplexity API key | Yes |
| `GOOGLE_AI_API_KEY` | Google AI API key | Yes |

## Deployment

### CI/CD Pipeline

The project includes a GitHub Actions workflow (`.github/workflows/ci.yml`) that:

1. **Tests**: Runs backend tests with PostgreSQL and Redis
2. **Lints**: Checks code quality with ruff (backend) and ESLint (frontend)
3. **Builds**: Creates Docker images for backend and frontend
4. **Deploys**: Pushes to AWS ECS on merge to main

#### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `DOCKER_USERNAME` | Docker Hub username |
| `DOCKER_PASSWORD` | Docker Hub password/token |
| `AWS_ACCESS_KEY_ID` | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key |
| `AWS_REGION` | AWS region (e.g., us-east-1) |
| `ECS_CLUSTER` | ECS cluster name |
| `ECS_SERVICE_BACKEND` | Backend ECS service name |
| `ECS_SERVICE_FRONTEND` | Frontend ECS service name |
| `API_URL` | Production API URL |

### AWS Deployment

The platform is designed to run on AWS with:
- **ECS Fargate** for containers
- **RDS PostgreSQL** for database
- **ElastiCache Redis** for caching
- **S3** for report storage
- **ALB** for load balancing

Terraform configurations are provided in `infrastructure/terraform/`.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.

## Acknowledgments

- Inspired by [Profound](https://tryprofound.com), [Otterly.AI](https://otterly.ai), and [Knowatoa](https://knowatoa.com)
- Built with FastAPI, Next.js, and modern AI APIs
