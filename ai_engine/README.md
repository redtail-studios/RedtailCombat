# AI Market Intelligence Engine

Scrapes free platforms for player/market signals, then uses **Claude** to find
gaps in the market and write a premium HTML intelligence report. Includes a
dashboard to scrape, analyse, and **backtest** signals against later years.

```
ai_engine/
├── scrape.py          # LOCAL CLI — collect data from all free platforms
├── app.py             # FastAPI: dashboard + analyse/report API (local & Vercel)
├── llm.py             # Claude (default) / OpenAI wrapper
├── analysis.py        # cheap signal/scorecard/competitor pre-aggregation
├── report.py          # builds the prompt + asks Claude for the HTML report
├── config.py          # what to research (subreddits, apps, signals, competitors)
├── dashboard.html     # the UI
├── scrapers/          # reddit, steam, googleplay, appstore, hackernews
├── data/              # scraped JSON per year (committed → deployed app reads it)
├── api/index.py       # Vercel entry point
├── vercel.json        # Vercel routing + function timeout
├── Procfile           # AWS Elastic Beanstalk entry point (gunicorn + uvicorn worker)
└── .ebextensions/     # EB health check path + load balancer timeout
```

## How it works (and why the split)

Scraping is long-running, rate-limited, and writes files — that does **not** fit
serverless. So:

- **Scrape locally** → produces `data/<year>/*.json` → commit them.
- **The web app** (dashboard + Claude report) runs locally **and** on Vercel,
  reading the committed data. On Vercel, scraping is disabled by design.

## 1. Setup (local)

```bash
cd ai_engine
python -m venv venv && source venv/bin/activate
pip install -r requirements-scrape.txt        # app + scraping deps
cp .env.example .env                            # add ANTHROPIC_API_KEY (+ Reddit keys)
```

## 2. Collect data

```bash
python scrape.py --year 2026                     # all free platforms
python scrape.py --year 2024 --only steam,googleplay
```

No keys needed for any platform — Reddit uses its public JSON endpoints, and
Steam, Google Play, App Store (iTunes RSS), and Hacker News are all keyless.
Re-run per year you want to backtest.

## 3. Run the dashboard locally

```bash
python app.py            # → http://localhost:8000
```

- **Step 1** scrapes a year (live platform status + log).
- **Step 2** generates the Claude report — *Analyse years* or *Backtest + validate*
  (analyse 2022–2023 as predictions, score them against 2024–2025 reality).

## 4. Deploy to Vercel

```bash
npm i -g vercel          # if needed
cd ai_engine
vercel                   # first deploy (link/create project)
```

In the Vercel project settings add environment variables:
`ANTHROPIC_API_KEY` (and `ANTHROPIC_MODEL=claude-opus-4-8`). Then:

```bash
vercel --prod
```

**Notes**
- The Claude report can take 1–3 minutes. `vercel.json` sets `maxDuration: 300`,
  which needs a **Vercel Pro** plan (Hobby caps functions at 60s — the report may
  time out there). For a free plan, run reports locally.
- `data/` is committed on purpose so the deployed app has something to analyse.
  Refresh data locally and redeploy to update it.

## 5. Deploy on AWS

The AI engine is deployed on ECS on AWS. 

- Step 1: Build the image using 
```bash
docker build -t redtail-ai-engine .
```

- Step 2: Tag for ECR
```bash
docker tag redtail-ai-engine:latest 512190911607.dkr.ecr.us-east-1.amazonaws.com/redtail-ai-engine:latest
```

- Step 3: Login
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 512190911607.dkr.ecr.us-east-1.amazonaws.com
```

- Step 4: Push the image
```bash
docker push 512190911607.dkr.ecr.us-east-1.amazonaws.com/redtail-ai-engine:latest
```

- Step 5: Force ECS Service redeploy
```bash
aws ecs update-service \
  --cluster redtail-ai-engine-cluster \
  --service redtail-ai-engine-task-service-k6omwqv9 \
  --force-new-deployment
```

