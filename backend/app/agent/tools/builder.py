import uuid
from datetime import datetime

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.agent.extraction import extract_interaction_fields, generate_follow_ups
from app.services import interactions as interaction_svc
from app.services import materials as material_svc


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
            "occurred_at": datetime.utcnow(),
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
            f"Interaction id: {interaction.id}. Suggested follow-ups: {follow_ups or 'none'}."
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
            f"interaction_type={existing.interaction_type}, topics_discussed={existing.topics_discussed}, "
            f"materials_shared={existing.materials_shared}, samples_distributed={existing.samples_distributed}, "
            f"sentiment={existing.sentiment}, outcomes={existing.outcomes}, "
            f"follow_up_actions={existing.follow_up_actions}"
        )
        fields = extract_interaction_fields(f"Current record: {current_summary}\nRequested change: {instruction}")
        update_data = {k: v for k, v in fields.items() if v not in (None, "", [])}
        updated = interaction_svc.update_interaction(db, target_id, update_data)
        ctx["last_interaction_id"] = updated.id
        return f"Updated interaction {updated.id}. New sentiment: {updated.sentiment}, outcomes: {updated.outcomes}"

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
    def suggest_follow_up(interaction_id: str = "last") -> str:
        """Generate AI-suggested follow-up actions for a logged interaction and attach them to
        that record. `interaction_id` may be a UUID or "last" for the most recent interaction."""
        target_id = ctx.get("last_interaction_id") if interaction_id == "last" else uuid.UUID(interaction_id)
        if target_id is None:
            return "No interaction is currently in context."
        existing = interaction_svc.get_interaction(db, target_id)
        if existing is None:
            return f"No interaction found with id {target_id}."
        follow_ups = generate_follow_ups(f"{existing.topics_discussed}\n{existing.outcomes}")
        interaction_svc.update_interaction(db, target_id, {"suggested_follow_ups": follow_ups})
        return f"Suggested follow-ups: {follow_ups}"

    @tool
    def search_materials(query: str, kind: str = "material") -> str:
        """Search the catalog of marketing materials or drug samples available to share with an HCP.
        `kind` is either "material" (brochures/decks) or "sample" (drug samples)."""
        results = material_svc.search_materials(db, query, kind=kind)
        if not results:
            return f"No {kind}s found matching '{query}'."
        return ", ".join(r.name for r in results)

    return [log_interaction, edit_interaction, get_hcp_history, suggest_follow_up, search_materials]
