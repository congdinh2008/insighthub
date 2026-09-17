"use client";

import { useEffect, useState } from "react";
import type { Document } from "@/lib/api";

export default function UploadPanel({ initial, initialError = "" }: { initial: Document[]; initialError?: string }) {
  const [docs, setDocs] = useState<Document[]>(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(initialError);
  const [pollError, setPollError] = useState("");
  const [pollCycle, setPollCycle] = useState(0);
  const [pollingStopped, setPollingStopped] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(!initialError);
  const pending = docs.some((doc) => doc.status === "pending");

  useEffect(() => {
    if (!pending) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    let attempts = 0;
    setPollingStopped(false);
    async function poll() {
      attempts += 1;
      let stillPending = true;
      try {
        const res = await fetch("/api/documents", { cache: "no-store", signal: controller.signal });
        if (!res.ok) throw new Error("Không đọc được trạng thái tài liệu.");
        const items: Document[] = await res.json();
        if (controller.signal.aborted) return;
        setDocs(items);
        setHasLoaded(true);
        setPollError("");
        stillPending = items.some((doc) => doc.status === "pending");
      } catch (err) {
        if (controller.signal.aborted) return;
        setPollError("Không đọc được trạng thái tài liệu. Đang thử lại...");
      }
      if (controller.signal.aborted || !stillPending) return;
      if (attempts < 60) {
        timer = setTimeout(poll, 2000);
      } else {
        setPollingStopped(true);
        setPollError("Chưa hoàn tất sau 60 lần kiểm tra. Kiểm tra worker hoặc làm mới trạng thái.");
      }
    }
    timer = setTimeout(poll, 2000);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [pending, pollCycle]);

  async function refresh(clearUploadError = true) {
    const res = await fetch("/api/documents", { cache: "no-store" });
    if (!res.ok) throw new Error("API chưa sẵn sàng.");
    setDocs(await res.json());
    setHasLoaded(true);
    setPollError("");
    setPollingStopped(false);
    setPollCycle((cycle) => cycle + 1);
    if (clearUploadError) setError("");
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      setError("File vượt quá 10 MB.");
      e.target.value = "";
      return;
    }
    setBusy(true);
    setError("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch("/api/proxy?target=upload", {
        method: "POST",
        body: fd,
        signal: AbortSignal.timeout(90000),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `Upload lỗi: ${res.status}`);
      }
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lỗi không xác định");
      // Rejected uploads can still create failed metadata. Preserve their error.
      await refresh(false).catch(() => {});
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  }

  return (
    <div className="panel">
      <h2>Tài liệu</h2>
      <input
        type="file"
        aria-label="Chọn tài liệu .txt, .md hoặc .pdf"
        accept=".txt,.md,.pdf"
        onChange={handleUpload}
        disabled={busy}
      />
      {busy && <p className="meta">Đang gửi tài liệu...</p>}
      {pending && <p className="meta" role="status">{pollingStopped ? "Tự động cập nhật đã dừng. Hãy làm mới trạng thái." : "Đang chờ xử lý. Trạng thái sẽ tự cập nhật."}</p>}
      <button onClick={() => { setError(""); refresh().catch(() => setError("Không đọc được trạng thái.")); }} disabled={busy}>Làm mới trạng thái</button>
      {error && <p className="error" role="alert">{error}</p>}
      {pollError && <p className="error" role="alert">{pollError}</p>}
      <ul className="doc-list" style={{ marginTop: "1rem" }}>
        {hasLoaded && docs.length === 0 && (
          <li className="meta">Chưa có tài liệu. Upload .txt / .md / .pdf.</li>
        )}
        {docs.map((d) => (
          <li key={d.id} className="doc-item">
            <span>
              {d.filename}{" "}
              <span className="meta">({d.chunk_count} chunks)</span>
            </span>
            <span className={`badge ${d.status}`}>{d.status}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
