# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Workflow Rules

1. Use concise prompts that clearly specify the information needed.
2. Avoid unnecessary follow-up questions by asking for all relevant details upfront.
3. **ALWAYS ENTER PLAN MODE FIRST** before coding to ensure a clear understanding of the problem and desired outcome.
4. Leverage existing knowledge and resources to avoid redundant code generation.
5. Continuously evaluate responses for relevance and accuracy.

## Commands

```bash
# Install dependencies
uv sync

# Run dev server (reload on file change requires DEBUG=True in .env)
uvicorn main:app --reload
# or
python main.py

# Run migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "<description>"

# Run tests
pytest
```

## Environment Variables (`.env`)

```
DATABASE_URL=postgresql://user:password@host:5432/syncfit
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_KEY=<anon-public-key>
SUPABASE_JWT_SECRET=<jwt-secret>
GEMINI_API_KEY=<gemini-key>
```

## Architecture Overview

**Dual-database design:** Supabase manages authentication (`auth.users`); SQLAlchemy/PostgreSQL manages all application data. These are bridged via `supabase_user_id` on the `users` table, which stores the Supabase auth UUID.

**Auth flow:**
1. Client authenticates with Supabase directly and receives a JWT.
2. JWT is sent as `Authorization: Bearer <token>` on every protected request.
3. `app/supabase_client.py` calls `supabase.auth.get_user(token)` to validate it — no local JWT secret parsing.
4. `app/dependencies.py` exposes three reusable deps: `get_current_user` (returns JWT payload dict), `get_current_user_optional`, and `get_current_db_user` (returns full SQLAlchemy `User` object from the internal DB).

**New user registration flow:**
- Supabase account is created on the client side (via Supabase SDK or console).
- The app's `POST /api/v1/users/` endpoint must then be called with the user's JWT to create the corresponding row in the internal `users` table. `is_active` defaults to `False` — the user is inactive until explicitly activated.

**Key files:**
- `main.py` — FastAPI app, lifespan (calls `init_db()`), router registration.
- `app/config.py` — Settings via `pydantic-settings`; reads `.env`.
- `app/database.py` — SQLAlchemy engine/session; `init_db()` runs `Base.metadata.create_all()`.
- `app/models/user.py` — `User`, `User_Profile`, `User_Supplements`, `User_Limitations`, `Weight_Loss_Progress`, `Event_Logs`, `Trainer_info`.
- `app/models/item.py` — Workout schema: `Workout_Plans`, `Workouts`, `Exercises`, association tables, `Workout_Logs`, `Workout_User_Stats`, `Badges`, `User_Badges`.
- `app/models/social.py` — `Connections`, `Conversations`, `Conversation_Participants`, `Messages`.
- `app/models/meal_plan.py` — Meal planning models.
- `app/schemas/` — Pydantic v2 schemas (request/response) mirroring the models directory.
- `app/api/v1/` — One router file per domain: `auth`, `users`, `workout`, `meal_plan`, `socials`, `health`.

**Alembic:** Migrations live in `alembic/versions/`. Always generate via `--autogenerate` and review before applying. `alembic/env.py` imports all models so autogenerate can detect schema changes.

**User roles & permissions:** `UserRole` (`admin`/`user`) and `UserType` (`trainer`/`trainee`) are separate enums on the `User` model. Admin checks are done inline in route handlers by querying the DB (`User.role == UserRoleModel.admin`) — there is no middleware-level RBAC.
