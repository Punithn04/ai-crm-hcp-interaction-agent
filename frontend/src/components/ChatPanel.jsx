import { useEffect, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import { applyInteractionFromServer } from "../features/interactionForm/formSlice";
import { addUserMessage, sendMessage } from "../features/chat/chatSlice";

export default function ChatPanel() {
  const dispatch = useDispatch();
  const { messages, pending } = useSelector((s) => s.chat);
  const [input, setInput] = useState("");
  const listRef = useRef(null);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || pending) return;
    dispatch(addUserMessage(text));
    setInput("");
    const result = await dispatch(sendMessage(text));
    if (sendMessage.fulfilled.match(result) && result.payload.interaction) {
      dispatch(applyInteractionFromServer(result.payload.interaction));
    }
  };

  return (
    <div className="card chat-card">
      <div className="chat-header">🤖 AI Assistant</div>
      <div className="chat-subheader">Log interaction via chat</div>

      <div className="chat-messages" ref={listRef}>
        {messages.map((m, idx) => (
          <div key={idx} className={`chat-bubble ${m.role}`}>
            {m.content}
          </div>
        ))}
        {pending && <div className="chat-bubble assistant">Thinking…</div>}
      </div>

      <div className="chat-input-row">
        <input
          type="text"
          placeholder="Describe interaction..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
        />
        <button className="btn btn-primary" onClick={handleSend} disabled={pending}>
          Log
        </button>
      </div>
    </div>
  );
}
