# BAH Web v2 deployment guide

## Architecture

```text
Browser
  -> Next.js frontend (HTTPS)
  -> FastAPI gateway
  -> internal vLLM on 127.0.0.1:8000
  -> Qwen2.5-3B-Instruct + BAH LoRA

FastAPI
  -> Supabase REST API
  -> usage_events
```

The model computer is no longer a dependency for public users.

## 1. Local test without GPU

### Backend

```powershell
cd backend
python -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set:

```env
INFERENCE_MODE=mock
FRONTEND_ORIGIN=http://localhost:3000
ANALYTICS_OPTIONAL=true
```

For analytics, also set `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, and `ADMIN_KEY`.

Run:

```powershell
uvicorn main:app --reload --port 8000
```

Check:

`http://localhost:8000/api/health`

### Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Open:

`http://localhost:3000`

## 2. Supabase

Create a Supabase project.

Open SQL Editor and run:

`supabase/schema.sql`

Create a secret key in **Settings -> API Keys** and put it ONLY in the backend environment.

Use:

```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SECRET_KEY=sb_secret_...
```

Do not use the secret key in a `NEXT_PUBLIC_*` variable.

## 3. Local feedback test

1. Ask a question.
2. Confirm a `chat` row exists in `usage_events`.
3. Click `Helpful`.
4. Confirm a positive `feedback` row exists.
5. Click `Needs work` and select a reason.
6. Confirm a negative `feedback` row exists.
7. Verify question/answer columns remain null when content sharing is off.
8. Turn content sharing on and submit a new question. Verify the new event contains the content.

## 4. GPU service

The public GPU service should run the supplied `inference/Dockerfile`.

Build from repository root:

```bash
docker build -f inference/Dockerfile -t bah-gpu:v2 .
```

The image:

- downloads/loads `Qwen/Qwen2.5-3B-Instruct`
- registers `zhaoweichang/business-admin-answer-helper` as the `bah` LoRA
- runs vLLM on `127.0.0.1:8000`
- runs FastAPI on `0.0.0.0:8080`

## 5. GPU provider settings

For a first deployment, test a single GPU with enough VRAM for Qwen2.5-3B plus KV cache. Start conservatively with a 16 GB class GPU; move to 24 GB+ if you need larger context/concurrency.

Environment variables:

```env
BASE_MODEL=Qwen/Qwen2.5-3B-Instruct
LORA_REPO=zhaoweichang/business-admin-answer-helper
VLLM_MODEL=bah
VLLM_API_KEY=<long random secret>
PUBLIC_PORT=8080
MAX_MODEL_LEN=8192
GPU_MEMORY_UTILIZATION=0.90

SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SECRET_KEY=sb_secret_...
ADMIN_KEY=<different long random secret>
FRONTEND_ORIGIN=https://your-frontend-domain.example
MODEL_VERSION=BAH-HF-v2
```

Expose only `8080/http` publicly.
Do not expose `8000`.

## 6. vLLM

The current vLLM LoRA serving interface supports:

```bash
vllm serve Qwen/Qwen2.5-3B-Instruct \
  --enable-lora \
  --max-loras 1 \
  --max-lora-rank 32 \
  --lora-modules '{"name":"bah","path":"zhaoweichang/business-admin-answer-helper","base_model_name":"Qwen/Qwen2.5-3B-Instruct"}'
```

The BAH adapter is rank 24, so the deployment uses the next supported maximum, 32.

## 7. Production frontend

Set in the frontend hosting provider:

```env
NEXT_PUBLIC_API_BASE_URL=https://YOUR-GPU-SERVICE.example.com
```

Do NOT set any Supabase secret, vLLM key, or admin key in the frontend.

## 8. Production checklist

- [ ] HTTPS enabled
- [ ] `.env` not committed
- [ ] Supabase secret key server-only
- [ ] vLLM key server-only
- [ ] admin key server-only
- [ ] port 8000 private
- [ ] port 8080 public
- [ ] analytics checked
- [ ] feedback checked
- [ ] CSV export checked
- [ ] mock mode changed to `remote`
- [ ] test completed from a different device
- [ ] no full prompts/answers appear in logs
