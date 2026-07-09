import { configureStore } from "@reduxjs/toolkit";

import chatReducer from "../features/chat/chatSlice";
import formReducer from "../features/interactionForm/formSlice";

export const store = configureStore({
  reducer: {
    form: formReducer,
    chat: chatReducer,
  },
});
