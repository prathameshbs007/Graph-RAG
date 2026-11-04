import type { Source } from "../types";

const retrieverStyle: Record<string, string> = {
  bm25: "bg-amber-100 text-amber-800",
  dense: "bg-sky-100 text-sky-800",
  graph: "bg-emerald-100 text-emerald-800",
};

export const SourceChip = ({ source }: { source: Source }) => {
  const isAudio = source.modality === "audio";
  const found = [...source.found_by];
  if (source.via === "graph" && !found.includes("graph")) found.push("graph");

  return (
    <div
      className={`flex flex-col p-4 bg-gradient-to-br from-blue-50 to-indigo-50 border rounded-lg hover:shadow-md transition-all duration-200 ${
        source.cited ? "border-indigo-400" : "border-blue-200"
      }`}
    >
      <div className="flex items-center justify-between mb-2 gap-2">
        <span
          className={`flex items-center gap-1 ${isAudio ? "bg-purple-100 text-purple-700" : "bg-blue-100 text-blue-700"} text-xs font-bold px-2.5 py-1 rounded-full`}
        >
          {isAudio ? "🎵" : "📄"} [{source.evidence_id}] {isAudio ? "Audio" : "Paper"}
        </span>
        <span className="text-xs font-semibold text-indigo-600 bg-white px-2.5 py-1 rounded">
          Relevance: {(source.score * 100).toFixed(0)}%
        </span>
      </div>

      <h5 className="font-semibold text-gray-900 leading-snug my-1.5 text-sm">
        {source.paper_title}
      </h5>
      {!isAudio && source.authors.length > 0 && (
        <p className="text-xs text-gray-600 font-medium">
          {source.authors.join(", ")} • {source.year ?? "n.d."}
        </p>
      )}

      {/* Where exactly the evidence comes from: page + section, or a timestamp range */}
      <p className="text-xs text-gray-600 mt-1">
        {isAudio ? "🕒 " : "📍 "}
        {source.location}
      </p>

      <div className="flex flex-wrap gap-1.5 mt-2">
        {found.map((f) => (
          <span
            key={f}
            className={`text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded ${retrieverStyle[f] ?? "bg-gray-100 text-gray-700"}`}
            title={`Found by ${f}`}
          >
            {f}
          </span>
        ))}
        {source.cited && (
          <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-indigo-600 text-white">
            cited in answer
          </span>
        )}
      </div>

      <p className="text-xs text-gray-700 mt-2.5 p-2.5 bg-white rounded border-l-4 border-blue-400 italic">
        "{source.chunk_text.substring(0, 160)}
        {source.chunk_text.length > 160 ? "..." : ""}"
      </p>
    </div>
  );
};
