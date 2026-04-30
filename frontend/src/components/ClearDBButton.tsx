import { useState } from "react";

export const ClearDBButton = () => {
  const [loading, setLoading] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [result, setResult] = useState<{
    success?: boolean;
    error?: string;
  } | null>(null);

  const handleClearDB = async () => {
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch("http://localhost:8054/admin/clear-db", {
        method: "POST",
      });
      const data = await res.json();
      if (res.ok) {
        setResult({ success: true });
        setShowConfirm(false);
        setTimeout(() => setResult(null), 3000);
      } else {
        setResult({ error: data.detail || "Failed to clear database" });
      }
    } catch (error) {
      setResult({ error: "Connection error. Make sure backend is running." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative">
      {!showConfirm ? (
        <button
          onClick={() => setShowConfirm(true)}
          className="group relative px-4 py-2.5 rounded-xl font-semibold text-sm text-red-400 border border-red-500/30 hover:border-red-500/60 hover:bg-red-500/5 transition-all duration-200 overflow-hidden"
          title="Clear all database contents"
        >
          <span className="relative z-10 flex items-center gap-2">
            🗑️ <span className="hidden sm:inline">Clear DB</span>
          </span>
          <div className="absolute inset-0 bg-gradient-to-r from-red-600/0 via-red-600/10 to-red-600/0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
        </button>
      ) : (
        <div className="absolute right-0 top-full mt-3 glass-dark border border-red-500/30 rounded-2xl shadow-2xl shadow-red-500/20 p-6 w-72 z-50 backdrop-blur-xl">
          {/* Header */}
          <div className="flex items-start gap-3 mb-4">
            <span className="text-2xl">⚠️</span>
            <div>
              <p className="text-lg font-bold text-white">Clear All Data?</p>
              <p className="text-xs text-gray-400 mt-1">This cannot be undone</p>
            </div>
          </div>

          {/* Warning Message */}
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 mb-4">
            <p className="text-xs text-red-300 leading-relaxed">
              This will permanently delete all documents, audio files, papers, and graphs from the knowledge base.
            </p>
          </div>

          {/* Buttons */}
          <div className="flex gap-2">
            <button
              onClick={() => setShowConfirm(false)}
              className="flex-1 px-4 py-2 rounded-lg text-sm font-semibold text-gray-300 bg-white/5 hover:bg-white/10 border border-white/10 transition-all duration-200"
            >
              Cancel
            </button>
            <button
              onClick={handleClearDB}
              disabled={loading}
              className="flex-1 px-4 py-2 rounded-lg text-sm font-semibold text-white bg-gradient-to-r from-red-600 to-red-700 hover:shadow-lg hover:shadow-red-500/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Clearing
                </>
              ) : (
                <>Confirm</>
              )}
            </button>
          </div>

          {/* Results */}
          {result?.success && (
            <div className="mt-4 p-3 bg-green-500/10 border border-green-500/30 rounded-lg text-xs text-green-300 font-semibold flex items-center gap-2">
              <span>✓</span>
              Database cleared successfully
            </div>
          )}
          {result?.error && (
            <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-xs text-red-300 font-semibold flex items-center gap-2">
              <span>✗</span>
              {result.error}
            </div>
          )}
        </div>
      )}
    </div>
  );
};;
