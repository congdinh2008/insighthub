"use client";

import { useState } from "react";
import type { ChatResult, ChatSource } from "@/lib/api";

export default function ChatPanel() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<ChatResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleAsk() {
    if (!question.trim()) return;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const res = await fetch("/api/proxy?target=chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `Lỗi: ${res.status}`);
      }
      setResult(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lỗi không xác định");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <h2>Hỏi đáp (RAG)</h2>
      <textarea
        placeholder="Đặt câu hỏi dựa trên tài liệu đã upload..."
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
      />
      <button onClick={handleAsk} disabled={busy || !question.trim()}>
        {busy ? "Đang truy vấn..." : "Hỏi"}
      </button>
      {error && <p className="error">{error}</p>}
      {result && (
        <>
          <div className="answer">{result.answer}</div>
          <div className="sources">
            Nguồn:{" "}
            {result.sources.length === 0
              ? "(không có)"
              : result.sources.map((s: ChatSource, i: number) => (
                  <span key={i} style={{ marginRight: "0.75rem" }}>
                    {s.filename}{" "}
                    <span style={{ color: "#888", fontSize: "0.85em" }}>
                      ({(s.similarity * 100).toFixed(1)}%)
                    </span>
                  </span>
                ))}
          </div>
          <div className="meta">Latency: {result.latency_ms} ms</div>
        </>
      )}
    </div>
  );
}
