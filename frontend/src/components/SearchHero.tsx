const EXAMPLE_QUERIES = [
    'What architecture does the paper propose?',
    'How does self-attention work?',
    'Summarize the key experimental results',
];

export const SearchHero = ({ onPick }: { onPick: (query: string) => void }) => (
    <div className="flex flex-col items-center text-center gap-4 py-8 animate-fade-in">
        <h2 className="text-2xl sm:text-3xl font-semibold text-text-default tracking-tight">
            Ask your research library anything
        </h2>
        <p className="text-text-muted max-w-md">
            Query across every paper, figure, and audio transcript you've ingested — with citations and knowledge-graph context.
        </p>
        <div className="flex flex-wrap justify-center gap-2 mt-2">
            {EXAMPLE_QUERIES.map(q => (
                <button
                    key={q}
                    type="button"
                    onClick={() => onPick(q)}
                    className="text-sm px-3 py-1.5 rounded-full border border-border-default bg-surface-raised text-text-muted hover:text-accent-700 hover:border-accent-300 dark:hover:text-accent-300 dark:hover:border-accent-700 transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500"
                >
                    {q}
                </button>
            ))}
        </div>
    </div>
);
