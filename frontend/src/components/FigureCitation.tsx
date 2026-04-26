import React from 'react';

export const FigureCitation = ({ figure }: { figure: any }) => {
    const imgUrl = `http://localhost:8054${figure.url}`;

    return (
        <div className="border bg-white rounded-lg overflow-hidden flex flex-col shadow-sm max-w-sm">
            <div className="bg-gray-100 h-48 w-full flex items-center justify-center overflow-hidden">
                <img
                    src={imgUrl}
                    alt={figure.caption}
                    className="max-h-full object-contain cursor-pointer transition-transform hover:scale-105"
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
    );
};
