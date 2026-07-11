import React from 'react';
import { Search } from 'lucide-react';

export const QueryBar = ({
    value,
    onChange,
    onSearch,
    loading,
    compareMode,
    onCompareModeChange,
}: {
    value: string;
    onChange: (text: string) => void;
    onSearch: (txt: string) => void;
    loading: boolean;
    compareMode: boolean;
    onCompareModeChange: (value: boolean) => void;
}) => {
    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (value.trim() && !loading) {
            onSearch(value);
        }
    };

    return (
        <div className="w-full flex flex-col gap-3">
            <form
                onSubmit={handleSubmit}
                className="flex w-full items-center bg-surface-raised border border-border-default rounded-full shadow-sm overflow-hidden p-1 pl-4 focus-within:ring-2 focus-within:ring-accent-500 transition-shadow duration-150"
            >
                <Search className="text-text-muted w-5 h-5 mr-2 shrink-0" />
                <input
                    type="text"
                    value={value}
                    onChange={e => onChange(e.target.value)}
                    placeholder="Ask about transformers, graph attention, datasets..."
                    className="flex-1 outline-none py-3 text-base sm:text-lg bg-transparent text-text-default placeholder:text-text-muted min-w-0"
                    disabled={loading}
                />
                <button
                    type="submit"
                    disabled={loading || !value.trim()}
                    className="bg-accent-600 text-white rounded-full px-5 py-2.5 ml-2 hover:bg-accent-700 font-medium text-sm transition-colors duration-150 disabled:bg-neutral-300 dark:disabled:bg-neutral-700 disabled:text-neutral-500 shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-2"
                >
                    {loading ? 'Searching…' : 'Search'}
                </button>
            </form>
            <label className="flex items-center gap-2 text-sm text-text-muted pl-4 cursor-pointer select-none w-fit">
                <input
                    type="checkbox"
                    checked={compareMode}
                    onChange={e => onCompareModeChange(e.target.checked)}
                    className="rounded accent-accent-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-1"
                />
                Compare graph impact
            </label>
        </div>
    );
};
