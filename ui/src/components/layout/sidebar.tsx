"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MessageSquare, FileText, FlaskConical, Wrench, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/chat",      label: "Chat",      icon: MessageSquare, desc: "Ask financial questions" },
  { href: "/documents", label: "Documents", icon: FileText,       desc: "Upload PDF / CSV" },
  { href: "/eval",      label: "Evaluation",icon: FlaskConical,   desc: "Test accuracy" },
  { href: "/mcp",       label: "MCP Tools", icon: Wrench,         desc: "Tool registry" },
];

export default function Sidebar() {
  const path = usePathname();

  return (
    <aside className="w-60 min-h-screen bg-gray-900 border-r border-gray-800 flex flex-col">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
            <TrendingUp className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">FinAnalyst</p>
            <p className="text-xs text-gray-500">Multi-Agent RAG</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {nav.map(({ href, label, icon: Icon, desc }) => {
          const active = path.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors group",
                active
                  ? "bg-brand-600/20 text-brand-400"
                  : "text-gray-400 hover:bg-gray-800 hover:text-gray-100"
              )}
            >
              <Icon className={cn("w-4 h-4 shrink-0", active ? "text-brand-400" : "text-gray-500 group-hover:text-gray-300")} />
              <div>
                <p className="text-sm font-medium leading-none">{label}</p>
                <p className="text-xs text-gray-600 mt-0.5">{desc}</p>
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Langfuse link */}
      <div className="px-4 py-4 border-t border-gray-800">
        <a
          href={process.env.NEXT_PUBLIC_LANGFUSE_URL || "http://localhost:3000"}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          <span className="w-2 h-2 rounded-full bg-brand-500 animate-pulse" />
          Open Langfuse →
        </a>
      </div>
    </aside>
  );
}
