export const SourceChip = ({
  index,
  source,
}: {
  index: number;
  source: any;
}) => {
  const isAudio = source.modality === "audio";

  return (
    <div className="flex flex-col p-4 bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-lg hover:shadow-md hover:border-blue-300 transition-all duration-200">
      <div className="flex items-center justify-between mb-2">
        <span
          className={`flex items-center gap-1 ${isAudio ? "bg-purple-100 text-purple-700" : "bg-blue-100 text-blue-700"} text-xs font-bold px-2.5 py-1 rounded-full`}
        >
          {isAudio ? "🎵" : "📄"} [{index}] {isAudio ? "Audio" : "Paper"}
        </span>
        <span className="text-xs font-semibold text-indigo-600 bg-white px-2.5 py-1 rounded">
          Relevance: {(source.score * 100).toFixed(0)}%
        </span>
      </div>
      <h5 className="font-semibold text-gray-900 leading-snug my-1.5 text-sm">
        {source.paper_title || source.title}
      </h5>
      {!isAudio && source.authors?.length > 0 && (
        <p className="text-xs text-gray-600 font-medium">
          {source.authors.join(", ")} • {source.year || "n.d."}
        </p>
      )}
      <p className="text-xs text-gray-700 mt-2.5 p-2.5 bg-white rounded border-l-3 border-blue-400 italic">
        "{source.chunk_text.substring(0, 100)}
        {source.chunk_text.length > 100 ? "..." : ""}"
      </p>
    </div>
  );
};
