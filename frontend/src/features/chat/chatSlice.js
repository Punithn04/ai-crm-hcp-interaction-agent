import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";

import { api } from "../../api/client";

const initialState = {
  threadId: `thread-${Date.now()}`,
  messages: [
    {
      role: "assistant",
      content:
        'Log interaction details here (e.g., "Met Dr. Smith, discussed Product X efficacy, positive sentiment, shared brochure") or ask for help.',
    },
  ],
  pending: false,
  error: null,
};

export const sendMessage = createAsyncThunk(
  "chat/sendMessage",
  async (message, { getState }) => {
    const state = getState();
    const hcpId = state.form.hcpId;
    const response = await api.sendChatMessage({
      message,
      hcp_id: hcpId,
      thread_id: state.chat.threadId,
    });
    return response;
  }
);

const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    addUserMessage(state, action) {
      state.messages.push({ role: "user", content: action.payload });
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state) => {
        state.pending = true;
        state.error = null;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.pending = false;
        state.messages.push({ role: "assistant", content: action.payload.reply });
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.pending = false;
        state.error = action.error.message;
        state.messages.push({
          role: "assistant",
          content: "Sorry, something went wrong reaching the AI assistant.",
        });
      });
  },
});

export const { addUserMessage } = chatSlice.actions;
export default chatSlice.reducer;
