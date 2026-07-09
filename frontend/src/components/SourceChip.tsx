import type { SourceChunk } from '../types';

function formatTimestamp(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export const SourceChip = ({ index, source }: { index: number; source: SourceChunk }) => {
    const isAudio = source.modality === 'audio';

    return (
        <div className="flex flex-col p-3 bg-gray-50 border rounded-lg hover:shadow-md transition">
            <div className="flex items-center justify-between mb-1">
                <span className="bg-blue-100 text-blue-800 text-xs font-bold px-2 py-1 rounded-full">[{index}] {isAudio ? 'Audio Transcript' : 'Paper'}</span>
                <span className="text-xs text-gray-500 font-mono">Score: {source.score.toFixed(2)}</span>
            </div>
            <h5 className="font-medium text-gray-800 leading-snug my-1">{source.paper_title}</h5>
            {!isAudio && source.authors?.length > 0 && (
                <p className="text-sm text-gray-500">{source.authors.join(', ')} ({source.year ?? 'n.d.'})</p>
            )}
            {isAudio && source.start_time != null && source.end_time != null && (
                <span className="w-fit text-xs font-mono bg-amber-100 text-amber-800 px-2 py-0.5 rounded mt-1">
                    {formatTimestamp(source.start_time)} - {formatTimestamp(source.end_time)}
                </span>
            )}
            <p className="text-xs text-gray-600 italic mt-2 line-clamp-2 border-l-2 pl-2 border-gray-300">"{source.chunk_text}"</p>
        </div>
    );
};
