"use client";

import { useState } from "react";
import type { ChatResult } from "@/lib/api";

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

  // Deduplicate sources by filename, keep highest similarity per source
  const sourceSummary = result
    ? Object.values(
        result.contexts.reduce<Record<string, { source: string; similarity: number }>>(
          (acc, ctx) => {
            if (!acc[ctx.source] || ctx.similarity > acc[ctx.source].similarity) {
              acc[ctx.source] = { source: ctx.source, similarity: ctx.similarity };
            }
            return acc;
          },
          {}
        )
      ).sort((a, b) => b.similarity - a.similarity)
    : [];

  return (
    <div className="panel">
      <h2>Hỏi đáp (RAG)</h2>
      <textarea
        placeholder="Đặt câu hỏi dựa trên tài liệu đã upload..."
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) handleAsk();
        }}
      />
      <button onClick={handleAsk} disabled={busy || !question.trim()}>
        {busy ? "Đang truy vấn..." : "Hỏi (Ctrl+Enter)"}
      </button>

      {error && <p className="error">{error}</p>}

      {result && (
        <>
          <div className="answer">{result.answer}</div>

          {sourceSummary.length > 0 && (
            <div className="sources">
              <strong>Nguồn trích dẫn:</strong>
              <ul style={{ margin: "0.5rem 0 0", paddingLeft: "1.2rem" }}>
                {sourceSummary.map(({ source, similarity }) => (
                  <li key={source} style={{ marginBottom: "0.25rem" }}>
                    <span>{source}</span>{" "}
                    <span
                      className="meta"
                      title="Điểm tương đồng cosine — càng gần 1.0 càng liên quan"
                    >
                      (similarity: {(similarity * 100).toFixed(1)}%)
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="meta">Latency: {result.latency_ms} ms</div>
        </>
      )}
    </div>
  );
}
