import json
import re
from datetime import date

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.llm import get_llm

EXTRACTION_SYSTEM_PROMPT = """You are a life-science CRM assistant that extracts structured data from a \
field representative's free-text notes about a Healthcare Professional (HCP) interaction.

Today's date is {today} (YYYY-MM-DD). Use it to resolve any relative dates.

Return ONLY a JSON object (no markdown, no commentary) with these keys:
- interaction_type: one of "Meeting", "Call", "Email", "Conference"
- occurred_at: the date AND time the interaction happened.
  - If a specific time is mentioned (e.g. "at 5PM", "around 10:30am", "this morning"), return \
"YYYY-MM-DDTHH:MM" in 24-hour time (e.g. "2026-07-08T17:00" for "yesterday at 5PM").
  - If no time is mentioned at all, return just the date as "YYYY-MM-DD".
  - Resolve relative date references ("yesterday", "today", "last Monday", "two days ago") against \
today's date above. If no date is mentioned at all, use today's date.
- topics_discussed: short paragraph summarizing topics discussed
- materials_shared: list of strings (brochures/decks mentioned), [] if none
- samples_distributed: list of strings (drug/product samples mentioned), [] if none
- sentiment: one of "Positive", "Neutral", "Negative" (infer HCP's tone toward the product/rep)
- outcomes: short paragraph of key outcomes or agreements
- follow_up_actions: short paragraph of next steps, "" if none mentioned

If a field cannot be inferred, use an empty string or empty list. Do not invent facts not present in the notes.
"""

FOLLOW_UP_SYSTEM_PROMPT = """You are a life-science CRM assistant. Given a summary of an HCP interaction, \
propose up to 3 concise, actionable follow-up tasks for the field representative (e.g. "Schedule follow-up \
meeting in 2 weeks", "Send Phase III data PDF"). Return ONLY a JSON array of strings, no commentary.
"""

ADVERSE_EVENT_SYSTEM_PROMPT = """You are a pharmacovigilance assistant. Scan the following notes from a \
field representative's interaction with a Healthcare Professional for any mention of an ADVERSE EVENT — \
a patient side effect, adverse drug reaction, unexpected safety signal, hospitalization, or any harm \
possibly related to a drug/product.

Return ONLY a JSON object (no markdown, no commentary):
{
  "adverse_events": [
    {"description": "<what happened>", "drug": "<product name or 'unspecified'>",
     "seriousness": "serious" | "non-serious"}
  ],
  "reporting_required": true | false
}

Mark "reporting_required": true if ANY serious event is present (death, hospitalization, life-threatening,
disability, congenital anomaly). If no adverse event is mentioned, return an empty list and false. Do NOT
invent events that are not clearly stated in the notes.
"""

ADVERSE_EMAIL_SYSTEM_PROMPT = """You are a pharmacovigilance assistant. Draft a concise, professional \
internal email FROM a pharmaceutical field representative TO the company's Drug Safety / \
Pharmacovigilance team, notifying them of an adverse event reported during an HCP interaction that \
requires expedited reporting.

Include, in this order:
- A "Subject:" line (mention "Adverse Event Report" and the drug)
- A short body stating: the HCP who reported it, the drug/product, a clear description of the event(s), \
the seriousness, and that this requires reporting within the regulatory timeframe (24h for serious).
- A closing line noting the rep is available for follow-up details.

Keep it under 150 words. Return ONLY the email text (starting with "Subject:"). Do not invent patient \
identifiers or facts beyond what is provided.
"""

ENGAGEMENT_SYSTEM_PROMPT = """You are a life-science CRM analyst advising a pharmaceutical field \
representative. Given an HCP's full interaction history (dates, types, sentiment, topics), assess the \
relationship and reply in plain text (no markdown) with exactly these three short parts:

1. Sentiment trend: is the HCP warming up, stable, or cooling off? Reference the progression of sentiment.
2. Engagement level: High / Medium / Low, with a one-line reason.
3. Recommended next action: one concrete, strategic recommendation for the rep.

Keep the whole response to 3-5 sentences. Be specific to the history provided; do not invent interactions.
"""


def _parse_json_block(text: str):
    match = re.search(r"\{.*\}|\[.*\]", text, re.DOTALL)
    raw = match.group(0) if match else text
    return json.loads(raw)


def extract_interaction_fields(raw_text: str) -> dict:
    llm = get_llm(temperature=0.1)
    messages = [
        SystemMessage(content=EXTRACTION_SYSTEM_PROMPT.format(today=date.today().isoformat())),
        HumanMessage(content=raw_text),
    ]
    response = llm.invoke(messages)
    try:
        return _parse_json_block(response.content)
    except (json.JSONDecodeError, AttributeError):
        return {
            "interaction_type": "Meeting",
            "topics_discussed": raw_text,
            "materials_shared": [],
            "samples_distributed": [],
            "sentiment": "Neutral",
            "outcomes": "",
            "follow_up_actions": "",
        }


def generate_follow_ups(summary_text: str) -> list[str]:
    llm = get_llm(temperature=0.3)
    messages = [
        SystemMessage(content=FOLLOW_UP_SYSTEM_PROMPT),
        HumanMessage(content=summary_text),
    ]
    response = llm.invoke(messages)
    try:
        result = _parse_json_block(response.content)
        return result if isinstance(result, list) else []
    except (json.JSONDecodeError, AttributeError):
        return []


def detect_adverse_events(notes_text: str) -> dict:
    """Use the LLM to scan interaction notes for adverse events. Returns
    {"adverse_events": [...], "reporting_required": bool}."""
    llm = get_llm(temperature=0.0)
    messages = [
        SystemMessage(content=ADVERSE_EVENT_SYSTEM_PROMPT),
        HumanMessage(content=notes_text),
    ]
    response = llm.invoke(messages)
    try:
        result = _parse_json_block(response.content)
        if isinstance(result, dict):
            result.setdefault("adverse_events", [])
            result.setdefault("reporting_required", False)
            return result
    except (json.JSONDecodeError, AttributeError):
        pass
    return {"adverse_events": [], "reporting_required": False}


def analyze_engagement(history_summary: str) -> str:
    """Use the LLM to produce a plain-text engagement analysis from an HCP's history."""
    llm = get_llm(temperature=0.3)
    messages = [
        SystemMessage(content=ENGAGEMENT_SYSTEM_PROMPT),
        HumanMessage(content=history_summary),
    ]
    response = llm.invoke(messages)
    return response.content if hasattr(response, "content") else str(response)


def draft_adverse_event_email(context: str) -> str:
    """Use the LLM to draft a pharmacovigilance notification email for detected adverse event(s)."""
    llm = get_llm(temperature=0.3)
    messages = [
        SystemMessage(content=ADVERSE_EMAIL_SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]
    response = llm.invoke(messages)
    return response.content if hasattr(response, "content") else str(response)
