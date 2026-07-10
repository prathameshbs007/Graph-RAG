# DEPLOYMENT.md — Free-tier deployment

Everything below is $0/month: Qdrant Cloud free 1GB cluster, Neo4j AuraDB Free, Hugging Face Spaces free CPU tier, Vercel free hobby tier. No credit card required for any of them.

## 1. Qdrant Cloud

1. Create a free account at [cloud.qdrant.io](https://cloud.qdrant.io) and create a free 1GB cluster.
2. From the cluster's dashboard, copy the cluster URL and generate an API key.
3. Set in your deployment secrets (see §3 below for where):
   - `QDRANT_URL` — the cluster URL, e.g. `https://<cluster-id>.<region>.aws.cloud.qdrant.io`
   - `QDRANT_API_KEY` — the generated key

The app already supports these via `config.py` (Phase 1) — no code changes needed, just env vars.

## 2. Neo4j AuraDB Free

1. Create a free instance at [console.neo4j.io](https://console.neo4j.io).
2. **Download the credentials file when prompted — AuraDB only shows the generated password once.** If you lose it, reset the password from the instance's console page (Instance → "Reset password").
3. Set in your deployment secrets:
   - `NEO4J_URI` — `neo4j+s://<instance-id>.databases.neo4j.io` (from the console's "Connect" panel)
   - `NEO4J_USER` — **check the actual value in the downloaded credentials file.** AuraDB free instances have shown the instance ID itself (not the literal string `neo4j`) as the username in practice — don't assume, read it from the file.
   - `NEO4J_PASSWORD` — from the same file

The driver connects fine with the `neo4j+s://` scheme — verified directly with `neo4j.GraphDatabase.driver(...).verify_connectivity()` against a live AuraDB Free instance.

## 3. Backend → Hugging Face Spaces

The backend Dockerfile already listens on `$PORT` (defaulting to 8000 locally; HF Spaces sets `PORT=7860` for Docker SDK Spaces automatically) — verified by running the built image locally with `-e PORT=7860` and confirming `/health` responds on that port.

1. Create a new Space at [huggingface.co/new-space](https://huggingface.co/new-space):
   - SDK: **Docker**
   - Visibility: your choice (public is fine for a resume demo)
2. Push this repo's `backend/` directory as the Space's root (or push the whole repo and set the Space's Dockerfile path to `backend/Dockerfile` in Space settings — check current HF Spaces docs for the exact option name, since this changes over time).
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/<space-name>
   git subtree push --prefix backend space main
   ```
   (Or clone the Space repo separately and copy `backend/`'s contents in — either works.)
3. In the Space's **Settings → Repository secrets**, set:
   - `GROQ_API_KEY`
   - `QDRANT_URL`, `QDRANT_API_KEY`
   - `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
   - `ALLOWED_ORIGINS` — set this to your Vercel URL once you have it (§4), e.g. `https://your-app.vercel.app`
4. The Space will build and start automatically. Check `https://<your-username>-<space-name>.hf.space/health` once it's up.

**Note:** HF free Spaces sleep after ~48h of inactivity; the next request triggers a cold start (~1 min while the container boots and loads the ONNX models). Acceptable for a resume demo, not for anything latency-sensitive.

## 4. Frontend → Vercel

1. Import this repo at [vercel.com/new](https://vercel.com/new).
2. Project settings:
   - Root directory: `frontend`
   - Build command: `npm run build`
   - Output directory: `dist`
3. Environment variable:
   - `VITE_API_URL` = your HF Space URL, e.g. `https://<your-username>-<space-name>.hf.space`
4. Deploy. Once live, go back to the HF Space's secrets (§3) and set `ALLOWED_ORIGINS` to this Vercel URL so CORS allows the frontend to call the backend directly (they're different origins in this topology, unlike local dev where nginx proxies same-origin).

## 5. End-to-end verification

Once both are live:
1. Open the Vercel URL, ingest a PDF, confirm `/ingest/status/{id}` polling completes.
2. Run a query, confirm a cited answer comes back with sources.
3. Open the Graph Explorer tab, confirm nodes/edges render.

## 6. Known limitations of the free tier

- **HF Spaces**: sleeps after ~48h idle, ~1 min cold start on wake.
- **AuraDB Free**: pauses after 3 days idle — resume manually from the [Aura console](https://console.neo4j.io).
- Both are fine for a resume/demo project; neither is suited for production traffic.
