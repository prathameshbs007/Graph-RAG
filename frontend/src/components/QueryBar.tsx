import React, { useState } from "react";
import { Search } from "lucide-react";

export const QueryBar = ({
  onSearch,
  loading,
}: {
  onSearch: (txt: string) => void;
  loading: boolean;
}) => {
  const [text, setText] = useState("");
  const [isFocused, setIsFocused] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim() && !loading) {
      onSearch(text);
    }
  };

  const suggestions = [
    { query: "What are the main concepts?", icon: "🎯" },
    { query: "Show relationships between topics", icon: "🔗" },
    { query: "Summarize key findings", icon: "📋" },
  ];

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-3xl space-y-6">
      {/* Main Search Input */}
      <div className="relative group">
        {/* Glow effect */}
        <div
          className={`absolute -inset-1 bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-600 rounded-2xl blur-xl opacity-0 transition-all duration-500 ${
            isFocused ? "opacity-75" : "opacity-0"
          } group-hover:opacity-50`}
        ></div>

        {/* Search Container */}
        <div className="relative glass-dark border border-white/20 rounded-2xl overflow-hidden transition-all duration-300">
          <div className="flex items-center px-6 py-4 gap-3">
            {/* Search Icon */}
            <Search className="w-5 h-5 text-cyan-400 flex-shrink-0" />

            {/* Input */}
            <input
              type="text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder="Ask anything about your documents..."
              className="flex-1 outline-none bg-transparent text-white placeholder-gray-500 text-lg font-medium"
              disabled={loading}
            />

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || !text.trim()}
              className="flex items-center gap-2 px-6 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl hover:shadow-lg hover:shadow-blue-500/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 relative overflow-hidden group btn-glow"
            >
              {loading ? (
                <>
                  <svg
                    className="animate-spin h-5 w-5"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  Searching
                </>
              ) : (
                <>
                  <Search className="w-5 h-5" />
                  Search
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Quick Suggestions */}
      {!text && (
        <div className="space-y-3">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest pl-2">
            Quick Suggestions:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {suggestions.map((item, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setText(item.query)}
                className="glass-dark border border-white/10 rounded-xl p-3 text-left hover:border-cyan-400/50 hover:bg-cyan-400/5 transition-all duration-200 group text-sm font-medium text-gray-300 hover:text-white"
              >
                <span className="text-lg mb-2 block group-hover:scale-110 transition-transform">
                  {item.icon}
                </span>
                {item.query}
              </button>
            ))}
          </div>
        </div>
      )}
    </form>
  );
};
