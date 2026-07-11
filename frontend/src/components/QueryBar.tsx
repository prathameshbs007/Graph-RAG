import React, { useState } from 'react';
import { Search } from 'lucide-react';

export const QueryBar = ({
    onSearch,
    loading,
    compareMode,
    onCompareModeChange,
}: {
    onSearch: (txt: string) => void;
    loading: boolean;
    compareMode: boolean;
    onCompareModeChange: (value: boolean) => void;
}) => {
    const [text, setText] = useState('');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (text.trim() && !loading) {
            onSearch(text);
        }
    };

    return (
        <div className="w-full flex flex-col gap-2">
            <form onSubmit={handleSubmit} className="flex w-full items-center bg-white border border-gray-300 rounded-full shadow-sm overflow-hidden p-1 px-3">
                <Search className="text-gray-400 w-6 h-6 mr-2" />
                <input
                    type="text"
                    value={text}
                    onChange={e => setText(e.target.value)}
                    placeholder="Ask about transformers, graph attention, datasets..."
                    className="flex-1 outline-none p-3 text-lg bg-transparent text-gray-800"
                    disabled={loading}
                />
                <button
                    type="submit"
                    disabled={loading || !text.trim()}
                    className="bg-blue-600 text-white rounded-full px-6 py-2 ml-2 hover:bg-blue-700 font-medium transition disabled:bg-gray-400"
                >
                    {loading ? 'Searching...' : 'Search'}
                </button>
            </form>
            <label className="flex items-center gap-2 text-sm text-gray-600 pl-4 cursor-pointer select-none">
                <input
                    type="checkbox"
                    checked={compareMode}
                    onChange={e => onCompareModeChange(e.target.checked)}
                    className="rounded"
                />
                Compare graph impact
            </label>
        </div>
    );
};
