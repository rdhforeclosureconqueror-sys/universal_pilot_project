import { useMemo, useRef, useState } from "react";
import { apiClient } from "../services/apiClient";

type ChatRole = "ai" | "user" | "system";

interface ChatMessage {
  id: string;
  role: ChatRole;
  text: string;
  actions?: string[];
  results?: unknown;
}

const investorDemoSteps = [
  "Find foreclosure leads in Dallas",
  "Score leads",
  "Create case from highest scoring lead",
  "Skiptrace homeowner",
  "Calculate foreclosure rescue eligibility",
  "Discover housing assistance programs",
  "Generate homeowner rescue action plan",
  "Show portfolio impact analysis",
];

export const MufasaAssistant = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: crypto.randomUUID(), role: "ai", text: "Welcome. How can I help?" },
  ]);

  const [prompt, setPrompt] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [executionIndicator, setExecutionIndicator] = useState<string>("");
  const [investorMode, setInvestorMode] = useState(false);

  const threadRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      threadRef.current?.scrollTo({
        top: threadRef.current.scrollHeight,
        behavior: "smooth",
      });
    });
  };

  const pushMessage = (message: ChatMessage) => {
    setMessages((prev) => [...prev, message]);
    scrollToBottom();
  };

  const streamAiMessage = async (
    content: string,
    actions: string[],
    results: unknown,
  ) => {
    const id = crypto.randomUUID();

    pushMessage({
      id,
      role: "ai",
      text: "",
      actions,
      results,
    });

    for (let index = 1; index <= content.length; index += 3) {
      const chunk = content.slice(0, index);

      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, text: chunk } : m)),
      );

      await new Promise((resolve) => setTimeout(resolve, 8));
    }
  };

  const indicatorFromPrompt = (text: string) => {
    const p = text.toLowerCase();

    if (p.includes("foreclosure")) return "Running foreclosure scan...";
    if (p.includes("score")) return "Scoring leads...";
    if (p.includes("skiptrace")) return "Skiptrace complete";
    if (p.includes("action plan") || p.includes("assistance"))
      return "Generating homeowner rescue plan...";

    return "Executing platform actions...";
  };

  const sendPrompt = async (message: string) => {
    const trimmed = message.trim();

    if (!trimmed) return;

    pushMessage({
      id: crypto.randomUUID(),
      role: "user",
      text: trimmed,
    });

    setExecutionIndicator(indicatorFromPrompt(trimmed));

    const response = await apiClient.request("/admin/ai/mufasa/chat", {
      method: "POST",
      payload: {
        prompt: trimmed,
        investor_mode: investorMode,
      },
    });

    const body = (response.data || {}) as {
      response?: string;
      actions_executed?: string[];
      results?: unknown;
      detail?: string;
    };

    if (!response.ok) {
      await streamAiMessage(
        body.detail || "I could not execute that command.",
        [],
        body,
      );
      return;
    }

    await streamAiMessage(
      body.response || "Done.",
      body.actions_executed || [],
      body.results || {},
    );
  };

  const handleSend = async () => {
    if (isRunning || !prompt.trim()) return;

    setIsRunning(true);

    try {
      const current = prompt;
      setPrompt("");

      await sendPrompt(current);
    } finally {
      setExecutionIndicator("");
      setIsRunning(false);
    }
  };

  const runInvestorDemo = async () => {
    if (isRunning) return;

    setIsRunning(true);

    try {
      for (const step of investorDemoSteps) {
        await sendPrompt(step);
      }
    } finally {
      setExecutionIndicator("");
      setIsRunning(false);
    }
  };

  const executionCount = useMemo(
    () =>
      messages.reduce(
        (count, message) => count + (message.actions?.length || 0),
        0,
      ),
    [messages],
  );

  return (
    <section
      style={{
        border: "1px solid #d7deeb",
        borderRadius: 10,
        background: "#fff",
        padding: 14,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <h2 style={{ marginTop: 0 }}>Mufasa Assistant</h2>

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <label
            style={{
              fontSize: 13,
              color: "#33466b",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <input
              type="checkbox"
              checked={investorMode}
              onChange={(event) => setInvestorMode(event.target.checked)}
            />
            Investor Mode
          </label>

          <button
            type="button"
            onClick={runInvestorDemo}
            disabled={isRunning}
            className="admin-action-button"
          >
            Run Investor Demo
          </button>
        </div>
      </div>

      {investorMode ? (
        <p style={{ marginTop: 0, color: "#2b4a7a", fontSize: 13 }}>
          Investor mode enabled: responses emphasize platform capabilities,
          architecture, and impact potential.
        </p>
      ) : null}

      <div
        ref={threadRef}
        style={{
          border: "1px solid #e1e8f5",
          borderRadius: 8,
          background: "#f8fbff",
          padding: 12,
          maxHeight: 360,
          overflowY: "auto",
          marginBottom: 12,
        }}
      >
        {messages.map((message) => (
          <div key={message.id} style={{ marginBottom: 10 }}>
            <strong>
              {message.role === "ai"
                ? "AI"
                : message.role === "user"
                ? "You"
                : "System"}
              :
            </strong>{" "}
            {message.text}

            {message.actions && message.actions.length > 0 ? (
              <div style={{ marginTop: 6, fontSize: 12, color: "#33466b" }}>
                Executed: {message.actions.join(", ")}
              </div>
            ) : null}
          </div>
        ))}
      </div>

      {executionIndicator ? (
        <p style={{ marginTop: 0, color: "#33466b" }}>{executionIndicator}</p>
      ) : null}

      <p style={{ fontSize: 12, color: "#556a90" }}>
        Total executed actions in thread: {executionCount}
      </p>

      <div style={{ display: "flex", gap: 8 }}>
        <input
          type="text"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              void handleSend();
            }
          }}
          placeholder="Find foreclosure leads in Dallas"
          style={{
            flex: 1,
            border: "1px solid #c7d2e8",
            borderRadius: 8,
            padding: "10px 12px",
          }}
        />

        <button
          type="button"
          onClick={() => void handleSend()}
          disabled={isRunning}
          className="admin-action-button"
        >
          Send
        </button>
      </div>
    </section>
  );
};