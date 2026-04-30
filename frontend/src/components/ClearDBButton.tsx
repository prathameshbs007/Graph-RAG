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
          className="px-3 py-2 rounded-lg font-medium text-sm text-red-600 hover:bg-red-50 transition-all duration-200 border border-red-200 hover:border-red-300"
          title="Clear all database contents"
        >
          🗑️ Clear DB
        </button>
      ) : (
        <div className="absolute right-0 top-full mt-2 bg-white border border-red-200 rounded-lg shadow-xl p-4 w-64 z-50">
          <p className="text-sm font-semibold text-gray-900 mb-3">
            Clear Database?
          </p>
          <p className="text-xs text-gray-600 mb-4">
            This will delete all documents, audio files, and graphs. This action
            cannot be undone.
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setShowConfirm(false)}
              className="flex-1 px-3 py-2 rounded-lg text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleClearDB}
              disabled={loading}
              className="flex-1 px-3 py-2 rounded-lg text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? "Clearing..." : "Confirm"}
            </button>
          </div>
          {result?.success && (
            <div className="mt-3 p-2 bg-green-50 border border-green-200 rounded text-xs text-green-700 font-medium">
              ✓ Database cleared successfully
            </div>
          )}
          {result?.error && (
            <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700 font-medium">
              ✗ {result.error}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
