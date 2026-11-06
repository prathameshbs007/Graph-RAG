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
    <div className="relative">
      {!showConfirm ? (
        <button
          onClick={() => setShowConfirm(true)}
          type="button"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-error-container/20 text-error hover:bg-error-container/40 hover:text-on-error-container transition-all text-xs font-mono font-medium border border-error/20"
          title="Clear all database contents"
        >
          <span className="material-symbols-outlined text-[1rem]">delete_forever</span>
          <span className="hidden sm:inline">Clear DB</span>
        </button>
      ) : (
        <div className="absolute right-0 top-full mt-2 bg-surface-container-low/95 border border-error/40 rounded-xl shadow-[0_8px_32px_rgba(0,0,0,0.6)] p-4 w-72 z-50 backdrop-blur-xl">
          {/* Header */}
          <div className="flex items-start gap-2.5 mb-3">
            <span className="material-symbols-outlined text-error text-[1.25rem]">warning</span>
            <div>
              <p className="text-sm font-semibold text-on-surface">Clear All Knowledge Base?</p>
              <p className="text-xs text-on-surface-variant mt-0.5">This action is irreversible</p>
            </div>
          </div>

          {/* Warning Message */}
          <div className="bg-error-container/20 border border-error/30 rounded-lg p-2.5 mb-3">
            <p className="text-xs text-error leading-relaxed">
              Permanently purges all indexed PDF chunks, audio transcripts, figures, and learned graph synapses.
            </p>
          </div>

          {/* Buttons */}
          <div className="flex gap-2">
            <button
              onClick={() => setShowConfirm(false)}
              className="flex-1 px-3 py-1.5 rounded-lg text-xs font-medium text-on-surface-variant bg-surface-container hover:bg-surface-container-high transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleClearDB}
              disabled={loading}
              className="flex-1 px-3 py-1.5 rounded-lg text-xs font-semibold text-on-error bg-error hover:brightness-110 disabled:opacity-50 transition-all flex items-center justify-center gap-1"
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
            <div className="mt-2.5 p-2 bg-secondary/15 border border-secondary/30 rounded-lg text-xs text-secondary font-medium flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[0.875rem]">check_circle</span>
              <span>Database cleared successfully</span>
            </div>
          )}
          {result?.error && (
            <div className="mt-2.5 p-2 bg-error-container/20 border border-error/30 rounded-lg text-xs text-error font-medium flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[0.875rem]">error</span>
              <span>{result.error}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
