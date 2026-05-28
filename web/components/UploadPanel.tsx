"use client";

import { useEffect, useRef, useState } from "react";
import type { Document } from "@/lib/api";

export default function UploadPanel({ initial }: { initial: Document[] }) {
  const [docs, setDocs] = useState<Document[]>(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function refresh() {
    const res = await fetch("/api/documents", { cache: "no-store" });
    if (res.ok) setDocs(await res.json());
  }

  // Auto-poll every 2s while any document is still "pending"
  useEffect(() => {
    const hasPending = docs.some((d) => d.status === "pending");
    if (hasPending && !pollingRef.current) {
      pollingRef.current = setInterval(async () => {
        await refresh();
        // Stop polling once all documents leave "pending"
        setDocs((current) => {
          if (!current.some((d) => d.status === "pending")) {
            if (pollingRef.current) {
              clearInterval(pollingRef.current);
              pollingRef.current = null;
            }
          }
          return current;
        });
      }, 2000);
    } else if (!hasPending && pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    return () => {
      // Cleanup on unmount
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [docs]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch("/api/proxy?target=upload", {
        method: "POST",
        body: fd,
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `Upload lỗi: ${res.status}`);
      }
      // 202 Accepted — worker đang xử lý nền
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lỗi không xác định");
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  }

  const hasPending = docs.some((d) => d.status === "pending");

  return (
    <div className="panel">
      <h2>Tài liệu</h2>
      <input
        type="file"
        accept=".txt,.md,.pdf"
        onChange={handleUpload}
        disabled={busy}
      />
      {busy && <p className="meta">Đang upload... (worker xử lý nền)</p>}
      {hasPending && !busy && (
        <p className="meta" style={{ color: "#f59e0b" }}>
          ⏳ Worker đang xử lý — tự động cập nhật...
        </p>
      )}
      {error && <p className="error">{error}</p>}

      <ul className="doc-list" style={{ marginTop: "1rem" }}>
        {docs.length === 0 && (
          <li className="meta">Chưa có tài liệu. Upload .txt / .md / .pdf.</li>
        )}
        {docs.map((d) => (
          <li key={d.id} className="doc-item">
            <span>
              {d.filename}{" "}
              {d.status === "ready" && (
                <span className="meta">({d.chunk_count} chunks)</span>
              )}
            </span>
            <span className={`badge ${d.status}`}>{d.status}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
