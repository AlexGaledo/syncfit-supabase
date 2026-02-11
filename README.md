# SyncFit Backend API

FastAPI backend with SQLAlchemy ORM and Supabase Authentication integration.

## Features

- ✅ **FastAPI** - Modern, fast web framework
- ✅ **SQLAlchemy** - ORM for database operations
- ✅ **Supabase Auth** - JWT token verification (lightweight, no SDK)
- ✅ **PostgreSQL** - Database (via SQLAlchemy)
- ✅ **Pydantic** - Data validation
- ✅ **JWT Token Verification** - Secure API endpoints
- ✅ **CORS** - Cross-origin resource sharing
- ✅ **Auto-generated API Docs** - Swagger UI and ReDoc

## Project Structure

```
backendv2/
├── app/
│   ├── __init__.py
│   ├── config.py              # Application configuration
│   ├── database.py            # SQLAlchemy setup
│   ├── dependencies.py        # FastAPI dependencies
│   ├── supabase_client.py     # Supabase client & auth
│   ├── api/                   # API routes
│   │   ├── health.py          # Health check endpoints
│   │   ├── auth.py            # Auth endpoints
│   │   ├── users.py           # User CRUD
│   │   └── items.py           # Example items CRUD
│   ├── models/                # SQLAlchemy models
│   │   ├── user.py
│   │   └── item.py
│   ├── schemas/               # Pydantic schemas
│   │   ├── user.py
│   │   └── item.py
│   └── middleware/            # Custom middleware
│       ├── cors.py
│       └── auth.py
├── main.py                    # Application entry point
├── pyproject.toml             # Dependencies
└── .env                       # Environment variables
```

## Setup

### 1. Install Dependencies

Using `uv` (recommended):
```bash
uv sync
```

Or using `pip`:
```bash
pip install -e .
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and update the values:

```bash
cp .env.example .env
```

Edit `.env`:
```env
# Database Settings
DATABASE_URL=postgresql://user:password@localhost:5432/syncfit

# Supabase Settings
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_JWT_SECRET=your-jwt-secret
```

**Getting Supabase Credentials:**
1. Go to your Supabase project dashboard
2. Navigate to Settings → API
3. Copy `URL` → `SUPABASE_URL`
4. Copy `anon public` → `SUPABASE_KEY`
5. Copy `JWT Secret` → `SUPABASE_JWT_SECRET`

### 3. Setup Database

Make sure PostgreSQL is running, then the tables will be created automatically on startup.

Alternatively, use Alembic for migrations:
```bash
# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head
```

### 4. Run the Server

```bash
uvicorn main:app --reload
```

Or run directly:
```bash
python main.py
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
