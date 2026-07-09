# AI-First CRM — HCP Module: Log Interaction Screen

An AI-first "Log Interaction" screen for pharmaceutical field representatives, built for the
Healthcare Professional (HCP) module of a CRM. Reps can log HCP interactions either through a
**structured form** or a **conversational AI chat interface** backed by a LangGraph agent.

## Architecture

```
frontend/   React 18 + Redux Toolkit (Vite) — structured form + AI chat panel
backend/    FastAPI + SQLAlchemy (Postgres/MySQL) + LangGraph agent (Groq)
```

> **Note on the LLM**: the assignment specifies `gemma2-9b-it` on Groq, but that model was
> decommissioned by Groq in October 2025. The assignment also lists `llama-3.3-70b-versatile`
> as an acceptable alternative, and this project defaults to it (configurable via `GROQ_MODEL`
> in `.env`). Groq's smaller `llama-3.1-8b-instant` was tried first as the direct Gemma
> replacement, but it proved unreliable at multi-tool selection (occasionally hallucinating a new
> interaction when asked to *read* history, or looping on redundant tool calls). The 70B model
> handles the agent's tool-calling reliably. Swap `GROQ_MODEL` back to `gemma2-9b-it` if that
> model is ever reinstated on your account.

- **Frontend**: React UI with Redux Toolkit slices for the interaction form and chat state.
  Google Inter font. Calls the FastAPI backend via `/api/*`.
- **Backend**: FastAPI exposes REST CRUD for interactions/HCPs/materials, plus a `/api/chat`
  endpoint that drives a LangGraph agent.
- **AI Agent Framework**: LangGraph `StateGraph` (ReAct-style agent + tool node loop) powered by
  Groq via `langchain-groq`, defaulting to `llama-3.3-70b-versatile` (see LLM note above).
- **Database**: Postgres (SQLAlchemy models: `HCP`, `Interaction`, `Material`).

## LangGraph Agent & Tools

The agent (`backend/app/agent/graph.py`) is a `StateGraph` with an `agent` node (LLM bound to
tools) and a `tools` node (`ToolNode`), looping until the model responds without further tool
calls — the standard LangGraph ReAct pattern. It maintains per-conversation context
(`last_interaction_id`, `hcp_id`) so follow-up chat turns like "make that positive" resolve
correctly.

Five tools (`backend/app/agent/tools/builder.py`):

1. **`log_interaction`** — Takes free-text notes (e.g. "Met Dr. Smith, discussed Product X
   efficacy, positive sentiment, shared brochure") and an HCP name. Calls the LLM
   (`extract_interaction_fields`) to extract interaction type, topics, materials/samples,
   sentiment, outcomes, and follow-ups as structured JSON, then persists an `Interaction` row.
   Also calls the LLM again to generate AI-suggested follow-up actions.
2. **`edit_interaction`** — Takes a free-text instruction (e.g. "change sentiment to positive")
   and an interaction id (or `"last"` for the most recent one in the conversation). Uses the LLM
   to interpret the instruction against the current record and applies only the changed fields.
3. **`get_hcp_history`** — Looks up an HCP by name and returns their recent interaction history so
   the rep can recall past conversations.
4. **`detect_adverse_event`** — Scans a logged interaction's notes with the LLM for any patient
   adverse event / adverse drug reaction (side effects, safety signals, hospitalizations),
   classifies seriousness, flags whether a 24-hour pharmacovigilance report is required, and stores
   the structured findings on the interaction (`adverse_events`). Reflects a real regulatory
   obligation in pharma — adverse events must be captured and reported.
5. **`analyze_hcp_engagement`** — Reads an HCP's full interaction history and uses the LLM to assess
   the sentiment trend (warming up / stable / cooling off), overall engagement level, and a
   recommended next action for the rep — turning raw history into a strategic read.

> Note: `log_interaction` and `edit_interaction` are the two tools mandated by the assignment; the
> other three are chosen to fit a realistic pharma field-rep workflow. `log_interaction` also
> auto-generates AI follow-up suggestions (shown as "AI Suggested Follow-ups" on the screen).

## Running locally

### Prerequisites
- Python 3.11+ (tested on 3.13)
- Node.js 18+
- A Postgres database (see step 1 below for a one-line Docker option) — or adjust `DATABASE_URL` for MySQL
- A free Groq API key from https://console.groq.com (Console → API Keys → Create API Key)

### Step 1 — Start Postgres

Easiest option (Docker), which matches the default `DATABASE_URL` exactly:

```bash
docker run --name hcp-crm-postgres \
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=hcp_crm \
  -p 5432:5432 -d postgres:16
```

Already created it once? Just start it again with `docker start hcp-crm-postgres`.

Prefer a native install? Create a database named `hcp_crm` and make sure `DATABASE_URL`
in `.env` matches your username/password/port.

### Step 2 — Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
copy .env.example .env       # Windows  (macOS/Linux: cp .env.example .env)
# then open .env and paste your GROQ_API_KEY

python -m app.seed           # creates tables + sample HCPs/materials
uvicorn app.main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`. Health check: open `http://localhost:8000/api/health`
→ should return `{"status":"ok"}`.

### Step 3 — Frontend

In a second terminal (leave the backend running):

```bash
cd frontend
npm install
npm run dev
```

Then open **http://localhost:5173**. The frontend proxies `/api/*` to `http://localhost:8000`
(see `vite.config.js`), so both servers must be running together.

## Using the screen

- **Structured form** (left): search/select an HCP, fill in interaction details, add
  attendees/materials/samples via type-ahead, pick sentiment, and click **Log Interaction**.
- **AI chat** (right): describe the interaction in natural language (e.g. "Met Dr. Priya Sharma,
  discussed OncoBoost Phase III data, she was positive, shared the efficacy deck") and the
  LangGraph agent extracts structured fields, saves the interaction, and populates the form.
  From there you can:
  - Edit it: *"change the sentiment to neutral"*
  - Ask for history: *"what did we discuss with Dr. Sharma last time?"*
  - Screen for safety issues: *"a patient on OncoBoost developed severe neutropenia and was
    hospitalized"* — flags whether pharmacovigilance reporting is required and drafts a
    notification email for the Drug Safety team (reviewed by the rep, never auto-sent)
  - Ask for a relationship read: *"how is my relationship with Dr. Sharma trending?"* — the AI
    reads the HCP's history and returns a sentiment trend, engagement level, and a recommendation

## Project structure

```
backend/app/
  agent/
    graph.py         StateGraph agent (ReAct loop)
    tools/builder.py  5 LangGraph tools
    extraction.py     LLM-based field extraction & follow-up generation
    runner.py         Per-thread conversation + context management
  models/             SQLAlchemy models (HCP, Interaction, Material)
  routers/            REST endpoints (hcps, materials, interactions, chat)
  services/           DB access shared by REST routes and agent tools
  schemas/            Pydantic request/response models

frontend/src/
  features/           Redux slices (interactionForm, chat)
  components/         InteractionForm, ChatPanel, HcpSearchInput, TagAdder
  api/client.js        Fetch wrapper for backend API
```
