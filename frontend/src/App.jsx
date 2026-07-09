import ChatPanel from "./components/ChatPanel";
import InteractionForm from "./components/InteractionForm";

export default function App() {
  return (
    <div className="app-shell">
      <div className="app-title">Log HCP Interaction</div>
      <div className="screen">
        <InteractionForm />
        <ChatPanel />
      </div>
    </div>
  );
}
