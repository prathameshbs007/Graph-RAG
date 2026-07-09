import { useState } from 'react';
import { assetUrl } from '../lib/api';
import type { FigureReference } from '../types';

export const FigureCitation = ({ figure }: { figure: FigureReference }) => {
    const [isOpen, setIsOpen] = useState(false);
    const imgUrl = assetUrl(figure.url);

    return (
        <>
            <div className="border bg-white rounded-lg overflow-hidden flex flex-col shadow-sm max-w-sm">
                <div
                    className="bg-gray-100 h-48 w-full flex items-center justify-center overflow-hidden cursor-zoom-in"
                    onClick={() => setIsOpen(true)}
                >
                    <img
                        src={imgUrl}
                        alt={figure.caption}
                        className="max-h-full object-contain transition-transform hover:scale-105"
                        onError={(e) => (e.currentTarget.style.display = 'none')}
                    />
                </div>
                <div className="p-3 bg-gray-50 border-t">
                    <p className="font-semibold text-sm text-gray-800 truncate" title={figure.paper_title}>{figure.paper_title}</p>
                    <p className="text-xs text-gray-500 mt-1 line-clamp-2" title={figure.caption}>{figure.caption}</p>
                    <div className="flex justify-between items-center mt-2">
                        <span className="text-xs font-mono bg-amber-100 text-amber-800 px-2 py-0.5 rounded">Pg {figure.page}</span>
                    </div>
                </div>
            </div>

            {isOpen && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 cursor-zoom-out"
                    onClick={() => setIsOpen(false)}
                >
                    <div className="relative max-w-[95vw] max-h-[95vh] flex flex-col">
                        <button
                            className="absolute -top-4 -right-4 bg-white text-black w-8 h-8 rounded-full flex items-center justify-center font-bold text-xl shadow-lg border-2 border-gray-300"
                            onClick={(e) => { e.stopPropagation(); setIsOpen(false); }}
                        >
                            &times;
                        </button>
                        <img
                            src={imgUrl}
                            className="w-full h-full object-contain bg-white rounded shadow-2xl"
                            alt="Full Resolution View"
                        />
                    </div>
                </div>
            )}
        </>
    );
};
