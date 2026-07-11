import ReactMarkdown from 'react-markdown';
import { SourceChip } from './SourceChip';
import { FigureCitation } from './FigureCitation';
import type { QueryResponse } from '../types';

export const AnswerCard = ({ data }: { data: QueryResponse | null }) => {
    if (!data) return null;

    return (
        <div className="animate-fade-in bg-surface-raised border border-border-default rounded-xl p-6 sm:p-8 shadow-sm">
            <div className="text-text-default leading-relaxed mb-8">
                <ReactMarkdown
                    components={{
                        p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
                        ul: ({ children }) => <ul className="list-disc pl-5 mb-3 space-y-1">{children}</ul>,
                        ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 space-y-1">{children}</ol>,
                        strong: ({ children }) => <strong className="font-semibold text-text-default">{children}</strong>,
                        code: ({ children }) => (
                            <code className="font-mono text-sm bg-surface-hover px-1 py-0.5 rounded">{children}</code>
                        ),
                        a: ({ children, href }) => (
                            <a
                                href={href}
                                target="_blank"
                                rel="noreferrer"
                                className="text-accent-600 dark:text-accent-400 underline underline-offset-2 hover:text-accent-700 dark:hover:text-accent-300"
                            >
                                {children}
                            </a>
                        ),
                    }}
                >
                    {data.answer}
                </ReactMarkdown>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                    <h4 className="font-semibold text-text-muted mb-3 uppercase tracking-wider text-xs border-b border-border-default pb-2">Cited Sources</h4>
                    <div className="flex flex-col gap-2">
                        {data.sources?.map((s, idx) => (
                            <SourceChip key={s.chunk_id || idx} index={idx + 1} source={s} />
                        ))}
                        {data.sources?.length === 0 && (
                            <p className="text-text-muted italic text-sm">No sources retrieved for this query.</p>
                        )}
                    </div>
                </div>

                <div>
                    <h4 className="font-semibold text-text-muted mb-3 uppercase tracking-wider text-xs border-b border-border-default pb-2">Visual Evidence</h4>
                    <div className="flex flex-col gap-4">
                        {data.figures?.length > 0 ? (
                            data.figures.map((f, idx) => (
                                <FigureCitation key={f.figure_id || idx} figure={f} />
                            ))
                        ) : (
                            <p className="text-text-muted italic text-sm">No visual evidence retrieved for this query.</p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
