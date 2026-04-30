import { SourceChip } from "./SourceChip";
import { FigureCitation } from "./FigureCitation";

export const AnswerCard = ({ data }: { data: any }) => {
  if (!data) return null;

  return (
    <div className="w-full glass-dark border border-white/10 rounded-3xl p-8 shadow-2xl shadow-blue-500/20">
      {/* Header */}
      <div className="mb-8 pb-6 border-b border-white/10">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-3xl">✨</span>
          <h3 className="text-3xl font-black text-gradient">Answer</h3>
          <div className="ml-auto">
            <span className="inline-block text-xs font-bold bg-cyan-400/20 text-cyan-300 px-3 py-1 rounded-full border border-cyan-400/30">
              Evidence-Based
            </span>
          </div>
        </div>
      </div>

      {/* Answer Section */}
      <div className="mb-10 p-8 bg-gradient-to-br from-white/10 to-white/5 rounded-2xl border border-white/10 backdrop-blur">
        <p className="text-white text-lg leading-relaxed whitespace-pre-wrap font-medium">
          {data.answer}
        </p>
      </div>

      {/* Sources and Figures Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sources Section */}
        <div className="glass-dark border border-white/10 rounded-2xl p-6 card-hover overflow-hidden group">
          {/* Background glow */}
          <div className="absolute inset-0 opacity-0 group-hover:opacity-20 bg-gradient-to-br from-blue-600 to-cyan-600 transition-opacity duration-300"></div>
          
          <div className="relative z-10">
            <div className="flex items-center gap-3 mb-5">
              <span className="text-2xl">📚</span>
              <h4 className="font-black text-white uppercase tracking-widest text-sm">
                Cited Sources
              </h4>
              {data.sources?.length > 0 && (
                <span className="ml-auto bg-blue-500/30 text-blue-200 text-xs font-bold px-3 py-1.5 rounded-full border border-blue-500/50">
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
                <p className="text-gray-400 italic text-center py-6">
                  No sources available
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Figures Section */}
        <div className="glass-dark border border-white/10 rounded-2xl p-6 card-hover overflow-hidden group">
          {/* Background glow */}
          <div className="absolute inset-0 opacity-0 group-hover:opacity-20 bg-gradient-to-br from-purple-600 to-pink-600 transition-opacity duration-300"></div>
          
          <div className="relative z-10">
            <div className="flex items-center gap-3 mb-5">
              <span className="text-2xl">🖼️</span>
              <h4 className="font-black text-white uppercase tracking-widest text-sm">
                Visual Evidence
              </h4>
              {data.figures?.length > 0 && (
                <span className="ml-auto bg-purple-500/30 text-purple-200 text-xs font-bold px-3 py-1.5 rounded-full border border-purple-500/50">
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
                <p className="text-gray-400 italic text-center py-6">
                  No visual evidence retrieved
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 pt-6 border-t border-white/10">
        <div className="flex items-center justify-between text-xs text-gray-400 font-semibold">
          <div className="flex items-center gap-2">
            <span>✓</span>
            <span>Generated from knowledge graph</span>
          </div>
          <div className="flex gap-4">
            <span>{data.sources?.length || 0} sources</span>
            <span className="text-white/30">•</span>
            <span>{data.figures?.length || 0} figures</span>
          </div>
        </div>
      </div>
    </div>
  );
};
