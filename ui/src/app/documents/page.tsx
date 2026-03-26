"use client";

import { useState, useCallback } from "react";
import { Upload, FileText, CheckCircle, XCircle, Loader2, File } from "lucide-react";
import { ingestDocument, type IngestResult } from "@/lib/api";
import { cn } from "@/lib/utils";

interface UploadRecord {
  id: string;
  file: File;
  status: "uploading" | "success" | "error";
  result?: IngestResult;
  error?: string;
}

export default function DocumentsPage() {
  const [records, setRecords] = useState<UploadRecord[]>([]);
  const [dragging, setDragging] = useState(false);

  const uploadFile = useCallback(async (file: File) => {
    const id = Date.now().toString() + file.name;
    setRecords((prev) => [...prev, { id, file, status: "uploading" }]);

    try {
      const result = await ingestDocument(file);
      setRecords((prev) =>
        prev.map((r) => r.id === id ? { ...r, status: "success", result } : r)
      );
    } catch (err) {
      setRecords((prev) =>
        prev.map((r) =>
          r.id === id ? { ...r, status: "error", error: err instanceof Error ? err.message : "Upload failed" } : r
        )
      );
    }
  }, []);

  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    Array.from(files).forEach((f) => {
      if (f.name.endsWith(".pdf") || f.name.endsWith(".csv")) uploadFile(f);
    });
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  return (
    <div className="p-6 max-w-3xl">
      <div className="mb-6">
        <h1 className="text-lg font-semibold">Documents</h1>
        <p className="text-xs text-gray-500 mt-1">Upload PDF or CSV financial documents — they are chunked, embedded, and stored in pgvector for RAG queries.</p>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          "border-2 border-dashed rounded-2xl p-10 text-center transition-colors cursor-pointer",
          dragging ? "border-brand-500 bg-brand-500/10" : "border-gray-700 hover:border-gray-600"
        )}
        onClick={() => document.getElementById("file-input")?.click()}
      >
        <Upload className="w-8 h-8 text-gray-600 mx-auto mb-3" />
        <p className="text-sm text-gray-400">Drag & drop files here, or <span className="text-brand-400">browse</span></p>
        <p className="text-xs text-gray-600 mt-1">Supports PDF and CSV</p>
        <input
          id="file-input"
          type="file"
          accept=".pdf,.csv"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {/* Upload records */}
      {records.length > 0 && (
        <div className="mt-6 space-y-3">
          <h2 className="text-sm font-medium text-gray-400">Uploads</h2>
          {records.map((r) => (
            <div key={r.id} className="bg-gray-800/50 border border-gray-700/50 rounded-xl px-4 py-3 flex items-start gap-3">
              <div className="mt-0.5">
                {r.status === "uploading" && <Loader2 className="w-4 h-4 animate-spin text-gray-500" />}
                {r.status === "success" && <CheckCircle className="w-4 h-4 text-green-500" />}
                {r.status === "error" && <XCircle className="w-4 h-4 text-red-500" />}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <File className="w-3.5 h-3.5 text-gray-500 shrink-0" />
                  <p className="text-sm font-medium text-gray-200 truncate">{r.file.name}</p>
                  <span className="text-xs text-gray-600">
                    {(r.file.size / 1024).toFixed(0)} KB
                  </span>
                </div>

                {r.status === "uploading" && (
                  <p className="text-xs text-gray-500 mt-1">Processing...</p>
                )}
                {r.status === "success" && r.result && (
                  <div className="flex gap-4 mt-1.5">
                    <Stat label="Pages" value={r.result.pages} />
                    <Stat label="Chunks" value={r.result.chunks} />
                    <span className="text-xs text-green-400 font-medium">{r.result.status}</span>
                  </div>
                )}
                {r.status === "error" && (
                  <p className="text-xs text-red-400 mt-1">{r.error}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Info box */}
      <div className="mt-8 bg-gray-800/30 border border-gray-700/50 rounded-xl p-4">
        <p className="text-xs font-medium text-gray-400 mb-2">How ingestion works</p>
        <div className="space-y-1.5">
          {[
            ["1. Load", "PDF pages or CSV rows extracted as text"],
            ["2. Chunk", "Split into 500-token overlapping pieces"],
            ["3. Embed", "Each chunk → 1536-dim vector (text-embedding-3-small)"],
            ["4. Store", "Vectors saved to pgvector for similarity search"],
          ].map(([step, desc]) => (
            <div key={step} className="flex gap-3">
              <span className="text-xs font-mono text-brand-500 w-16 shrink-0">{step}</span>
              <span className="text-xs text-gray-500">{desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-1">
      <span className="text-xs text-gray-500">{label}:</span>
      <span className="text-xs text-gray-200 font-medium">{value}</span>
    </div>
  );
}
