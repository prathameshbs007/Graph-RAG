import { FileText, Headphones } from 'lucide-react';
import type { SourceChunk } from '../types';

function formatTimestamp(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function ScoreRing({ score }: { score: number }) {
    const pct = Math.max(0, Math.min(score, 1));
    const radius = 8;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference * (1 - pct);
    return (
        <svg width="20" height="20" viewBox="0 0 20 20" className="shrink-0" role="img" aria-label={`Relevance score ${score.toFixed(2)}`}>
            <circle cx="10" cy="10" r={radius} fill="none" strokeWidth="2.5" className="stroke-neutral-200 dark:stroke-neutral-700" />
            <circle
                cx="10"
                cy="10"
                r={radius}
                fill="none"
                strokeWidth="2.5"
                strokeDasharray={circumference}
                strokeDashoffset={offset}
                strokeLinecap="round"
                transform="rotate(-90 10 10)"
                className="stroke-accent-500 transition-[stroke-dashoffset] duration-300"
            />
        </svg>
    );
}

export const SourceChip = ({ index, source }: { index: number; source: SourceChunk }) => {
    const isAudio = source.modality === 'audio';
    const Icon = isAudio ? Headphones : FileText;

    return (
        <div className="flex flex-col p-3 bg-surface-hover border border-border-default rounded-lg hover:shadow-sm hover:border-accent-200 dark:hover:border-accent-800 transition-all duration-150">
            <div className="flex items-center justify-between mb-1.5">
                <span className="flex items-center gap-1.5 text-xs font-semibold text-text-muted">
                    <span className="flex items-center justify-center w-5 h-5 rounded-full bg-accent-100 dark:bg-accent-900 text-accent-700 dark:text-accent-300 text-[10px] font-bold shrink-0">
                        {index}
                    </span>
                    <Icon className="w-3.5 h-3.5" />
                    {isAudio ? 'Audio' : 'Paper'}
                </span>
                <ScoreRing score={source.score} />
            </div>
            <h5 className="font-medium text-text-default text-sm leading-snug">{source.paper_title}</h5>
            {!isAudio && source.authors?.length > 0 && (
                <p className="text-xs text-text-muted mt-0.5">{source.authors.join(', ')} ({source.year ?? 'n.d.'})</p>
            )}
            {isAudio && source.start_time != null && source.end_time != null && (
                <span className="w-fit text-xs font-mono bg-accent-50 dark:bg-accent-950 text-accent-700 dark:text-accent-300 px-1.5 py-0.5 rounded mt-1">
                    {formatTimestamp(source.start_time)} – {formatTimestamp(source.end_time)}
                </span>
            )}
            <p className="text-xs text-text-muted italic mt-2 line-clamp-2 border-l-2 border-border-default pl-2">"{source.chunk_text}"</p>
        </div>
    );
};
