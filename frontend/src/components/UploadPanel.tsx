import React, { useState } from "react";

export const UploadPanel = () => {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [authors, setAuthors] = useState("");
  const [year, setYear] = useState("");
  const [sourcePaperId, setSourcePaperId] = useState("");
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [progress, setProgress] = useState(0);

  const isAudio =
    file?.type.startsWith("audio/") || file?.name.match(/\.(mp3|wav|m4a)$/i);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setProgress(10);
    const formData = new FormData();
    formData.append("file", file);
    if (title) formData.append("title", title);

    if (isAudio) {
      if (sourcePaperId) formData.append("source_paper_id", sourcePaperId);
    } else {
      if (authors) formData.append("authors", authors);
      if (year) formData.append("year", year);
    }

    try {
      setProgress(40);
      const endpoint = isAudio ? "/ingest/audio" : "/ingest/pdf";
      const res = await fetch(`http://localhost:8054${endpoint}`, {
        method: "POST",
        body: formData,
      });
      setProgress(80);
      const data = await res.json();
      setResult(data);
      setProgress(100);
    } catch (error) {
      console.error("Upload failed", error);
      setResult({ error: "Failed to upload" });
    } finally {
      setUploading(false);
      setTimeout(() => setProgress(0), 2000);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8 text-center">
        <h2 className="text-3xl font-bold bg-gradient-to-r from-blue-900 to-indigo-900 bg-clip-text text-transparent mb-2">
          Ingest Content
        </h2>
        <p className="text-gray-600">
          Upload PDFs and audio files to build your knowledge graph
        </p>
      </div>

      <div className="bg-white rounded-2xl shadow-lg p-8 border border-gray-100">
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
              className={`flex flex-col items-center justify-center p-8 rounded-xl border-2 border-dashed transition-all cursor-pointer ${
                file
                  ? "bg-blue-50 border-blue-300"
                  : "border-gray-300 hover:border-blue-300 hover:bg-blue-50"
              }`}
            >
              <div className="text-4xl mb-3">
                {file ? (isAudio ? "🎵" : "📄") : "📁"}
              </div>
              {file ? (
                <div className="text-center">
                  <p className="font-semibold text-gray-900">{file.name}</p>
                  <p className="text-sm text-gray-600 mt-1">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                  <p className="text-xs text-blue-600 mt-2 font-medium">
                    Click to change file
                  </p>
                </div>
              ) : (
                <div className="text-center">
                  <p className="font-semibold text-gray-900 mb-1">
                    Drag & drop your file here
                  </p>
                  <p className="text-sm text-gray-600">
                    or click to select a PDF or audio file
                  </p>
                </div>
              )}
            </label>
          </div>

          {/* Title Input */}
          <div>
            <label className="block text-sm font-semibold text-gray-900 mb-2">
              Title (Optional)
            </label>
            <input
              type="text"
              placeholder="Auto-extracted from PDF or enter manually"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
            />
          </div>

          {/* Conditional Fields */}
          {file && !isAudio && (
            <>
              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-2">
                  Authors (Optional)
                </label>
                <input
                  type="text"
                  placeholder="Comma separated list of authors"
                  value={authors}
                  onChange={(e) => setAuthors(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-2">
                  Publication Year (Optional)
                </label>
                <input
                  type="number"
                  placeholder="e.g., 2024"
                  value={year}
                  onChange={(e) => setYear(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                />
              </div>
            </>
          )}

          {file && isAudio && (
            <div>
              <label className="block text-sm font-semibold text-gray-900 mb-2">
                Source Paper ID (Optional)
              </label>
              <input
                type="text"
                placeholder="Link this audio to a paper"
                value={sourcePaperId}
                onChange={(e) => setSourcePaperId(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
              />
            </div>
          )}

          {/* Progress Bar */}
          {uploading && progress > 0 && (
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700">
                  Processing
                </span>
                <span className="text-sm font-semibold text-blue-600">
                  {progress}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-blue-600 to-indigo-600 h-3 rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
            </div>
          )}

          {/* Submit Button */}
          <button
            disabled={!file || uploading}
            type="submit"
            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold py-3 rounded-lg hover:shadow-lg hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105"
          >
            {uploading ? "⏳ Processing..." : "📤 Upload & Ingest"}
          </button>
        </form>

        {/* Result Display */}
        {result && (
          <div
            className={`mt-6 p-4 rounded-lg border-l-4 ${
              result.error
                ? "bg-red-50 border-red-500"
                : "bg-green-50 border-green-500"
            }`}
          >
            <h3
              className={`font-semibold mb-2 ${
                result.error ? "text-red-900" : "text-green-900"
              }`}
            >
              {result.error ? "❌ Error" : "✅ Success"}
            </h3>
            <div
              className={`text-sm overflow-auto max-h-64 ${
                result.error ? "text-red-700" : "text-green-700"
              }`}
            >
              <pre className="whitespace-pre-wrap font-mono">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
