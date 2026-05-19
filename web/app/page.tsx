import UploadPanel from "@/components/UploadPanel";
import ChatPanel from "@/components/ChatPanel";
import { listDocuments } from "@/lib/api";
import type { Document } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Home() {
  let docs: Document[] = [];
  let initialError = "";
  try {
    docs = await listDocuments();
  } catch {
    initialError = "Không tải được danh sách tài liệu. Kiểm tra API rồi làm mới trạng thái.";
  }

  return (
    <div className="container">
      <header>
        <h1>InsightHub</h1>
        <p>RAG Notebook - AI for DevOps DO2603</p>
      </header>

      <div className="grid">
        <UploadPanel initial={docs} initialError={initialError} />
        <ChatPanel />
      </div>

      <footer>
        InsightHub starter DO2603 · Next.js + FastAPI + pgvector ·
        Đây là project nền cho 7 buổi học - học viên sẽ containerize,
        deploy, observe, secure và tối ưu cost.
      </footer>
    </div>
  );
}
