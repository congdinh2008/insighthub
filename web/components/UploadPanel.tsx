"use client";

import { useEffect, useState } from "react";
import type { Document } from "@/lib/api";

export default function UploadPanel({ initial, initialError = "" }: { initial: Document[]; initialError?: string }) {
  const [docs, setDocs] = useState<Document[]>(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(initialError);
  const [hasLoaded, setHasLoaded] = useState(!initialError);
  const pending = docs.some((doc) => doc.status === "pending");

  useEffect(() => {
    if (!pending) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    let attempts = 0;
    async function poll() {
      try {
        const res = await fetch("/api/documents", { cache: "no-store", signal: controller.signal });
        if (!res.ok) throw new Error("Không đọc được trạng thái tài liệu.");
        const items: Document[] = await res.json();
        setDocs(items);
        if (items.some((doc) => doc.status === "pending") && ++attempts < 60) {
          timer = setTimeout(poll, 2000);
        } else if (items.some((doc) => doc.status === "pending")) {
          setError("Chưa hoàn tất sau 2 phút. Kiểm tra worker hoặc làm mới trạng thái.");
        }
      } catch (err) {
        if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "Không đọc được trạng thái.");
      }
    }
    timer = setTimeout(poll, 2000);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [pending]);

  async function refresh() {
    const res = await fetch("/api/documents", { cache: "no-store" });
    if (!res.ok) throw new Error("API chưa sẵn sàng.");
    setDocs(await res.json());
    setHasLoaded(true);
    setError("");
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
      {pending && <p className="meta" role="status">Đang chờ xử lý. Trạng thái sẽ tự cập nhật.</p>}
      <button onClick={() => { setError(""); refresh().catch(() => setError("Không đọc được trạng thái.")); }} disabled={busy}>Làm mới trạng thái</button>
      {error && <p className="error" role="alert">{error}</p>}
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
