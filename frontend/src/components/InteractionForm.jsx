import { useDispatch, useSelector } from "react-redux";

import { api } from "../api/client";
import {
  addAttendee,
  addMaterial,
  addSample,
  removeAttendee,
  removeMaterial,
  removeSample,
  resetSaveStatus,
  saveInteraction,
  setField,
} from "../features/interactionForm/formSlice";
import HcpSearchInput from "./HcpSearchInput";
import TagAdder from "./TagAdder";

const INTERACTION_TYPES = ["Meeting", "Call", "Email", "Conference"];
const SENTIMENTS = ["Positive", "Neutral", "Negative"];

export default function InteractionForm() {
  const dispatch = useDispatch();
  const form = useSelector((s) => s.form);

  const field = (name) => (e) => dispatch(setField({ field: name, value: e.target.value }));

  const handleLog = () => {
    dispatch(saveInteraction());
  };

  return (
    <div className="card">
      <div className="card-title">Log HCP Interaction</div>

      {form.saveStatus === "success" && (
        <div className="status-banner success">
          Interaction saved successfully.{" "}
          <button className="btn" style={{ marginLeft: 8 }} onClick={() => dispatch(resetSaveStatus())}>
            Dismiss
          </button>
        </div>
      )}
      {form.saveStatus === "error" && (
        <div className="status-banner error">Failed to save: {form.saveError}</div>
      )}

      <div className="row-2">
        <HcpSearchInput />
        <div className="field">
          <label>Interaction Type</label>
          <select value={form.interactionType} onChange={field("interactionType")}>
            {INTERACTION_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="row-2">
        <div className="field">
          <label>Date</label>
          <input type="date" value={form.date} onChange={field("date")} />
        </div>
        <div className="field">
          <label>Time</label>
          <input type="time" value={form.time} onChange={field("time")} />
        </div>
      </div>

      <TagAdder
        label="Attendees"
        items={form.attendees}
        onAdd={(v) => dispatch(addAttendee(v))}
        onRemove={(v) => dispatch(removeAttendee(v))}
        buttonLabel="Add"
        placeholder="Enter names or search..."
      />

      <div className="field">
        <label>Topics Discussed</label>
        <textarea
          value={form.topicsDiscussed}
          onChange={field("topicsDiscussed")}
          placeholder="Enter key discussion points..."
        />
      </div>

      <TagAdder
        label="Materials Shared"
        items={form.materialsShared}
        onAdd={(v) => dispatch(addMaterial(v))}
        onRemove={(v) => dispatch(removeMaterial(v))}
        searchFn={(q) => api.searchMaterials(q, "material")}
        buttonLabel="Search/Add"
        placeholder="Search materials..."
      />

      <TagAdder
        label="Samples Distributed"
        items={form.samplesDistributed}
        onAdd={(v) => dispatch(addSample(v))}
        onRemove={(v) => dispatch(removeSample(v))}
        searchFn={(q) => api.searchMaterials(q, "sample")}
        buttonLabel="Add Sample"
        placeholder="Search samples..."
      />

      <div className="field">
        <label>Observed/Inferred HCP Sentiment</label>
        <div className="sentiment-row">
          {SENTIMENTS.map((s) => (
            <label key={s}>
              <input
                type="radio"
                name="sentiment"
                checked={form.sentiment === s}
                onChange={() => dispatch(setField({ field: "sentiment", value: s }))}
              />
              {s}
            </label>
          ))}
        </div>
      </div>

      <div className="field">
        <label>Outcomes</label>
        <textarea value={form.outcomes} onChange={field("outcomes")} placeholder="Key outcomes or agreements..." />
      </div>

      <div className="field">
        <label>Follow-up Actions</label>
        <textarea
          value={form.followUpActions}
          onChange={field("followUpActions")}
          placeholder="Enter next steps or tasks..."
        />
      </div>

      {form.adverseEvents.length > 0 && (
        <div className="adverse-events">
          <strong>⚠️ Adverse Event(s) Detected — Pharmacovigilance</strong>
          <ul>
            {form.adverseEvents.map((e, idx) => (
              <li key={idx}>
                {e.description}
                {e.drug ? ` (drug: ${e.drug})` : ""}
                {e.seriousness ? ` — ${e.seriousness}` : ""}
              </li>
            ))}
          </ul>
          {form.adverseEventReport && (
            <details className="ae-report">
              <summary>📧 Drafted pharmacovigilance email (review &amp; send)</summary>
              <pre>{form.adverseEventReport}</pre>
            </details>
          )}
        </div>
      )}

      {form.suggestedFollowUps.length > 0 && (
        <div className="suggested-followups">
          <strong>AI Suggested Follow-ups:</strong>
          <ul>
            {form.suggestedFollowUps.map((f, idx) => (
              <li key={idx}>{f}</li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ marginTop: 16, textAlign: "right" }}>
        <button className="btn btn-primary" onClick={handleLog} disabled={form.saveStatus === "saving"}>
          {form.saveStatus === "saving" ? "Saving..." : "Log Interaction"}
        </button>
      </div>
    </div>
  );
}
