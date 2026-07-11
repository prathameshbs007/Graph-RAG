import { useEffect, useState } from 'react';
import { assetUrl } from '../lib/api';
import type { FigureReference } from '../types';

export const FigureCitation = ({ figure }: { figure: FigureReference }) => {
    const [isOpen, setIsOpen] = useState(false);
    const imgUrl = assetUrl(figure.url);

    useEffect(() => {
        if (!isOpen) return;
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') setIsOpen(false);
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isOpen]);

    return (
        <>
            <div className="group border border-border-default bg-surface-raised rounded-lg overflow-hidden flex flex-col shadow-xs hover:shadow-md transition-shadow duration-150 max-w-sm">
                <button
                    type="button"
                    onClick={() => setIsOpen(true)}
                    className="aspect-video w-full bg-surface-hover flex items-center justify-center overflow-hidden cursor-zoom-in focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-inset"
                >
                    <img
                        src={imgUrl}
                        alt={figure.caption}
                        className="max-h-full max-w-full object-contain transition-transform duration-200 group-hover:scale-105"
                        onError={(e) => (e.currentTarget.style.display = 'none')}
                    />
                </button>
                <div className="p-3 border-t border-border-default">
                    <p className="font-medium text-sm text-text-default truncate" title={figure.paper_title}>{figure.paper_title}</p>
                    <p className="text-xs text-text-muted mt-1 line-clamp-2" title={figure.caption}>{figure.caption}</p>
                    <div className="flex justify-between items-center mt-2">
                        <span className="text-xs font-mono bg-accent-50 dark:bg-accent-950 text-accent-700 dark:text-accent-300 px-1.5 py-0.5 rounded">Pg {figure.page}</span>
                    </div>
                </div>
            </div>

            {isOpen && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-950/80 backdrop-blur-md p-4 cursor-zoom-out animate-fade-in"
                    onClick={() => setIsOpen(false)}
                    role="dialog"
                    aria-modal="true"
                    aria-label={figure.caption}
                >
                    <div
                        className="relative max-w-[90vw] max-h-[85vh] flex flex-col items-center cursor-default"
                        onClick={e => e.stopPropagation()}
                    >
                        <button
                            type="button"
                            className="absolute -top-3 -right-3 bg-surface-raised text-text-default w-8 h-8 rounded-full flex items-center justify-center font-bold text-lg shadow-lg border border-border-default hover:bg-surface-hover transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500"
                            onClick={() => setIsOpen(false)}
                            aria-label="Close"
                        >
                            &times;
                        </button>
                        <img
                            src={imgUrl}
                            className="max-w-full max-h-[75vh] object-contain bg-surface-raised rounded shadow-2xl"
                            alt={figure.caption}
                        />
                        <p className="text-neutral-100 text-sm mt-3 text-center max-w-lg">{figure.caption}</p>
                    </div>
                </div>
            )}
        </>
    );
};
