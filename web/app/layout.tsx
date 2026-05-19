import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "InsightHub - RAG Notebook",
  description: "AI-Native DevOps training project",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
