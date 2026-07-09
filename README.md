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
  Groq's `gemma2-9b-it` model via `langchain-groq`.
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
4. **`suggest_follow_up`** — Regenerates AI-suggested follow-up tasks for a given interaction and
   attaches them to the record.
5. **`search_materials`** — Searches the catalog of marketing materials / drug samples available
   to share with an HCP.

## Running locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- A Postgres database (or adjust `DATABASE_URL` for MySQL)
- A Groq API key from https://console.groq.com

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
copy .env.example .env       # then fill in GROQ_API_KEY and DATABASE_URL

python -m app.seed           # creates tables + sample HCPs/materials
uvicorn app.main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`. Health check: `GET /api/health`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173` and proxies `/api/*` to `http://localhost:8000`
(see `vite.config.js`).

## Using the screen

- **Structured form** (left): search/select an HCP, fill in interaction details, add
  attendees/materials/samples via type-ahead, pick sentiment, and click **Log Interaction**.
- **AI chat** (right): describe the interaction in natural language (e.g. "Met Dr. Priya Sharma,
  discussed OncoBoost Phase III data, she was positive, shared the efficacy deck") and the
  LangGraph agent extracts structured fields, saves the interaction, and populates the form. You
  can then follow up with edits ("change the sentiment to neutral") or ask "what did we discuss
  with Dr. Sharma last time?" to trigger the history/edit/follow-up tools.

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
