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

## API Endpoints

### Public Endpoints

- `GET /` - Root endpoint
- `GET /api/v1/health` - Health check
- `GET /api/v1/health/db` - Database health check

### Protected Endpoints (Require Authentication)

**Authentication:**
- `GET /api/v1/auth/me` - Get current user info
- `POST /api/v1/auth/verify` - Verify token

**Users:**
- `GET /api/v1/users` - List all users
- `GET /api/v1/users/{user_id}` - Get user by ID
- `POST /api/v1/users` - Create user
- `PATCH /api/v1/users/{user_id}` - Update user
- `DELETE /api/v1/users/{user_id}` - Delete user

**Items (Example):**
- `GET /api/v1/items` - List user's items
- `GET /api/v1/items/{item_id}` - Get item by ID
- `POST /api/v1/items` - Create item
- `PATCH /api/v1/items/{item_id}` - Update item
- `DELETE /api/v1/items/{item_id}` - Delete item

## Authentication

All protected endpoints require a Bearer token in the Authorization header:

```bash
curl -H "Authorization: Bearer YOUR_SUPABASE_TOKEN" \
  http://localhost:8000/api/v1/auth/me
```

### Using with Frontend

When a user logs in via Supabase on the frontend:

```typescript
// Frontend - Get token after login
const { data: { session } } = await supabase.auth.getSession()
const token = session?.access_token

// Make API request
fetch('http://localhost:8000/api/v1/items', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
```

## Database Models

### User Model
```python
- id: UUID (primary key)
- email: String
- full_name: String
- role: Enum (trainee, trainer, admin)
- supabase_user_id: UUID (from Supabase Auth)
- is_active: Boolean
- created_at: DateTime
- updated_at: DateTime
```

### Item Model (Example)
```python
- id: UUID (primary key)
- title: String
- description: Text
- owner_id: UUID (foreign key to User)
- created_at: DateTime
- updated_at: DateTime
```

## Adding New Endpoints

1. **Create Model** in `app/models/`
2. **Create Schema** in `app/schemas/`
3. **Create Router** in `app/api/`
4. **Register Router** in `main.py`

Example:
```python
# app/api/workouts.py
from fastapi import APIRouter, Depends
from app.dependencies import get_current_user

router = APIRouter(prefix="/workouts", tags=["Workouts"])

@router.get("/")
async def get_workouts(current_user: dict = Depends(get_current_user)):
    return {"workouts": []}

# main.py
from app.api import workouts
app.include_router(workouts.router, prefix=settings.API_V1_PREFIX)
```

## Development

### Run with Auto-reload
```bash
uvicorn main:app --reload --port 8000
```

### Run Tests (when added)
```bash
pytest
```

### Format Code
```bash
black .
isort .
```

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `APP_NAME` | Application name | `SyncFit Backend API` |
| `DEBUG` | Debug mode | `True` or `False` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/db` |
| `SUPABASE_URL` | Supabase project URL | `https://xxx.supabase.co` |
| `SUPABASE_KEY` | Supabase anon key | `eyJhbG...` |
| `SUPABASE_JWT_SECRET` | JWT secret for token verification | `your-secret` |
| `ALLOWED_ORIGINS` | CORS allowed origins | `http://localhost:3000` |

## Troubleshooting

### Database Connection Error
- Ensure PostgreSQL is running
- Check DATABASE_URL is correct
- Verify database exists

### Authentication Error
- Verify SUPABASE_JWT_SECRET matches your Supabase project
- Check token is valid and not expired
- Ensure Authorization header format: `Bearer <token>`

### CORS Error
- Add your frontend URL to ALLOWED_ORIGINS in .env
- Restart the server after changing .env

## Next Steps

- [ ] Add Alembic migrations
- [ ] Add unit tests
- [ ] Add logging
- [ ] Add rate limiting
- [ ] Add caching (Redis)
- [ ] Add background tasks (Celery)
- [ ] Add WebSocket support
- [ ] Add API versioning
- [ ] Add Docker configuration

## License

MIT
