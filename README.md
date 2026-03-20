# AI-Powered Global Ontology Engine

A real-time knowledge graph system that ingests multi-domain data (geopolitics, economics, defense, technology, climate, society) to provide AI-driven strategic insights with an interactive world map visualization.

## Features

- **Multi-Source Data Ingestion**: RSS feeds, NewsAPI, web scraping
- **Knowledge Graph**: Neo4j-based ontology with entities and relationships
- **GraphRAG**: AI-powered question answering using retrieval augmented generation
- **Real-time Insights**: Risk analysis, trend visualization, impact mapping
- **Interactive World Map**: Animated visualization with country-wise impact data
- **Risk Analysis Dashboard**: Category-based risk assessment with trend analysis

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │     │   Backend       │     │   Databases     │
│   (React)       │◄───►│   (FastAPI)     │◄───►│   Neo4j         │
│                 │     │                 │     │   PostgreSQL    │
│   Port: 3000    │     │   Port: 8000    │     │   Redis         │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │   Celery Workers         │
                    │   (Background Tasks)     │
                    └─────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API Key
- NewsAPI Key (optional)

### Setup

1. **Clone the repository**

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Start the application**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Neo4j Browser: http://localhost:7474

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for GPT models | Yes |
| `NEWS_API_KEY` | NewsAPI key for news ingestion | No |
| `NEO4J_URI` | Neo4j connection URI | Yes |
| `NEO4J_PASSWORD` | Neo4j password | Yes |
| `POSTGRES_URI` | PostgreSQL connection URI | Yes |
| `REDIS_URL` | Redis connection URL | Yes |

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/endpoints/     # API routes
│   │   ├── database/          # Database clients
│   │   ├── config.py          # Configuration
│   │   └── main.py            # FastAPI app
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/             # React pages
│   │   ├── components/        # React components
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## API Endpoints

### Health
- `GET /api/health` - System health check

### Query
- `POST /api/query` - Ask questions to the knowledge graph

### Insights
- `GET /api/insights/risk` - Get risk analysis
- `GET /api/insights/map` - Get map visualization data
- `GET /api/insights/trends` - Get trend data

### News
- `GET /api/news/articles` - Get ingested articles
- `GET /api/news/sources` - Get news sources
- `POST /api/news/ingestion/trigger` - Trigger manual ingestion

### Ontology
- `GET /api/ontology/stats` - Get graph statistics
- `GET /api/ontology/entity-types` - Get entity types
- `GET /api/ontology/relationship-types` - Get relationship types
- `GET /api/ontology/entities/{id}` - Get entity details
- `GET /api/ontology/search` - Search entities

## Technology Stack

- **Backend**: Python, FastAPI, Neo4j, PostgreSQL, Redis
- **Frontend**: React, Vite, React Simple Maps, D3.js, Recharts
- **AI/ML**: OpenAI GPT-4, LangChain
- **Background Tasks**: Celery, Redis
- **Containerization**: Docker, Docker Compose

## Development

### Running Locally

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## License

MIT License - See LICENSE file for details
