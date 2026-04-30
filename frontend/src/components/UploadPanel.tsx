import React, { useState } from "react";
import { useUploadContext } from "../contexts/UploadContext";

export const UploadPanel = () => {
  const { addTask, processQueue } = useUploadContext();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [authors, setAuthors] = useState("");
  const [year, setYear] = useState("");
  const [sourcePaperId, setSourcePaperId] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const isAudio =
    file?.type.startsWith("audio/") || file?.name.match(/\.(mp3|wav|m4a)$/i);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    // Add task to queue
    addTask(file, title, authors, year, isAudio ? sourcePaperId : undefined);

    // Reset form
    setFile(null);
    setTitle("");
    setAuthors("");
    setYear("");
    setSourcePaperId("");
    setSuccessMsg("✓ Added to upload queue! Processing will continue even if you switch tabs.");

    // Show success message for 3 seconds
    setTimeout(() => setSuccessMsg(""), 3000);

    // Trigger processing
    processQueue();
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-8 text-center">
        <h2 className="text-4xl md:text-5xl font-black tracking-tighter mb-2">
          <span className="text-gradient">Ingest Content</span>
        </h2>
        <p className="text-gray-400">
          Upload PDFs and audio files to build your knowledge graph. All uploads process in the background.
        </p>
      </div>

      {/* Upload Form */}
      <div className="glass-dark border border-white/10 rounded-3xl shadow-2xl shadow-blue-500/20 p-8">
        <form onSubmit={handleUpload} className="flex flex-col gap-6">
          {/* File Upload Area */}
          <div className="relative">
            <input
              type="file"
              accept="application/pdf,audio/*"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="hidden"
              id="file-input"
            />
            <label
              htmlFor="file-input"
              className={`flex flex-col items-center justify-center p-12 rounded-2xl border-2 border-dashed transition-all cursor-pointer ${
                file
                  ? "bg-cyan-500/10 border-cyan-400/50"
                  : "border-white/20 hover:border-cyan-400/50 hover:bg-cyan-500/5"
              }`}
            >
              <div className="text-5xl mb-4">
                {file ? (isAudio ? "🎵" : "📄") : "📁"}
              </div>
              {file ? (
                <div className="text-center">
                  <p className="font-semibold text-white">{file.name}</p>
                  <p className="text-sm text-gray-400 mt-2">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                  <p className="text-xs text-cyan-400 mt-3 font-medium">
                    Click to change file
                  </p>
                </div>
              ) : (
                <div className="text-center">
                  <p className="font-semibold text-white mb-2">
                    Drag & drop your file here
                  </p>
                  <p className="text-sm text-gray-400">
                    or click to select a PDF or audio file
                  </p>
                </div>
              )}
            </label>
          </div>

          {/* Title Input */}
          <div>
            <label className="block text-sm font-semibold text-white mb-2">
              Title (Optional)
            </label>
            <input
              type="text"
              placeholder="Auto-extracted from PDF or enter manually"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl focus:ring-2 focus:ring-cyan-500 focus:border-transparent outline-none transition-all text-white placeholder-gray-500"
            />
          </div>

          {/* Conditional Fields */}
          {file && !isAudio && (
            <>
              <div>
                <label className="block text-sm font-semibold text-white mb-2">
                  Authors (Optional)
                </label>
                <input
                  type="text"
                  placeholder="Comma separated list of authors"
                  value={authors}
                  onChange={(e) => setAuthors(e.target.value)}
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl focus:ring-2 focus:ring-cyan-500 focus:border-transparent outline-none transition-all text-white placeholder-gray-500"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-white mb-2">
                  Publication Year (Optional)
                </label>
                <input
                  type="number"
                  placeholder="e.g., 2024"
                  value={year}
                  onChange={(e) => setYear(e.target.value)}
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl focus:ring-2 focus:ring-cyan-500 focus:border-transparent outline-none transition-all text-white placeholder-gray-500"
                />
              </div>
            </>
          )}

          {file && isAudio && (
            <div>
              <label className="block text-sm font-semibold text-white mb-2">
                Source Paper ID (Optional)
              </label>
              <input
                type="text"
                placeholder="Link this audio to a paper"
                value={sourcePaperId}
                onChange={(e) => setSourcePaperId(e.target.value)}
                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl focus:ring-2 focus:ring-cyan-500 focus:border-transparent outline-none transition-all text-white placeholder-gray-500"
              />
            </div>
          )}

          {/* Success Message */}
          {successMsg && (
            <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-xl text-sm text-green-300 font-medium flex items-center gap-2">
              <span>✓</span>
              {successMsg}
            </div>
          )}

          {/* Submit Button */}
          <button
            disabled={!file}
            type="submit"
            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold py-3 rounded-xl hover:shadow-lg hover:shadow-blue-500/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105 flex items-center justify-center gap-2"
          >
            📤 <span>Upload & Queue</span>
          </button>

          <p className="text-xs text-gray-400 text-center">
            Uploads are processed in parallel. You can switch tabs and uploads will continue.
          </p>
        </form>
      </div>
    </div>
  );
};
