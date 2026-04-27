
import { SourceChip } from './SourceChip';
import { FigureCitation } from './FigureCitation';

export const AnswerCard = ({ data }: { data: any }) => {
    if (!data) return null;

    return (
        <div className="bg-white border rounded-xl p-8 shadow-sm">
            <h3 className="text-xl font-bold mb-4">Research OS Answer</h3>
            <div className="text-gray-800 text-lg leading-relaxed whitespace-pre-wrap mb-8">
                {data.answer}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                    <h4 className="font-semibold text-gray-600 mb-3 uppercase tracking-wider text-sm border-b pb-2">Cited Sources</h4>
                    <div className="flex flex-col gap-3">
                        {data.sources?.map((s: any, idx: number) => (
                            <SourceChip key={idx} index={idx + 1} source={s} />
                        ))}
                    </div>
                </div>

                <div>
                    <h4 className="font-semibold text-gray-600 mb-3 uppercase tracking-wider text-sm border-b pb-2">Visual Evidence</h4>
                    <div className="flex flex-col gap-4">
                        {data.figures?.length > 0 ? (
                            data.figures.map((f: any, idx: number) => (
                                <FigureCitation key={idx} figure={f} />
                            ))
                        ) : (
                            <p className="text-gray-400 italic">No visual evidence retrieved for this query.</p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
