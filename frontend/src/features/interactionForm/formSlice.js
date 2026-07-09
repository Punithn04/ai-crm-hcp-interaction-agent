import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";

import { api } from "../../api/client";

const initialState = {
  hcpId: null,
  hcpName: "",
  interactionType: "Meeting",
  date: new Date().toISOString().slice(0, 10),
  time: new Date().toTimeString().slice(0, 5),
  attendees: [],
  topicsDiscussed: "",
  materialsShared: [],
  samplesDistributed: [],
  sentiment: "Neutral",
  outcomes: "",
  followUpActions: "",
  suggestedFollowUps: [],
  adverseEvents: [],
  adverseEventReport: "",
  lastInteractionId: null,
  saveStatus: "idle", // idle | saving | success | error
  saveError: null,
};

export const saveInteraction = createAsyncThunk("form/saveInteraction", async (_, { getState }) => {
  const state = getState().form;
  if (!state.hcpId) {
    throw new Error("Please select an HCP before logging the interaction.");
  }
  const payload = {
    hcp_id: state.hcpId,
    interaction_type: state.interactionType,
    occurred_at: `${state.date}T${state.time}:00`,
    attendees: state.attendees,
    topics_discussed: state.topicsDiscussed,
    materials_shared: state.materialsShared,
    samples_distributed: state.samplesDistributed,
    sentiment: state.sentiment,
    outcomes: state.outcomes,
    follow_up_actions: state.followUpActions,
    source: "form",
  };
  if (state.lastInteractionId) {
    return api.updateInteraction(state.lastInteractionId, payload);
  }
  return api.createInteraction(payload);
});

const formSlice = createSlice({
  name: "form",
  initialState,
  reducers: {
    setField(state, action) {
      const { field, value } = action.payload;
      state[field] = value;
    },
    setHcp(state, action) {
      state.hcpId = action.payload.id;
      state.hcpName = action.payload.name;
    },
    addAttendee(state, action) {
      if (action.payload && !state.attendees.includes(action.payload)) {
        state.attendees.push(action.payload);
      }
    },
    removeAttendee(state, action) {
      state.attendees = state.attendees.filter((a) => a !== action.payload);
    },
    addMaterial(state, action) {
      if (action.payload && !state.materialsShared.includes(action.payload)) {
        state.materialsShared.push(action.payload);
      }
    },
    removeMaterial(state, action) {
      state.materialsShared = state.materialsShared.filter((m) => m !== action.payload);
    },
    addSample(state, action) {
      if (action.payload && !state.samplesDistributed.includes(action.payload)) {
        state.samplesDistributed.push(action.payload);
      }
    },
    removeSample(state, action) {
      state.samplesDistributed = state.samplesDistributed.filter((s) => s !== action.payload);
    },
    applyInteractionFromServer(state, action) {
      const i = action.payload;
      if (!i) return;
      state.lastInteractionId = i.id;
      state.hcpId = i.hcp_id;
      if (i.hcp_name) state.hcpName = i.hcp_name;
      state.interactionType = i.interaction_type;
      if (i.occurred_at) {
        // occurred_at is an ISO datetime (e.g. "2026-07-08T14:30:00"); split into the
        // form's separate date + time inputs.
        const [datePart, timePart] = i.occurred_at.split("T");
        if (datePart) state.date = datePart;
        if (timePart) state.time = timePart.slice(0, 5);
      }
      state.attendees = i.attendees ?? [];
      state.topicsDiscussed = i.topics_discussed ?? "";
      state.materialsShared = i.materials_shared ?? [];
      state.samplesDistributed = i.samples_distributed ?? [];
      state.sentiment = i.sentiment ?? "Neutral";
      state.outcomes = i.outcomes ?? "";
      state.followUpActions = i.follow_up_actions ?? "";
      state.suggestedFollowUps = i.suggested_follow_ups ?? [];
      state.adverseEvents = i.adverse_events ?? [];
      state.adverseEventReport = i.adverse_event_report ?? "";
    },
    resetSaveStatus(state) {
      state.saveStatus = "idle";
      state.saveError = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(saveInteraction.pending, (state) => {
        state.saveStatus = "saving";
        state.saveError = null;
      })
      .addCase(saveInteraction.fulfilled, (state, action) => {
        state.saveStatus = "success";
        state.lastInteractionId = action.payload.id;
        state.suggestedFollowUps = action.payload.suggested_follow_ups ?? [];
      })
      .addCase(saveInteraction.rejected, (state, action) => {
        state.saveStatus = "error";
        state.saveError = action.error.message;
      });
  },
});

export const {
  setField,
  setHcp,
  addAttendee,
  removeAttendee,
  addMaterial,
  removeMaterial,
  addSample,
  removeSample,
  applyInteractionFromServer,
  resetSaveStatus,
} = formSlice.actions;

export default formSlice.reducer;
