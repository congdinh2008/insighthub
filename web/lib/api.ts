// InsightHub Web — API client
// Server Components / Route Handlers gọi API qua docker network (API_INTERNAL_URL).

const API_URL = process.env.API_INTERNAL_URL || "http://api:8000";

export interface Document {
  id: number;
  filename: string;
  status: "pending" | "ready" | "failed";
  chunk_count: number;
  created_at: string | null;
}

export interface ChatSource {
  filename: string;
  similarity: number;
}

export interface ChatResult {
  answer: string;
  sources: ChatSource[];
  contexts: { source: string; similarity: number; chunk_text: string }[];
  latency_ms: number;
}

export async function listDocuments(): Promise<Document[]> {
  const res = await fetch(`${API_URL}/documents`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function askQuestion(question: string): Promise<ChatResult> {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export { API_URL };
