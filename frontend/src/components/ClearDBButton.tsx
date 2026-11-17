import { useState } from "react";
import { API } from "../api";

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
      const res = await fetch(`${API}/admin/clear-db`, {
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
    } catch {
      setResult({ error: "Connection error. Make sure backend is running." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button
        onClick={() => setShowConfirm(true)}
        type="button"
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-error-container/20 text-error hover:bg-error-container/40 hover:text-on-error-container transition-all text-xs font-mono font-medium border border-error/30 cursor-pointer"
        title="Clear all database contents"
      >
        <span className="material-symbols-outlined text-[1rem]">delete_forever</span>
        <span className="hidden sm:inline">Clear DB</span>
      </button>

      {showConfirm && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-fadeIn">
          {/* Backdrop dismissal */}
          <div
            className="absolute inset-0 cursor-pointer"
            onClick={() => !loading && setShowConfirm(false)}
          />

          {/* Modal Dialog Card */}
          <div className="relative bg-[#131b2e] border border-error/40 rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.85)] p-6 w-full max-w-sm z-10 text-on-surface">
            {/* Header */}
            <div className="flex items-start gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-error-container/30 border border-error/40 flex items-center justify-center text-error shrink-0 shadow-inner">
                <span className="material-symbols-outlined text-[1.5rem]">warning</span>
              </div>
              <div>
                <p className="text-base font-semibold text-on-surface tracking-tight">Clear Knowledge Base?</p>
                <p className="text-xs text-on-surface-variant mt-0.5">This action is irreversible</p>
              </div>
            </div>

            {/* Warning Message */}
            <div className="bg-error-container/20 border border-error/30 rounded-xl p-3.5 mb-5">
              <p className="text-xs text-error/90 leading-relaxed font-sans">
                Permanently purges all indexed PDF chunks, audio transcripts, figures, and learned graph synapses from Weaviate and Neo4j.
              </p>
            </div>

            {/* Buttons */}
            <div className="flex gap-2.5">
              <button
                type="button"
                onClick={() => setShowConfirm(false)}
                disabled={loading}
                className="flex-1 px-4 py-2 rounded-xl text-xs font-medium text-on-surface-variant bg-[#171f33] hover:bg-[#222a3d] border border-surface-container-highest/40 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleClearDB}
                disabled={loading}
                className="flex-1 px-4 py-2 rounded-xl text-xs font-semibold text-on-error bg-error hover:brightness-110 disabled:opacity-50 transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-lg shadow-error/20"
              >
                {loading ? (
                  <>
                    <span className="material-symbols-outlined text-[0.875rem] animate-spin">sync</span>
                    <span>Clearing...</span>
                  </>
                ) : (
                  <span>Confirm</span>
                )}
              </button>
            </div>

            {/* Results */}
            {result?.success && (
              <div className="mt-3 p-2.5 bg-secondary/15 border border-secondary/30 rounded-xl text-xs text-secondary font-medium flex items-center gap-2">
                <span className="material-symbols-outlined text-[1rem]">check_circle</span>
                <span>Database cleared successfully</span>
              </div>
            )}
            {result?.error && (
              <div className="mt-3 p-2.5 bg-error-container/20 border border-error/30 rounded-xl text-xs text-error font-medium flex items-center gap-2">
                <span className="material-symbols-outlined text-[1rem]">error</span>
                <span>{result.error}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
};
