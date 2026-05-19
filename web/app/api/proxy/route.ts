import { API_URL } from "@/lib/api";

export async function POST(req: Request) {
  const target = new URL(req.url).searchParams.get("target");
  if (target !== "upload" && target !== "chat") {
    return Response.json({ detail: "Đích yêu cầu không hợp lệ." }, { status: 400 });
  }
  const maxBytes = target === "upload" ? 11 * 1024 * 1024 : 16000;
  if (Number(req.headers.get("content-length") || 0) > maxBytes) {
    return Response.json({ detail: "Yêu cầu vượt giới hạn kích thước." }, { status: 413 });
  }
  if (!req.body) return Response.json({ detail: "Thiếu dữ liệu." }, { status: 400 });
  let received = 0;
  const boundedBody = req.body.pipeThrough(new TransformStream({
    transform(chunk, controller) {
      received += chunk.byteLength;
      if (received > maxBytes) throw new Error("BODY_TOO_LARGE");
      controller.enqueue(chunk);
    },
  }));
  try {
    const options: RequestInit & { duplex: "half" } = {
      method: "POST", body: boundedBody, duplex: "half",
      headers: { "Content-Type": req.headers.get("content-type") || "application/json" },
      signal: AbortSignal.timeout(90000), cache: "no-store",
    };
    const res = await fetch(`${API_URL}/${target === "upload" ? "documents" : "chat"}`, options);
    return Response.json(await res.json(), { status: res.status });
  } catch {
    return Response.json({ detail: received > maxBytes ? "Yêu cầu vượt giới hạn kích thước." : "API không sẵn sàng hoặc đã hết thời gian chờ." }, { status: received > maxBytes ? 413 : 502 });
  }
}
