# Video Analyzer

AI-powered video analysis platform that predicts viral potential using Claude Vision.

## Features

- **Video Upload & Analysis**: Upload videos and get AI-powered analysis of viral potential
- **Pattern Detection**: Extracts hook types, emotions, pacing, and visual elements
- **Viral Prediction**: Uses Markov Chain to predict viral probability based on benchmark data
- **Recommendations**: Thompson Sampling suggests optimal patterns for new videos
- **Benchmark Library**: Reference database of successful video patterns

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL, Redis
- **Frontend**: React, Vite, Tailwind CSS
- **AI**: Claude Vision API (Anthropic)
- **Storage**: Cloudflare R2 (S3-compatible)
- **ML**: Markov Chain, Thompson Sampling (Multi-Armed Bandit)

## Quick Start

### Using Docker

```bash
# Start all services
make dev

# Or with docker-compose directly
docker-compose up --build
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your credentials

# Run database migrations
alembic upgrade head

# Seed benchmark data
python scripts/seed_benchmarks.py

# Start API
make local-dev

# Start frontend (in another terminal)
cd frontend
npm install
npm run dev
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login (form data)
- `POST /api/v1/auth/login/json` - Login (JSON)
- `GET /api/v1/auth/me` - Get current user
- `POST /api/v1/auth/refresh` - Refresh token

### Videos
- `POST /api/v1/videos/upload` - Upload video for analysis
- `GET /api/v1/videos` - List user's videos
- `GET /api/v1/videos/{id}` - Get video details
- `GET /api/v1/videos/{id}/analysis` - Get analysis results
- `POST /api/v1/videos/{id}/analyze` - Trigger re-analysis
- `DELETE /api/v1/videos/{id}` - Delete video

### Benchmarks
- `GET /api/v1/benchmarks/patterns` - Get top patterns
- `GET /api/v1/benchmarks/videos` - List benchmark videos
- `GET /api/v1/benchmarks/stats` - Get benchmark statistics

### Recommendations
- `GET /api/v1/recommendations/videos/{id}/recommendations` - Get video improvement suggestions
- `GET /api/v1/recommendations/patterns` - Get recommended patterns (Thompson Sampling)
- `GET /api/v1/recommendations/compare` - Compare pattern combinations
- `GET /api/v1/recommendations/trending` - Get trending patterns

## Environment Variables

See `.env.example` for all required variables:

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - JWT secret key
- `ANTHROPIC_API_KEY` - Claude API key
- `R2_*` - Cloudflare R2 credentials

## Project Structure

```
video-analyzer/
├── api/                    # FastAPI application
│   ├── main.py            # App entry point
│   ├── dependencies.py    # Auth dependencies
│   └── routers/           # API endpoints
├── database/              # Database layer
│   ├── base.py           # SQLAlchemy setup
│   ├── models.py         # SQLAlchemy models
│   └── schemas.py        # Pydantic schemas
├── utils/                 # Utility modules
│   ├── video_analyzer.py # Claude Vision integration
│   ├── markov_chain.py   # Viral prediction
│   ├── thompson_sampling.py # Pattern recommendations
│   ├── storage.py        # R2 storage adapter
│   └── security.py       # Security utilities
├── frontend/              # React UI
├── alembic/              # Database migrations
└── scripts/              # Utility scripts
```

## License

Private - All rights reserved.
