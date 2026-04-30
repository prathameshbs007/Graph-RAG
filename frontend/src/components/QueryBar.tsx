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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim() && !loading) {
      onSearch(text);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl">
      <div className="relative group">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full blur opacity-75 group-hover:opacity-100 transition duration-300"></div>
        <div className="relative flex items-center bg-white rounded-full shadow-xl overflow-hidden border border-gray-200">
          <Search className="text-gray-400 w-5 h-5 ml-6 mr-2 flex-shrink-0" />
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Ask about your documents, concepts, relationships..."
            className="flex-1 outline-none py-4 px-3 text-base bg-transparent text-gray-800 placeholder:text-gray-500"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !text.trim()}
            className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-full px-8 py-4 mr-1 hover:shadow-lg hover:from-blue-700 hover:to-indigo-700 font-semibold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none flex items-center gap-2"
          >
            {loading ? (
              <>
                <svg
                  className="animate-spin h-4 w-4"
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
                Searching...
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                Search
              </>
            )}
          </button>
        </div>
      </div>

      {/* Quick suggestion pills */}
      <div className="mt-4 flex flex-wrap gap-2 justify-center">
        <div className="text-xs text-gray-500 font-medium w-full text-center mb-1">
          Try asking:
        </div>
        <button
          type="button"
          onClick={() => setText("What are the main concepts?")}
          className="text-xs bg-white hover:bg-blue-50 border border-gray-300 rounded-full px-3 py-1.5 text-gray-700 transition-colors"
        >
          Main concepts
        </button>
        <button
          type="button"
          onClick={() => setText("Show me relationships between topics")}
          className="text-xs bg-white hover:bg-blue-50 border border-gray-300 rounded-full px-3 py-1.5 text-gray-700 transition-colors"
        >
          Relationships
        </button>
        <button
          type="button"
          onClick={() => setText("Summarize the key findings")}
          className="text-xs bg-white hover:bg-blue-50 border border-gray-300 rounded-full px-3 py-1.5 text-gray-700 transition-colors"
        >
          Summarize
        </button>
      </div>
    </form>
  );
};
