import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/layout/sidebar";

export const metadata: Metadata = {
  title: "AI Financial Analyst",
  description: "Multi-Agent RAG system for financial analysis",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </body>
    </html>
  );
}
