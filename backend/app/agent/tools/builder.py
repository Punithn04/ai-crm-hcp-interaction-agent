import uuid
from datetime import datetime

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.agent.extraction import (
    analyze_engagement,
    detect_adverse_events,
    draft_adverse_event_email,
    extract_interaction_fields,
    generate_follow_ups,
)
from app.services import interactions as interaction_svc


def _parse_occurred_at(value) -> datetime:
    """Turn the LLM's extracted date string (YYYY-MM-DD, or full ISO) into a datetime.

    The extractor usually returns a date only, which parses to midnight. In that case we
    stamp it with the current time-of-day so the logged 'time' reflects when the rep is
    recording it (rather than always showing 00:00). Falls back to now if unparseable."""
    now = datetime.now()
    if not value:
        return now
    try:
        dt = datetime.fromisoformat(str(value))
    except ValueError:
        try:
            dt = datetime.strptime(str(value)[:10], "%Y-%m-%d")
        except ValueError:
            return now
    if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
        dt = dt.replace(hour=now.hour, minute=now.minute, second=now.second, microsecond=0)
    return dt


def build_tools(db: Session, ctx: dict):
    """Build the 5 LangGraph tools bound to a DB session and a per-conversation context.

    ctx tracks {"hcp_id": uuid|None, "last_interaction_id": uuid|None} so the agent can
    resolve references like "that interaction" / "the last one" across turns.
    """

    @tool
    def log_interaction(hcp_name: str, raw_notes: str) -> str:
        """Log a new HCP interaction from free-text notes (e.g. dictated or typed by the rep).
        Uses the LLM to extract interaction type, topics discussed, materials/samples shared,
        HCP sentiment, outcomes, and follow-up actions from the raw notes, then saves the record.
        Also generates AI-suggested follow-up tasks. Use this whenever the user describes a visit,
        call, or meeting with an HCP in natural language."""
        hcp = interaction_svc.find_hcp_by_name(db, hcp_name)
        if hcp is None:
            return f"No HCP found matching '{hcp_name}'. Ask the user to confirm the HCP name."

        fields = extract_interaction_fields(raw_notes)
        data = {
            "hcp_id": hcp.id,
            "interaction_type": fields.get("interaction_type", "Meeting"),
            "occurred_at": _parse_occurred_at(fields.get("occurred_at")),
            "attendees": [],
            "topics_discussed": fields.get("topics_discussed", ""),
            "materials_shared": fields.get("materials_shared", []) or [],
            "samples_distributed": fields.get("samples_distributed", []) or [],
            "sentiment": fields.get("sentiment", "Neutral"),
            "outcomes": fields.get("outcomes", ""),
            "follow_up_actions": fields.get("follow_up_actions", ""),
            "source": "chat",
        }
        interaction = interaction_svc.create_interaction(db, data)

        follow_ups = generate_follow_ups(f"{data['topics_discussed']}\n{data['outcomes']}")
        if follow_ups:
            interaction_svc.update_interaction(db, interaction.id, {"suggested_follow_ups": follow_ups})

        ctx["last_interaction_id"] = interaction.id
        ctx["hcp_id"] = hcp.id
        return (
            f"Logged {data['interaction_type']} with {hcp.name} (sentiment: {data['sentiment']}). "
            f"Suggested follow-ups: {follow_ups or 'none'}."
        )

    @tool
    def edit_interaction(instruction: str, interaction_id: str = "last") -> str:
        """Edit a previously logged interaction. `instruction` is a free-text description of what
        to change (e.g. "change sentiment to positive", "add that we shared the OncoBoost brochure").
        `interaction_id` can be a specific UUID or the literal "last" to mean the most recently
        logged/discussed interaction in this conversation."""
        target_id = ctx.get("last_interaction_id") if interaction_id == "last" else uuid.UUID(interaction_id)
        if target_id is None:
            return "No interaction is currently in context to edit. Log one first or provide an interaction id."

        existing = interaction_svc.get_interaction(db, target_id)
        if existing is None:
            return f"No interaction found with id {target_id}."

        current_summary = (
            f"interaction_type={existing.interaction_type}, "
            f"occurred_at={existing.occurred_at.date().isoformat()}, "
            f"topics_discussed={existing.topics_discussed}, "
            f"materials_shared={existing.materials_shared}, samples_distributed={existing.samples_distributed}, "
            f"sentiment={existing.sentiment}, outcomes={existing.outcomes}, "
            f"follow_up_actions={existing.follow_up_actions}"
        )
        fields = extract_interaction_fields(f"Current record: {current_summary}\nRequested change: {instruction}")
        update_data = {k: v for k, v in fields.items() if v not in (None, "", [])}
        if "occurred_at" in update_data:
            update_data["occurred_at"] = _parse_occurred_at(update_data["occurred_at"])
        updated = interaction_svc.update_interaction(db, target_id, update_data)
        ctx["last_interaction_id"] = updated.id
        hcp_name = updated.hcp.name if updated.hcp else "the HCP"
        return f"Updated the interaction with {hcp_name}. New sentiment: {updated.sentiment}, outcomes: {updated.outcomes or 'unchanged'}"

    @tool
    def get_hcp_history(hcp_name: str, limit: int = 5) -> str:
        """Retrieve the recent interaction history for a named HCP, so the rep can recall past
        conversations before logging a new one."""
        hcp = interaction_svc.find_hcp_by_name(db, hcp_name)
        if hcp is None:
            return f"No HCP found matching '{hcp_name}'."
        history = interaction_svc.list_interactions_for_hcp(db, hcp.id, limit=limit)
        if not history:
            return f"No prior interactions logged for {hcp.name}."
        lines = [
            f"- {i.occurred_at:%Y-%m-%d} [{i.interaction_type}] sentiment={i.sentiment}: {i.topics_discussed}"
            for i in history
        ]
        ctx["hcp_id"] = hcp.id
        return f"History for {hcp.name}:\n" + "\n".join(lines)

    @tool
    def detect_adverse_event(interaction_id: str = "last") -> str:
        """Scan a logged interaction's notes for any patient ADVERSE EVENT / adverse drug reaction
        (side effects, safety concerns, hospitalizations) and flag it for pharmacovigilance reporting.
        In pharma, adverse events are legally reportable, so run this on any interaction where a patient
        outcome or safety issue may have been mentioned. When an adverse event is found, this tool also
        DRAFTS a pharmacovigilance notification email to the Drug Safety team (the draft is saved for the
        rep to review and send — it is not sent automatically). `interaction_id` may be a UUID or "last"
        for the most recent interaction in the conversation."""
        target_id = ctx.get("last_interaction_id") if interaction_id == "last" else uuid.UUID(interaction_id)
        if target_id is None:
            return "No interaction is currently in context. Log one first."
        existing = interaction_svc.get_interaction(db, target_id)
        if existing is None:
            return f"No interaction found with id {target_id}."

        result = detect_adverse_events(f"{existing.topics_discussed}\n{existing.outcomes}")
        events = result.get("adverse_events", []) or []

        if not events:
            interaction_svc.update_interaction(db, target_id, {"adverse_events": [], "adverse_event_report": ""})
            return "No adverse events detected. No pharmacovigilance report required for this interaction."

        hcp_name = existing.hcp.name if existing.hcp else "the HCP"
        email_draft = draft_adverse_event_email(
            f"HCP: {hcp_name}\nAdverse events: {events}\n"
            f"Reporting required within 24h: {result.get('reporting_required')}"
        )
        interaction_svc.update_interaction(
            db, target_id, {"adverse_events": events, "adverse_event_report": email_draft}
        )

        lines = [
            f"- {e.get('description', 'unspecified')} "
            f"(drug: {e.get('drug', 'unspecified')}, {e.get('seriousness', 'non-serious')})"
            for e in events
        ]
        flag = (
            "⚠️ REPORTING REQUIRED: serious adverse event — submit within 24h."
            if result.get("reporting_required")
            else "Non-serious; log per standard pharmacovigilance procedure."
        )
        return (
            "Adverse event(s) detected:\n" + "\n".join(lines) + f"\n{flag}\n\n"
            "I've drafted a pharmacovigilance notification email to the Drug Safety team "
            "(saved on the interaction for your review — not sent automatically):\n\n" + email_draft
        )

    @tool
    def analyze_hcp_engagement(hcp_name: str) -> str:
        """Analyze a named HCP's full interaction history and report their sentiment trend
        (warming up / stable / cooling off), overall engagement level, and a recommended next action
        for the field rep. Use when the rep asks how a relationship is trending or how to approach an HCP."""
        hcp = interaction_svc.find_hcp_by_name(db, hcp_name)
        if hcp is None:
            return f"No HCP found matching '{hcp_name}'."
        history = interaction_svc.list_interactions_for_hcp(db, hcp.id, limit=20)
        if not history:
            return f"No interactions logged yet for {hcp.name} to analyze."

        summary = "\n".join(
            f"{i.occurred_at:%Y-%m-%d} [{i.interaction_type}] sentiment={i.sentiment}: {i.topics_discussed}"
            for i in reversed(history)  # oldest -> newest so the trend reads chronologically
        )
        ctx["hcp_id"] = hcp.id
        return analyze_engagement(f"HCP: {hcp.name} (specialty: {hcp.specialty})\nHistory (oldest first):\n{summary}")

    return [log_interaction, edit_interaction, get_hcp_history, detect_adverse_event, analyze_hcp_engagement]
