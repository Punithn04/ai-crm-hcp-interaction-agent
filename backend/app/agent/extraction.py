import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.llm import get_llm

EXTRACTION_SYSTEM_PROMPT = """You are a life-science CRM assistant that extracts structured data from a \
field representative's free-text notes about a Healthcare Professional (HCP) interaction.

Return ONLY a JSON object (no markdown, no commentary) with these keys:
- interaction_type: one of "Meeting", "Call", "Email", "Conference"
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


def _parse_json_block(text: str):
    match = re.search(r"\{.*\}|\[.*\]", text, re.DOTALL)
    raw = match.group(0) if match else text
    return json.loads(raw)


def extract_interaction_fields(raw_text: str) -> dict:
    llm = get_llm(temperature=0.1)
    messages = [
        SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
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
