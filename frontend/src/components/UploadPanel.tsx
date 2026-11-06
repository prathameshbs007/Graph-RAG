import React, { useState } from "react";
import { useUploadContext } from "../contexts/UploadContext";

export const UploadPanel = () => {
  const { addTask, processQueue } = useUploadContext();
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [audioFile, setAudioFile] = useState<File | null>(null);

  const [title, setTitle] = useState("");
  const [authors, setAuthors] = useState("");
  const [year, setYear] = useState("");
  const [sourcePaperId, setSourcePaperId] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const handlePdfSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!pdfFile) return;

    addTask(pdfFile, title, authors, year);
    setPdfFile(null);
    setTitle("");
    setAuthors("");
    setYear("");
    setSuccessMsg("✓ PDF queued for ingestion! Processing runs in the background.");
    setTimeout(() => setSuccessMsg(""), 4000);
    processQueue();
  };

  const handleAudioSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!audioFile) return;

    addTask(audioFile, title, "", "", sourcePaperId || undefined);
    setAudioFile(null);
    setTitle("");
    setSourcePaperId("");
    setSuccessMsg("✓ Audio talk queued for Whisper transcription & ingestion!");
    setTimeout(() => setSuccessMsg(""), 4000);
    processQueue();
  };

  return (
    <div className="w-full space-y-6 text-on-surface">
      {/* Top Utility Metadata Strip */}
      <div className="w-full flex flex-col md:flex-row md:items-center justify-between gap-3 pb-2 border-b border-surface-container-highest/30">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-secondary animate-ping"></span>
            <span className="font-semibold text-sm text-on-surface tracking-tight">
              Multi-Modal Ingestion Pipeline
            </span>
          </div>
          <span className="font-mono text-xs px-2 py-0.5 rounded bg-surface-container-high text-primary tracking-wide">
            ETL-ORCHESTRATOR::ONLINE
          </span>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs text-on-surface-variant">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-container">
            <span className="material-symbols-outlined text-[14px] text-secondary">memory</span>
            <span>Weaviate 1,024-dim</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-container">
            <span className="material-symbols-outlined text-[14px] text-primary">lan</span>
            <span>Neo4j Bolt: 7687</span>
          </div>
        </div>
      </div>

      {successMsg && (
        <div className="p-3 bg-secondary/15 border border-secondary/30 rounded-xl text-xs font-mono text-secondary flex items-center gap-2">
          <span className="material-symbols-outlined text-[1rem]">check_circle</span>
          <span>{successMsg}</span>
        </div>
      )}

      {/* Dual Dropzone Area */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Left: Research Papers (PDF) */}
        <div className="rounded-xl bg-surface-container/60 border border-surface-container-highest/50 p-5 flex flex-col justify-between shadow-xl">
          <div>
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-lg bg-surface-container-high flex items-center justify-center text-primary shadow-sm">
                  <span className="material-symbols-outlined text-[1.25rem]">description</span>
                </div>
                <div>
                  <h3 className="font-semibold text-sm text-on-surface">Research Papers & Preprints</h3>
                  <p className="text-xs text-on-surface-variant">Extract text, math chunks, & figure bounding boxes</p>
                </div>
              </div>
              <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-surface-container-highest text-secondary-fixed uppercase">
                PDF ≤ 100MB
              </span>
            </div>

            <form onSubmit={handlePdfSubmit} className="space-y-3">
              <div className="relative">
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
                  className="hidden"
                  id="file-input-pdf"
                />
                <label
                  htmlFor="file-input-pdf"
                  className={`flex flex-col items-center justify-center p-6 rounded-xl border-2 border-dashed transition-all cursor-pointer ${
                    pdfFile
                      ? "bg-primary/10 border-primary"
                      : "border-surface-container-highest/80 hover:border-primary/50 bg-surface-container-lowest/50"
                  }`}
                >
                  <span className="material-symbols-outlined text-[2rem] text-primary mb-1">
                    upload_file
                  </span>
                  {pdfFile ? (
                    <div className="text-center font-mono">
                      <p className="text-xs font-semibold text-on-surface truncate max-w-xs">{pdfFile.name}</p>
                      <p className="text-[10px] text-outline mt-0.5">{(pdfFile.size / (1024 * 1024)).toFixed(2)} MB</p>
                    </div>
                  ) : (
                    <div className="text-center">
                      <p className="text-xs font-medium text-on-surface">Click or drag PDF preprint here</p>
                      <p className="text-[10px] text-outline mt-0.5">PyMuPDF visual layout + BGE vectorization</p>
                    </div>
                  )}
                </label>
              </div>

              <div>
                <input
                  type="text"
                  placeholder="Paper title (optional, auto-extracted if empty)"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-container-lowest border border-surface-container-highest/50 rounded-lg text-xs font-mono text-on-surface placeholder:text-outline focus:outline-none focus:border-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <input
                  type="text"
                  placeholder="Authors (e.g. Thorne, Alvarez)"
                  value={authors}
                  onChange={(e) => setAuthors(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-container-lowest border border-surface-container-highest/50 rounded-lg text-xs font-mono text-on-surface placeholder:text-outline focus:outline-none focus:border-primary"
                />
                <input
                  type="number"
                  placeholder="Year (e.g. 2024)"
                  value={year}
                  onChange={(e) => setYear(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-container-lowest border border-surface-container-highest/50 rounded-lg text-xs font-mono text-on-surface placeholder:text-outline focus:outline-none focus:border-primary"
                />
              </div>

              <button
                type="submit"
                disabled={!pdfFile}
                className="w-full py-2.5 rounded-lg bg-primary text-on-primary font-semibold text-xs shadow-md hover:brightness-110 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-1.5"
              >
                <span className="material-symbols-outlined text-[1rem]">publish</span>
                <span>Ingest & Build Graph</span>
              </button>
            </form>
          </div>
        </div>

        {/* Right: Conference Talks & Audio */}
        <div className="rounded-xl bg-surface-container/60 border border-surface-container-highest/50 p-5 flex flex-col justify-between shadow-xl">
          <div>
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-lg bg-surface-container-high flex items-center justify-center text-secondary shadow-sm">
                  <span className="material-symbols-outlined text-[1.25rem]">graphic_eq</span>
                </div>
                <div>
                  <h3 className="font-semibold text-sm text-on-surface">Conference Talks & Lab Audio</h3>
                  <p className="text-xs text-on-surface-variant">Whisper-v3 transcription with aligned timecodes</p>
                </div>
              </div>
              <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-surface-container-highest text-secondary-fixed uppercase">
                WAV • MP3 • M4A
              </span>
            </div>

            <form onSubmit={handleAudioSubmit} className="space-y-3">
              <div className="relative">
                <input
                  type="file"
                  accept="audio/*,.mp3,.wav,.m4a"
                  onChange={(e) => setAudioFile(e.target.files?.[0] || null)}
                  className="hidden"
                  id="file-input-audio"
                />
                <label
                  htmlFor="file-input-audio"
                  className={`flex flex-col items-center justify-center p-6 rounded-xl border-2 border-dashed transition-all cursor-pointer ${
                    audioFile
                      ? "bg-secondary/10 border-secondary"
                      : "border-surface-container-highest/80 hover:border-secondary/50 bg-surface-container-lowest/50"
                  }`}
                >
                  <span className="material-symbols-outlined text-[2rem] text-secondary mb-1">
                    mic
                  </span>
                  {audioFile ? (
                    <div className="text-center font-mono">
                      <p className="text-xs font-semibold text-on-surface truncate max-w-xs">{audioFile.name}</p>
                      <p className="text-[10px] text-outline mt-0.5">{(audioFile.size / (1024 * 1024)).toFixed(2)} MB</p>
                    </div>
                  ) : (
                    <div className="text-center">
                      <p className="text-xs font-medium text-on-surface">Click or drag audio recording here</p>
                      <p className="text-[10px] text-outline mt-0.5">Automated timestamping & speaker indexing</p>
                    </div>
                  )}
                </label>
              </div>

              <div>
                <input
                  type="text"
                  placeholder="Audio session title (e.g. CVPR 2024 Keynote)"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-container-lowest border border-surface-container-highest/50 rounded-lg text-xs font-mono text-on-surface placeholder:text-outline focus:outline-none focus:border-secondary"
                />
              </div>

              <div>
                <input
                  type="text"
                  placeholder="Related Paper Title or ID (Optional, links audio to paper)"
                  value={sourcePaperId}
                  onChange={(e) => setSourcePaperId(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-container-lowest border border-surface-container-highest/50 rounded-lg text-xs font-mono text-on-surface placeholder:text-outline focus:outline-none focus:border-secondary"
                />
              </div>

              <button
                type="submit"
                disabled={!audioFile}
                className="w-full py-2.5 rounded-lg bg-secondary text-on-secondary font-semibold text-xs shadow-md hover:brightness-110 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-1.5"
              >
                <span className="material-symbols-outlined text-[1rem]">transcribe</span>
                <span>Transcribe & Ingest Audio</span>
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
