import { useState } from "react";
import { API } from "../api";
import type { FigureRef } from "../types";

export const FigureCitation = ({ figure }: { figure: FigureRef }) => {
  const [isOpen, setIsOpen] = useState(false);
  const imgUrl = `${API}${figure.url}`;

  return (
    <>
      <div className="bg-white rounded-lg overflow-hidden flex flex-col shadow-md hover:shadow-lg transition-all duration-200 border border-gray-200 hover:border-indigo-300 max-w-sm">
        {/* The stored crop: the figure plus its caption, cut from the page by bounding box */}
        <div
          className="bg-gradient-to-br from-gray-100 to-gray-200 h-44 w-full flex items-center justify-center overflow-hidden cursor-zoom-in relative group"
          onClick={() => setIsOpen(true)}
        >
          <img
            src={imgUrl}
            alt={figure.caption}
            className="max-h-full max-w-full object-contain transition-transform group-hover:scale-105"
          />
          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors flex items-center justify-center">
            <span className="opacity-0 group-hover:opacity-100 transition-opacity text-white text-sm font-semibold">
              🔍 View Full
            </span>
          </div>
        </div>

        <div className="p-4 bg-gradient-to-br from-white to-blue-50 border-t border-gray-200">
          <p className="font-semibold text-sm text-gray-900 truncate" title={figure.paper_title}>
            {figure.paper_title}
          </p>
          <p className="text-xs text-gray-600 mt-2 line-clamp-3 leading-relaxed italic" title={figure.caption}>
            {figure.caption}
          </p>
          <div className="flex flex-wrap gap-2 items-center mt-3">
            <span className="text-xs font-bold bg-blue-100 text-blue-700 px-2.5 py-1 rounded-full">
              [{figure.evidence_id}]
            </span>
            <span className="text-xs font-bold bg-amber-100 text-amber-700 px-2.5 py-1 rounded-full">
              📄 Page {figure.page}
            </span>
            <span className="text-xs text-gray-500">Relevance {(figure.score * 100).toFixed(0)}%</span>
            {figure.cited && (
              <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-indigo-600 text-white">
                cited in answer
              </span>
            )}
          </div>
        </div>
      </div>

      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-md p-4 cursor-zoom-out"
          onClick={() => setIsOpen(false)}
        >
          <div className="relative max-w-[90vw] max-h-[90vh] flex flex-col">
            <button
              className="absolute -top-10 right-0 bg-white text-black w-10 h-10 rounded-full flex items-center justify-center font-bold text-xl shadow-lg hover:bg-gray-200 transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                setIsOpen(false);
              }}
              title="Close"
            >
              ✕
            </button>
            <img
              src={imgUrl}
              className="w-full h-full object-contain bg-white rounded shadow-2xl max-h-[70vh]"
              alt="Full resolution view"
              onClick={(e) => e.stopPropagation()}
            />
            <div className="mt-4 bg-white rounded-lg p-4 shadow-lg max-w-2xl">
              <p className="font-semibold text-gray-900 mb-2">{figure.paper_title}</p>
              <p className="text-sm text-gray-700">{figure.caption}</p>
              {figure.description && (
                <p className="text-sm text-gray-500 mt-2 italic">{figure.description}</p>
              )}
              <span className="inline-block mt-3 text-xs font-bold bg-amber-100 text-amber-700 px-2.5 py-1 rounded-full">
                Page {figure.page}
              </span>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
