# TITAN AI OS — MVP Deployment Guide

## Week 6: Go-Live Checklist

---

## 1. Local Dev Setup (Week 1 — run first)

```powershell
# Clone / enter project
cd E:\TITAN
git init
git remote add origin https://github.com/YOUR_USERNAME/titan-ai-os.git

# Start all local services (Postgres + Redis + Qdrant)
cd backend
docker-compose up -d

# Verify all containers are healthy
docker-compose ps

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Copy and fill your .env
cp .env.example .env
# → Edit .env with your API keys

# Start FastAPI dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Test health check
curl http://localhost:8000/health
```

Expected health response:
```json
{
  "status": "healthy",
  "services": {
    "redis": "ok",
    "qdrant": "ok",
    "postgres": "ok"
  }
}
```

---

## 2. Frontend Dev Setup (Week 5)

```powershell
cd E:\TITAN\frontend
npm install

# Set your local API URL
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start Next.js dev server
npm run dev
# → Open http://localhost:3000
```

---

## 3. Railway Backend Deployment (Week 6)

### Step 1: Create Railway project
1. Go to https://railway.app
2. New Project → Deploy from GitHub repo
3. Select `titan-ai-os/backend` directory

### Step 2: Add Railway services
In your Railway project, add:
- PostgreSQL (Railway built-in)
- Redis (Railway built-in)

### Step 3: Set environment variables in Railway
```
DATABASE_URL          = (auto-set by Railway Postgres plugin)
REDIS_URL             = (auto-set by Railway Redis plugin)
QDRANT_HOST           = your-cluster.qdrant.io
QDRANT_PORT           = 6333
QDRANT_API_KEY        = your-qdrant-cloud-api-key
ANTHROPIC_API_KEY     = sk-ant-...
GEMINI_API_KEY        = AIza...
TAVILY_API_KEY        = tvly-...
RESEND_API_KEY        = re_...
RESEND_FROM_EMAIL     = intel@shivanchal.in
JWT_SECRET            = (generate: python -c "import secrets; print(secrets.token_hex(32))")
SECRET_KEY            = (generate: python -c "import secrets; print(secrets.token_hex(32))")
APP_ENV               = production
DEBUG                 = false
ALLOWED_ORIGINS       = https://your-app.vercel.app
```

### Step 4: Qdrant Cloud (free tier)
1. Go to https://cloud.qdrant.io
2. Create free cluster (512MB RAM, 1GB storage)
3. Copy cluster URL and API key → add to Railway env vars

---

## 4. Vercel Frontend Deployment (Week 6)

```powershell
# Install Vercel CLI
npm i -g vercel

cd E:\TITAN\frontend

# Deploy
vercel

# Set environment variable
vercel env add NEXT_PUBLIC_API_URL production
# → Enter your Railway backend URL: https://titan-backend.railway.app
```

---

## 5. Go-Live Verification Checklist

Run these tests after deployment:

```bash
BASE_URL=https://your-titan-backend.railway.app

# 1. Health check
curl $BASE_URL/health

# 2. Register a user
curl -X POST $BASE_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"ankit@test.com","password":"Test1234","full_name":"Ankit Dubey"}'

# 3. Login
curl -X POST $BASE_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ankit@test.com","password":"Test1234"}'
# → Copy the access_token from response

# 4. Test /auth/me
curl $BASE_URL/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 5. Test chat (streaming)
curl -N -X POST $BASE_URL/chat/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"What is TITAN AI OS?","use_tools":false}'
# → Should stream SSE events
```

---

## 6. Monitoring Setup (Post Go-Live)

### UptimeRobot (free)
1. Go to https://uptimerobot.com
2. Add HTTP monitor: `https://your-backend.railway.app/health`
3. Alert: email + (optionally) Telegram

### Sentry (free tier)
```bash
pip install sentry-sdk
```

Add to `app/main.py`:
```python
import sentry_sdk
sentry_sdk.init(dsn="your-sentry-dsn", traces_sample_rate=0.1)
```

---

## 7. Project File Tree (Complete)

```
titan-ai-os/
├── backend/
│   ├── app/
│   │   ├── main.py              ← FastAPI app
│   │   ├── config.py            ← Settings
│   │   ├── db.py                ← SQLAlchemy async engine
│   │   ├── auth/
│   │   │   ├── models.py        ← User, RefreshToken
│   │   │   ├── schemas.py       ← Pydantic schemas
│   │   │   ├── security.py      ← JWT, bcrypt
│   │   │   ├── dependencies.py  ← get_current_user, require_role
│   │   │   └── router.py        ← /auth endpoints
│   │   ├── memory/
│   │   │   ├── short_term.py    ← Redis memory
│   │   │   ├── long_term.py     ← PostgreSQL memory
│   │   │   ├── semantic.py      ← Qdrant vector memory
│   │   │   └── manager.py       ← MemoryManager facade
│   │   ├── agents/
│   │   │   ├── base.py          ← BaseAgent
│   │   │   ├── executive.py     ← ExecutiveAssistantAgent
│   │   │   └── llm_router.py    ← Model selection + streaming
│   │   ├── tools/
│   │   │   ├── registry.py      ← ToolRegistry
│   │   │   ├── web_search.py    ← Tavily
│   │   │   ├── email_send.py    ← Resend
│   │   │   └── doc_reader.py    ← PDF/DOCX parser
│   │   └── chat/
│   │       └── router.py        ← /chat SSE endpoint
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── docker-compose.yml       ← Local dev services
│   ├── railway.toml
│   └── .env.example
│
└── frontend/
    ├── app/
    │   ├── login/page.tsx       ← Auth page
    │   └── dashboard/page.tsx   ← Chat UI
    ├── lib/
    │   └── api.ts               ← Typed API client
    ├── package.json
    └── vercel.json
```

---

## 8. API Reference (Quick)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET  | /health | No | System health |
| POST | /auth/register | No | Create account |
| POST | /auth/login | No | Get tokens |
| POST | /auth/refresh | No | Rotate tokens |
| GET  | /auth/me | Yes | Current user |
| POST | /auth/logout | Yes | Revoke refresh token |
| POST | /chat/ | Yes | Stream chat (SSE) |
| GET  | /chat/conversations | Yes | List conversations |
| DELETE | /chat/conversations/{id} | Yes | Delete conversation |

---

## 9. Estimated Monthly Costs (MVP)

| Service | Plan | Cost |
|---------|------|------|
| Railway (backend) | Hobby | $5/month (~₹420) |
| Vercel (frontend) | Free | ₹0 |
| Supabase (DB) | Free | ₹0 |
| Qdrant Cloud | Free | ₹0 |
| Anthropic API | Pay-per-use | ~₹2,000–5,000/month (depends on usage) |
| Gemini API | Free tier | ₹0 (60 req/min free) |
| Tavily | Free tier | ₹0 (1000 searches/month) |
| Resend | Free tier | ₹0 (100 emails/day) |
| **Total** | | **~₹2,500–5,500/month** |

---

*TITAN AI OS — MVP v0.1.0 — Built by Shivanchal Consultants*
