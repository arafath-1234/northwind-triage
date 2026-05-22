# Northwind Triage Agent

AI triage agent for Northwind Home Services — built for the Avreo take-home assessment.

## What it does

Reads inbound customer messages and outputs structured triage decisions (category, priority, routing, draft reply, human review flag) using the Northwind SOP, service catalogue, and tone guide as the agent's rulebook.

## Architecture

```
frontend/index.html   →   POST /triage   →   backend/app.py   →   agent.py   →   Anthropic API
```

- **Backend**: FastAPI + Python. Single endpoint: `POST /triage`. Agent logic lives in `agent.py` — one system prompt, no per-message hacks, no chaining.
- **Frontend**: Single HTML file. No build step. Open directly in a browser.
- **Agent design**: One Claude call per message. The system prompt encodes all SOP rules, catalogue constraints, and tone guide as structured plain text. The model reasons over the rules and outputs JSON. Intentionally simple — the problem doesn't justify orchestration complexity.

---

## Setup

### Prerequisites
- Python 3.9 or higher
- An Anthropic API key — get one at [console.anthropic.com](https://console.anthropic.com)

---

### Step 1 — Clone the repo

```bash
git clone https://github.com/arafath-1234/northwind-triage.git
cd northwind-triage
```

---

### Step 2 — Create a virtual environment

**Mac/Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` at the start of your terminal prompt.

---

### Step 3 — Install dependencies

```bash
cd backend
pip install anthropic fastapi "uvicorn[standard]" python-dotenv pydantic
```

---

### Step 4 — Add your API key

Copy the example env file:

**Mac/Linux:**
```bash
cp .env.example .env
```

**Windows:**
```bash
copy .env.example .env
```

Open `.env` and replace the placeholder with your real key:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Make sure the spelling is exactly `ANTHROPIC_API_KEY` — no typos.

---

### Step 5 — Run the backend

```bash
python app.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

---

### Step 6 — Open the frontend

Open `frontend/index.html` directly in your browser (double-click it in your file explorer).

Paste a customer message, click **Run Triage**, and see the result.

---

### Step 7 — Run the batch evaluation

Open a second terminal, activate the venv, then:

```bash
cd backend
python batch_run.py
```

This runs all 20 messages from `05_Inbound_Messages.json` through the agent, scores them against `06_Benchmark.json`, and prints accuracy results. Full results are saved to `backend/batch_results.json`.

To view the scored table visually, load `batch_results.json` using the **Batch results** tab in the frontend.

---

## Project layout

```
northwind-triage/
├── backend/
│   ├── app.py              # FastAPI server — POST /triage endpoint
│   ├── agent.py            # Triage agent — system prompt + Anthropic API call
│   ├── batch_run.py        # Runs all 20 messages and scores vs benchmark
│   ├── requirements.txt    
│   ├── .env.example        # Copy to .env and add your API key
│   └── .env                # Your API key — not committed to git
├── frontend/
│   └── index.html          # Single-file UI — open directly in browser
├── data/
│   ├── 05_Inbound_Messages.json   # 20 inbound customer messages
│   └── 06_Benchmark.json          # Gold-standard triage decisions
├── README.md
└── writeup.md              # Accuracy scores, benchmark disagreements, agent design notes
```

---

## Quick test

Once the backend is running, you can test it directly from the terminal:

**Mac/Linux:**
```bash
curl -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"message": "Hi, the cold tap in our ensuite has been dripping for a week. Can you book someone? We are in Mosman. Thanks, Sarah"}'
```

**Windows:**
```bash
curl -X POST http://localhost:8000/triage -H "Content-Type: application/json" -d "{\"message\": \"Hi, the cold tap in our ensuite has been dripping for a week. Can you book someone? We are in Mosman. Thanks, Sarah\"}"
```

Expected response: `BOOKING`, `P3`, `Dispatch`, `needs_human_review: false`

---

See `writeup.md` for accuracy scores, benchmark disagreements, and agent design notes.
