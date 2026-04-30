import { SourceChip } from "./SourceChip";
import { FigureCitation } from "./FigureCitation";

export const AnswerCard = ({ data }: { data: any }) => {
  if (!data) return null;

  return (
    <div className="w-full bg-gradient-to-br from-white via-blue-50 to-white border border-gray-200 rounded-2xl p-8 shadow-lg">
      {/* Header */}
      <div className="mb-8 pb-6 border-b-2 border-gradient-to-r from-blue-200 to-indigo-200">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-2xl">💡</span>
          <h3 className="text-2xl font-bold bg-gradient-to-r from-blue-900 to-indigo-900 bg-clip-text text-transparent">
            Research Answer
          </h3>
        </div>
        <p className="text-sm text-gray-600">
          Evidence-based insights from your knowledge graph
        </p>
      </div>

      {/* Answer Section */}
      <div className="mb-10 p-6 bg-white rounded-xl border border-blue-100">
        <p className="text-gray-800 text-base leading-relaxed whitespace-pre-wrap font-medium">
          {data.answer}
        </p>
      </div>

      {/* Sources and Figures Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Sources Section */}
        <div className="bg-white rounded-xl p-6 border border-gray-200 hover:shadow-md transition-shadow">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-xl">📚</span>
            <h4 className="font-bold text-gray-900 uppercase tracking-wider text-sm">
              Cited Sources
            </h4>
            {data.sources?.length > 0 && (
              <span className="ml-auto bg-blue-100 text-blue-800 text-xs font-bold px-2.5 py-0.5 rounded-full">
                {data.sources.length}
              </span>
            )}
          </div>
          <div className="flex flex-col gap-3">
            {data.sources?.length > 0 ? (
              data.sources.map((s: any, idx: number) => (
                <SourceChip key={idx} index={idx + 1} source={s} />
              ))
            ) : (
              <p className="text-gray-400 italic text-center py-4">
                No sources available
              </p>
            )}
          </div>
        </div>

        {/* Figures Section */}
        <div className="bg-white rounded-xl p-6 border border-gray-200 hover:shadow-md transition-shadow">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-xl">🖼️</span>
            <h4 className="font-bold text-gray-900 uppercase tracking-wider text-sm">
              Visual Evidence
            </h4>
            {data.figures?.length > 0 && (
              <span className="ml-auto bg-indigo-100 text-indigo-800 text-xs font-bold px-2.5 py-0.5 rounded-full">
                {data.figures.length}
              </span>
            )}
          </div>
          <div className="flex flex-col gap-4">
            {data.figures?.length > 0 ? (
              data.figures.map((f: any, idx: number) => (
                <FigureCitation key={idx} figure={f} />
              ))
            ) : (
              <p className="text-gray-400 italic text-center py-4">
                No visual evidence retrieved
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-6 border-t border-gray-200">
        <p className="text-xs text-gray-500 text-center">
          ✓ Answer generated from knowledge graph • {data.sources?.length || 0}{" "}
          sources • {data.figures?.length || 0} figures
        </p>
      </div>
    </div>
  );
};
