// InsightHub Web — list documents proxy cho client component
import { listDocuments } from "@/lib/api";

export async function GET() {
  try {
    const docs = await listDocuments();
    return Response.json(docs);
  } catch {
    return Response.json([], { status: 502 });
  }
}
