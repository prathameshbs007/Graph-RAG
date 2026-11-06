import { useState } from "react";
import { API } from "../api";
import type { FigureRef } from "../types";

export const FigureCitation = ({ figure }: { figure: FigureRef }) => {
  const [isOpen, setIsOpen] = useState(false);
  const imgUrl = `${API}${figure.url}`;

  return (
    <>
      <div className="p-3.5 rounded-xl bg-surface-container/60 hover:bg-surface-container transition-all border border-surface-container-highest/50 flex flex-col group">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-1.5 py-0.5 rounded bg-surface-container-high text-on-surface font-mono text-xs font-semibold">
                {figure.evidence_id}
              </span>
              <span className="text-xs font-semibold text-on-surface line-clamp-1" title={figure.paper_title}>
                {figure.paper_title}
              </span>
            </div>
            <div className="font-mono text-[11px] text-outline mt-0.5">
              Page {figure.page}
            </div>
          </div>
          <span className="px-2 py-0.5 rounded bg-secondary/15 text-secondary font-mono text-xs shrink-0 font-medium">
            {(figure.score * 100).toFixed(0)}%
          </span>
        </div>

        {/* Thumbnail Preview with Click-to-Zoom */}
        <div
          className="w-full bg-surface-container-lowest rounded-lg p-2 my-1.5 overflow-hidden flex items-center justify-center cursor-pointer group-hover:border-primary/40 border border-transparent transition-all h-40 relative"
          onClick={() => setIsOpen(true)}
        >
          <img
            src={imgUrl}
            alt={figure.caption}
            className="max-h-full max-w-full object-contain transition-transform group-hover:scale-105"
          />
          <div className="absolute inset-0 bg-surface/0 group-hover:bg-surface/30 transition-colors flex items-center justify-center">
            <span className="opacity-0 group-hover:opacity-100 transition-opacity px-2 py-1 rounded bg-surface-container-high text-xs font-mono text-on-surface shadow-md flex items-center gap-1">
              <span className="material-symbols-outlined text-[0.875rem]">zoom_in</span> Zoom
            </span>
          </div>
        </div>

        {figure.caption && (
          <p className="text-xs text-on-surface-variant line-clamp-2 leading-relaxed italic mt-1" title={figure.caption}>
            {figure.caption}
          </p>
        )}

        {figure.cited && (
          <div className="mt-2 flex items-center">
            <span className="px-1.5 py-0.5 rounded bg-secondary text-on-secondary text-[10px] uppercase font-bold">
              cited in answer
            </span>
          </div>
        )}
      </div>

      {/* Modal Zoom View */}
      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4 cursor-zoom-out"
          onClick={() => setIsOpen(false)}
        >
          <div className="relative max-w-[90vw] max-h-[90vh] flex flex-col bg-surface-container-low border border-surface-container-highest p-4 rounded-2xl shadow-2xl">
            <button
              className="absolute -top-3 -right-3 bg-surface-container-high text-on-surface hover:text-error w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm shadow-lg border border-surface-container-highest transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                setIsOpen(false);
              }}
              title="Close"
            >
              ✕
            </button>
            <div className="w-full max-h-[70vh] flex items-center justify-center overflow-hidden bg-surface-container-lowest rounded-lg p-2">
              <img
                src={imgUrl}
                className="max-h-[68vh] max-w-full object-contain"
                alt="Full resolution figure"
                onClick={(e) => e.stopPropagation()}
              />
            </div>
            <div className="mt-3 text-left">
              <p className="font-semibold text-on-surface text-sm mb-1">{figure.paper_title}</p>
              <p className="text-xs text-on-surface-variant leading-relaxed">{figure.caption}</p>
              {figure.description && (
                <p className="text-xs text-outline mt-1.5 font-mono">{figure.description}</p>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};
