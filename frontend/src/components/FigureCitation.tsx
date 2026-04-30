import { useState } from "react";

export const FigureCitation = ({ figure }: { figure: any }) => {
  const [isOpen, setIsOpen] = useState(false);
  const imgUrl = `http://localhost:8054${figure.url}`;

  return (
    <>
      <div className="bg-white rounded-lg overflow-hidden flex flex-col shadow-md hover:shadow-lg transition-all duration-200 border border-gray-200 hover:border-indigo-300 max-w-sm">
        {/* Image Container */}
        <div
          className="bg-gradient-to-br from-gray-100 to-gray-200 h-40 w-full flex items-center justify-center overflow-hidden cursor-zoom-in relative group"
          onClick={() => setIsOpen(true)}
        >
          <img
            src={imgUrl}
            alt={figure.caption}
            className="max-h-full max-w-full object-contain transition-transform group-hover:scale-110"
            onError={(e) => {
              e.currentTarget.style.display = "none";
              const parent = e.currentTarget.parentElement;
              if (parent)
                parent.innerHTML =
                  '<div className="w-full h-full flex items-center justify-center text-gray-400">📷 Image unavailable</div>';
            }}
          />
          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors flex items-center justify-center">
            <div className="opacity-0 group-hover:opacity-100 transition-opacity">
              <span className="text-white text-sm font-semibold">
                🔍 View Full
              </span>
            </div>
          </div>
        </div>

        {/* Info Section */}
        <div className="p-4 bg-gradient-to-br from-white to-blue-50 border-t border-gray-200">
          <p
            className="font-semibold text-sm text-gray-900 truncate"
            title={figure.paper_title}
          >
            {figure.paper_title}
          </p>
          <p
            className="text-xs text-gray-600 mt-2 line-clamp-2 leading-relaxed italic"
            title={figure.caption}
          >
            {figure.caption}
          </p>
          <div className="flex gap-2 items-center mt-3">
            <span className="text-xs font-bold bg-amber-100 text-amber-700 px-2.5 py-1 rounded-full">
              📄 Page {figure.page}
            </span>
            <span className="text-xs text-gray-500">Figure</span>
          </div>
        </div>
      </div>

      {/* Modal */}
      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-md p-4 cursor-zoom-out"
          onClick={() => setIsOpen(false)}
        >
          <div className="relative max-w-[90vw] max-h-[90vh] flex flex-col">
            {/* Close Button */}
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

            {/* Image */}
            <img
              src={imgUrl}
              className="w-full h-full object-contain bg-white rounded shadow-2xl"
              alt="Full Resolution View"
              onClick={(e) => e.stopPropagation()}
            />

            {/* Caption */}
            <div className="mt-4 bg-white rounded-lg p-4 shadow-lg max-w-2xl">
              <p className="font-semibold text-gray-900 mb-2">
                {figure.paper_title}
              </p>
              <p className="text-sm text-gray-700">{figure.caption}</p>
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
