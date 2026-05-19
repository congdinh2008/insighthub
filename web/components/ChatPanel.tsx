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
        throw new Error(typeof d.detail === "string" ? d.detail : `Câu hỏi không hợp lệ hoặc API trả lỗi (${res.status}).`);
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
        aria-label="Câu hỏi về tài liệu"
        maxLength={2000}
        placeholder="Đặt câu hỏi dựa trên tài liệu đã upload..."
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
      />
      <button onClick={handleAsk} disabled={busy || !question.trim()}>
        {busy ? "Đang truy vấn..." : "Hỏi"}
      </button>
      {error && <p className="error" role="alert">{error}</p>}
      {result && (
        <>
          <div className="answer">{result.answer}</div>
          <div className="sources">
            Nguồn: {result.sources.join(", ") || "(không có)"}
          </div>
          <div className="meta">Latency: {result.latency_ms} ms</div>
        </>
      )}
    </div>
  );
}
